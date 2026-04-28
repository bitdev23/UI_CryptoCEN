"""Email notification system for Mantraj AI.

Transport priority (auto-selected based on env vars):
  1. Resend  (RESEND_API_KEY)  — primary; same service used by Supabase auth emails
  2. SMTP    (SMTP_HOST)       — fallback for custom SMTP providers
  3. Noop / log-only          — local dev with no credentials configured

Exposed helpers:
  - send_welcome_email(to_email, display_name)
  - send_quota_warning(to_email, display_name, percent_used, plan, posts_remaining)
  - send_post_published(to_email, display_name, post_title, post_url)

All send functions are non-blocking: they run in a daemon thread so the
caller never waits for API / SMTP round-trips.
"""

from __future__ import annotations

import logging
import os
import smtplib
import threading
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

logger = logging.getLogger('velank.notifications')


# ── Config ────────────────────────────────────────────────────────────────────

_RESEND_API_KEY: str = os.getenv('RESEND_API_KEY', '').strip()
_SMTP_HOST: str = os.getenv('SMTP_HOST', '').strip()
_SMTP_PORT: int = int(os.getenv('SMTP_PORT', '587'))
_SMTP_USER: str = os.getenv('SMTP_USER', '').strip()
_SMTP_PASSWORD: str = os.getenv('SMTP_PASSWORD', '').strip()
_EMAIL_FROM: str = os.getenv('EMAIL_FROM', 'noreply@velank.io').strip()
_EMAIL_FROM_NAME: str = os.getenv('EMAIL_FROM_NAME', 'Mantraj AI').strip()
_APP_URL: str = os.getenv('APP_URL', 'https://app.velank.io').strip()

# Set EMAIL_ENABLED=0 to suppress all email (useful in staging / CI)
_EMAIL_ENABLED: bool = os.getenv('EMAIL_ENABLED', '1').strip().lower() in {'1', 'true', 'yes'}


# ── Transport layer ───────────────────────────────────────────────────────────

def _send_via_resend(to_email: str, subject: str, html_body: str) -> bool:
    """Send via Resend API (https://resend.com)."""
    resend_available = False
    try:
        import resend
        resend_available = True
    except ImportError:
        logger.warning('[RESEND] resend package not installed — run: pip install "resend>=2.0.0"')
        return False

    if not _RESEND_API_KEY:
        logger.error('[RESEND] RESEND_API_KEY not configured in environment')
        return False

    resend.api_key = _RESEND_API_KEY
    logger.info('[RESEND] Package available: %s, API key present: %s', resend_available, bool(_RESEND_API_KEY))
    
    try:
        logger.info('[RESEND] Attempting to send email to %s', to_email)
        logger.info('[RESEND] From: %s', f'{_EMAIL_FROM_NAME} <{_EMAIL_FROM}>')
        
        resp = resend.Emails.send({
            'from': f'{_EMAIL_FROM_NAME} <{_EMAIL_FROM}>',
            'to': [to_email],
            'subject': subject,
            'html': html_body,
        })
        
        logger.info('[RESEND] Full response type: %s', type(resp).__name__)
        logger.info('[RESEND] Full response: %s', resp)
        
        # SDK v2 returns an object; v1 returns a dict — handle both
        email_id = resp.get('id') if isinstance(resp, dict) else getattr(resp, 'id', None)
        
        if email_id:
            logger.info('[RESEND] ✓ Email sent successfully to %s — id=%s', to_email, email_id)
            return True
        else:
            logger.error('[RESEND] Response received but no id field. Response: %s', resp)
            # Check if there's an error in the response
            error = resp.get('error') if isinstance(resp, dict) else getattr(resp, 'error', None)
            if error:
                logger.error('[RESEND] API error: %s', error)
            return False
            
    except Exception as e:
        logger.error('[RESEND] ✗ Exception during send to %s: %s', to_email, str(e))
        logger.exception('[RESEND] Full traceback:')
        return False


def _send_via_smtp(to_email: str, subject: str, html_body: str) -> bool:
    """Send an email via SMTP (e.g. SES, Mailgun, any standard SMTP)."""
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = f'{_EMAIL_FROM_NAME} <{_EMAIL_FROM}>'
    msg['To'] = to_email
    msg.attach(MIMEText(html_body, 'html'))

    try:
        with smtplib.SMTP(_SMTP_HOST, _SMTP_PORT, timeout=15) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            if _SMTP_USER and _SMTP_PASSWORD:
                server.login(_SMTP_USER, _SMTP_PASSWORD)
            server.sendmail(_EMAIL_FROM, [to_email], msg.as_string())
        logger.info('SMTP email sent to %s', to_email)
        return True
    except Exception as e:
        logger.exception('SMTP send failed for %s: %s', to_email, e)
        return False


def _send_email(to_email: str, subject: str, html_body: str) -> bool:
    """Route to the best available transport."""
    if not _EMAIL_ENABLED:
        logger.debug('[EMAIL] Email disabled by EMAIL_ENABLED flag — skipping "%s"', subject)
        return False
    if not to_email:
        logger.warning('[EMAIL] Empty recipient, skipping')
        return False

    if _RESEND_API_KEY:
        logger.info('[EMAIL] Using Resend transport')
        return _send_via_resend(to_email, subject, html_body)
    elif _SMTP_HOST:
        logger.info('[EMAIL] Using SMTP transport')
        return _send_via_smtp(to_email, subject, html_body)
    else:
        logger.warning('[EMAIL] No email transport configured (no RESEND_API_KEY or SMTP_HOST) — would send "%s" to %s', subject, to_email)
        return False


def _send_async(to_email: str, subject: str, html_body: str) -> None:
    """Fire-and-forget email send in a daemon thread."""
    def thread_runner():
        logger.info('[EMAIL_ASYNC] Starting send to %s (subject: %s)', to_email, subject[:50])
        result = _send_email(to_email, subject, html_body)
        if result:
            logger.info('[EMAIL_ASYNC] ✓ Successfully sent to %s', to_email)
        else:
            logger.warning('[EMAIL_ASYNC] ✗ Failed to send to %s', to_email)
    
    t = threading.Thread(
        target=thread_runner,
        daemon=True,
        name=f'email-{subject[:30]}',
    )
    logger.info('[EMAIL_ASYNC] Spawning thread for %s', to_email)
    t.start()


# ── HTML templates ────────────────────────────────────────────────────────────

_BASE_STYLE = """
<style>
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; color: #1a1a2e; margin: 0; padding: 0; }
  .container { max-width: 560px; margin: 0 auto; padding: 32px 24px; }
  .header { font-size: 22px; font-weight: 600; margin-bottom: 16px; color: #6c5ce7; }
  .body-text { font-size: 15px; line-height: 1.65; color: #333; }
  .cta-btn { display: inline-block; padding: 12px 28px; background: #6c5ce7; color: #fff; text-decoration: none; border-radius: 6px; font-weight: 600; margin-top: 20px; }
  .footer { margin-top: 36px; font-size: 12px; color: #999; border-top: 1px solid #eee; padding-top: 16px; }
</style>
"""


def _wrap_html(inner_html: str) -> str:
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8">{_BASE_STYLE}</head><body>
<div class="container">{inner_html}
<div class="footer">Mantraj AI by Velank &middot; <a href="{_APP_URL}" style="color:#6c5ce7;">app.velank.io</a></div>
</div></body></html>"""


# ── Public API ────────────────────────────────────────────────────────────────

def send_welcome_email(to_email: str, display_name: Optional[str] = None) -> None:
    """Send a welcome email after first signup."""
    name = display_name or 'there'
    subject = 'Welcome to Mantraj AI 🎉'
    html = _wrap_html(f"""
<div class="header">Welcome aboard, {name}!</div>
<div class="body-text">
  <p>You're all set to start creating high-quality LinkedIn posts powered by AI and your own knowledge base.</p>
  <p>Here's how to get started:</p>
  <ol>
    <li><strong>Upload documents</strong> to your Knowledge Base</li>
    <li><strong>Configure</strong> your industry, role, and tone</li>
    <li><strong>Generate</strong> your first post in seconds</li>
  </ol>
  <a class="cta-btn" href="{_APP_URL}">Open Dashboard →</a>
</div>
""")
    _send_async(to_email, subject, html)


def send_quota_warning(
    to_email: str,
    display_name: Optional[str] = None,
    percent_used: int = 80,
    plan: str = 'free',
    posts_remaining: int = 0,
) -> None:
    """Warn user when they hit 80% or 90% of their monthly quota."""
    name = display_name or 'there'
    subject = f"\u26a0\ufe0f You have used {percent_used}% of your monthly quota"
    html = _wrap_html(f"""
<div class="header">Quota heads-up, {name}</div>
<div class="body-text">
  <p>You have used <strong>{percent_used}%</strong> of your <strong>{plan}</strong> plan monthly post generation limit.</p>
  <p>You have <strong>{posts_remaining}</strong> posts remaining this billing cycle.</p>
  <p>Need more? Upgrade your plan to unlock higher limits, more KB storage, and advanced features.</p>
  <a class="cta-btn" href="{_APP_URL}#/settings?tab=billing">View Plans →</a>
</div>
""")
    _send_async(to_email, subject, html)


def send_post_published(
    to_email: str,
    display_name: Optional[str] = None,
    post_title: str = '',
    post_url: str = '',
) -> None:
    """Notify user when a scheduled post has been published to LinkedIn."""
    name = display_name or 'there'
    title_preview = (post_title or 'Your post')[:80]
    subject = f'✅ Post published: {title_preview}'
    view_link = post_url or _APP_URL
    html = _wrap_html(f"""
<div class="header">Post published, {name}!</div>
<div class="body-text">
  <p>Your LinkedIn post has been successfully published:</p>
  <blockquote style="border-left:3px solid #6c5ce7; padding-left:12px; color:#555; margin:16px 0;">
    {title_preview}…
  </blockquote>
  <a class="cta-btn" href="{view_link}">View on LinkedIn →</a>
</div>
""")
    _send_async(to_email, subject, html)


def send_subscription_expiry_reminder(
    to_email: str,
    display_name: Optional[str] = None,
    plan: str = 'starter',
    days_remaining: int = 3,
    renewal_url: str = '',
) -> None:
    """Notify user that their paid plan is close to expiry (manual renewal flow)."""
    name = display_name or 'there'
    safe_days = max(0, int(days_remaining or 0))
    plan_name = (plan or 'starter').replace('_', ' ').title()
    link = renewal_url or f"{_APP_URL}#/settings?tab=billing"

    if safe_days <= 0:
        subject = f'Your {plan_name} plan has expired'
        body_line = 'Your paid plan has expired. Renew now to continue with paid limits and features.'
    elif safe_days == 1:
        subject = f'Your {plan_name} plan expires tomorrow'
        body_line = 'Your paid plan expires in 1 day. Renew now to avoid interruption.'
    else:
        subject = f'Your {plan_name} plan expires in {safe_days} days'
        body_line = f'Your paid plan expires in {safe_days} days. Renew early to avoid interruption.'

    html = _wrap_html(f"""
<div class=\"header\">Plan expiry reminder, {name}</div>
<div class=\"body-text\">
  <p>{body_line}</p>
  <p><strong>Current plan:</strong> {plan_name}</p>
  <p>This account uses one-time payments (no auto-debit). Renewal is manual.</p>
  <a class=\"cta-btn\" href=\"{link}\">Renew / Manage Plan →</a>
</div>
""")
    _send_async(to_email, subject, html)


def send_otp_email(to_email: str, otp_code: str) -> None:
    """Send 6-digit OTP code for password reset (non-blocking)."""
    logger.info('[OTP_EMAIL] Queuing OTP email to %s', to_email)
    subject = f'Your Velank AI reset code: {otp_code}'
    html = _wrap_html(f"""
<div class="header">Password reset code</div>
<div class="body-text">
  <p>We received a request to reset the password for your Velank AI account.
     Use the 6-digit code below to continue. <strong>It expires in 10 minutes.</strong></p>
  <div style="letter-spacing:10px;font-size:38px;font-weight:700;color:#1a1a2e;
              text-align:center;margin:28px 0;padding:22px 16px;
              background:#f5f3ff;border-radius:14px;font-family:monospace,monospace">
    {otp_code}
  </div>
  <p style="font-size:13px;color:#888">
    If you didn't request a password reset, you can safely ignore this email —
    your account remains secure.
  </p>
</div>
""")
    _send_async(to_email, subject, html)


def send_otp_email_sync(to_email: str, otp_code: str) -> bool:
    """Send 6-digit OTP code synchronously and return send result."""
    logger.info('[OTP_EMAIL] Sending OTP email synchronously to %s', to_email)
    subject = f'Your Velank AI reset code: {otp_code}'
    html = _wrap_html(f"""
<div class="header">Password reset code</div>
<div class="body-text">
  <p>We received a request to reset the password for your Velank AI account.
     Use the 6-digit code below to continue. <strong>It expires in 10 minutes.</strong></p>
  <div style="letter-spacing:10px;font-size:38px;font-weight:700;color:#1a1a2e;
              text-align:center;margin:28px 0;padding:22px 16px;
              background:#f5f3ff;border-radius:14px;font-family:monospace,monospace">
    {otp_code}
  </div>
  <p style="font-size:13px;color:#888">
    If you didn't request a password reset, you can safely ignore this email —
    your account remains secure.
  </p>
</div>
""")
    result = _send_email(to_email, subject, html)
    if result:
        logger.info('[OTP_EMAIL] ✓ Synchronous OTP sent to %s', to_email)
    else:
        logger.error('[OTP_EMAIL] ✗ Synchronous OTP failed for %s', to_email)
    return result
