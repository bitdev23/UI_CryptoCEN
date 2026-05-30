"""
Simple web dashboard for non-technical LinkedIn automation management.
Run: python app.py
Then open: http://localhost:5050
"""
from flask import Flask, render_template, request, jsonify, redirect, url_for, g, session
from typing import Optional
import os
import json
import base64
import logging
import threading
import time
import sys
import hmac
import hashlib
import schedule
import pytz
import random
import re
import textwrap
import calendar
import requests
from urllib.parse import urlencode
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, date, timezone
from functools import wraps
from uuid import UUID, uuid4
from pathlib import Path
from dotenv import load_dotenv, dotenv_values

try:
    import fcntl
except ImportError:  # pragma: no cover - Windows local dev only
    fcntl = None

BASE_DIR = Path(__file__).resolve().parent


def _load_project_env() -> None:
    env_path = BASE_DIR / '.env'
    load_dotenv(dotenv_path=env_path, override=False)

    if not env_path.exists():
        return

    for key, value in dotenv_values(env_path).items():
        if value is None:
            continue
        current = os.getenv(key)
        if current is None or not str(current).strip():
            os.environ[key] = value


_load_project_env()

from ai_provider import AIProvider
from config import DEFAULT_PROFILE, POST_FORMATS
from prompt_builder import PromptBuilder as _PromptBuilder
from notifications import send_welcome_email as _send_welcome_email, send_quota_warning as _send_quota_warning, send_post_published as _send_post_published, send_otp_email_sync as _send_otp_email_sync, send_subscription_expiry_reminder as _send_subscription_expiry_reminder
from linkedin_poster import LinkedInPoster
from auth import require_auth, signup_user, login_user, logout_user, verify_token, refresh_access_token, request_password_reset, auth_healthcheck, supabase as auth_supabase
from database.db_helper import get_db as _get_db_helper
from kb_jobs import enqueue_kb_training_job, get_kb_training_status
from freemium import create_freemium_blueprint, load_plan_limits as load_freemium_plan_limits
from crypto_utils import encrypt_value, decrypt_value, is_encrypted
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_cors import CORS
try:
    from flask_compress import Compress as _FlaskCompress
except ImportError:  # pragma: no cover — optional dependency
    _FlaskCompress = None
try:
    import sentry_sdk
    from sentry_sdk.integrations.flask import FlaskIntegration
    from sentry_sdk.integrations.logging import LoggingIntegration
    _sentry_available = True
except ImportError:  # pragma: no cover
    _sentry_available = False

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_APP_START_TIME = time.time()
_APP_BOOT_ID = uuid4().hex

# ── Sentry error tracking ─────────────────────────────────────────────────
_sentry_dsn = os.getenv('SENTRY_DSN', '').strip()
if _sentry_available and _sentry_dsn:
    sentry_sdk.init(
        dsn=_sentry_dsn,
        integrations=[
            FlaskIntegration(transaction_style='endpoint'),
            LoggingIntegration(
                level=logging.WARNING,       # breadcrumbs from WARNING+
                event_level=logging.ERROR,   # send Sentry event on ERROR+
            ),
        ],
        traces_sample_rate=float(os.getenv('SENTRY_TRACES_SAMPLE_RATE', '0.05')),
        profiles_sample_rate=0.0,
        environment=os.getenv('FLASK_ENV', 'development'),
        release=os.getenv('GIT_SHA', 'unknown'),
        send_default_pii=False,  # GDPR: no IPs or cookies in events
    )
    logger.info('Sentry error tracking enabled (env=%s)', os.getenv('FLASK_ENV', 'development'))
else:
    if not _sentry_dsn:
        logger.info('Sentry disabled — set SENTRY_DSN to enable')

app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False

# ── CRITICAL: Flask secret key (no unsafe default) ────────────────────────
_flask_secret = os.getenv('FLASK_SECRET_KEY', '').strip()
if not _flask_secret:
    # Allow a generated ephemeral key ONLY in local dev; refuse to start in production
    if os.getenv('FLASK_ENV') == 'production':
        raise RuntimeError(
            'FLASK_SECRET_KEY environment variable is required in production. '
            'Generate one with: python3 -c "import secrets; print(secrets.token_urlsafe(48))"'
        )
    _flask_secret = 'dev-only-' + os.urandom(16).hex()
    logging.getLogger(__name__).warning(
        'FLASK_SECRET_KEY is not set — using an ephemeral random key. '
        'Sessions will not survive restarts. Set FLASK_SECRET_KEY for production.'
    )
app.secret_key = _flask_secret

# ── CORS ──────────────────────────────────────────────────────────────────
CORS(app, resources={r"/api/*": {"origins": os.getenv('ALLOWED_ORIGINS', 'https://app.velank.io').split(',')}})

# ── Response compression (gzip/brotli) ────────────────────────────────────
if _FlaskCompress is not None:
    app.config['COMPRESS_MIN_SIZE'] = 512          # compress responses > 512 bytes
    app.config['COMPRESS_ALGORITHM'] = ['br', 'gzip', 'deflate']
    _FlaskCompress(app)
    logger.info('Flask-Compress enabled (br/gzip/deflate)')

# ── Rate Limiting ─────────────────────────────────────────────────────────
_redis_url = os.getenv('REDIS_URL', '').strip()


def _rate_limit_key() -> str:
    """Per-user rate limiting key.

    Extracts the Supabase user ID from the JWT in the Authorization header
    so each *user* has their own bucket regardless of IP address.
    Falls back to remote IP for unauthenticated routes.
    """
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        token = auth_header[7:]
        try:
            # Decode the JWT payload (no signature verification needed —
            # just extracting the sub claim for bucketing).
            import base64
            payload_b64 = token.split('.')[1]
            # Re-pad to a multiple of 4
            payload_b64 += '=' * (4 - len(payload_b64) % 4)
            payload = json.loads(base64.urlsafe_b64decode(payload_b64))
            uid = payload.get('sub', '').strip()
            if uid:
                return f'user:{uid}'
        except Exception:
            pass  # malformed token — fall through to IP
    return f'ip:{get_remote_address()}'


limiter = Limiter(
    key_func=_rate_limit_key,
    app=app,
    default_limits=["300 per minute", "3000 per hour"],
    storage_uri=_redis_url if _redis_url else "memory://",
    strategy="fixed-window",
    on_breach=lambda limit: logger.warning(
        'Rate limit breached: %s key=%s path=%s',
        limit.limit,
        limit.key,
        request.path,
    ),
)

# Register freemium blueprint
freemium_bp = create_freemium_blueprint()
app.register_blueprint(freemium_bp)

app.config['SESSION_COOKIE_SECURE'] = os.getenv('FLASK_ENV') == 'production'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = 86400  # 24 hours


# ── Security Headers Middleware ───────────────────────────────────────────

@app.before_request
def _structured_request_start():
    """Attach timing and context to each request for structured logging."""
    request._start_time = time.time()
    request._request_id = secrets.token_hex(8)


@app.after_request
def _structured_request_log(response):
    """Emit a structured log line for every API request."""
    if not hasattr(request, '_start_time'):
        return response
    elapsed_ms = round((time.time() - request._start_time) * 1000, 1)
    if request.path.startswith('/api/') or request.path == '/health':
        # Extract user_id from the auth token if present (best-effort, no DB hit)
        uid = ''
        try:
            uid = getattr(request, '_current_user_id', '') or ''
        except Exception:
            pass
        logger.info(
            'req:%s %s %s %s %sms uid=%s',
            request._request_id,
            request.method,
            request.path,
            response.status_code,
            elapsed_ms,
            uid or '-',
        )
    response.headers['X-Request-Id'] = request._request_id
    return response


@app.after_request
def set_security_headers(response):
    """Inject security headers into every response."""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Permissions-Policy'] = 'geolocation=(), camera=(), microphone=()'
    if os.getenv('FLASK_ENV') == 'production':
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com https://cdn.razorpay.com https://checkout.razorpay.com; "
            "style-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com https://fonts.googleapis.com; "
            "font-src 'self' https://cdnjs.cloudflare.com https://fonts.gstatic.com; "
            "img-src 'self' data: https://checkout.razorpay.com https://static.razorpay.com; "
            "frame-src 'self' https://checkout.razorpay.com https://api.razorpay.com; "
            "connect-src 'self' https://*.supabase.co https://ipapi.co https://api.razorpay.com https://checkout.razorpay.com https://lumberjack.razorpay.com https://cdn.razorpay.com;"
        )

    # Auth screens must not be cached, otherwise users can get stale JS flows
    # after deploys (especially behind CDN/proxy layers).
    if request.path in {'/login', '/auth/callback', '/auth/reset-callback'}:
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    return response


# ── Custom Error Handlers ─────────────────────────────────────────────────
@app.errorhandler(404)
def not_found_error(error):
    if request.path.startswith('/api/'):
        return jsonify({'success': False, 'message': 'Endpoint not found'}), 404
    return render_template('error.html',
        error_code=404,
        error_title='Page Not Found',
        error_message="The page you're looking for doesn't exist or has been moved. Check the URL or head back to your dashboard."
    ), 404


@app.errorhandler(429)
def ratelimit_handler(error):
    if request.path.startswith('/api/'):
        return jsonify({
            'success': False,
            'message': 'Too many requests. Please slow down and try again shortly.',
            'retry_after': error.description
        }), 429
    return render_template('error.html',
        error_code=429,
        error_title='Too Many Requests',
        error_message="You've sent too many requests in a short period. Please wait a moment and try again."
    ), 429


@app.errorhandler(500)
def internal_error(error):
    logger.exception('Internal server error: %s', error)
    
    # Log error to database
    try:
        import traceback
        error_type = type(error).__name__
        error_message = str(error)
        stack_trace = traceback.format_exc()
        user_id = None
        try:
            user_id = session.get('user_id')
        except:
            pass
        
        error_log = {
            'error_type': error_type,
            'error_message': error_message,
            'stack_trace': stack_trace,
            'endpoint': request.path,
            'request_method': request.method,
            'status_code': 500,
            'severity': 'critical',
            'context': {
                'referrer': request.referrer,
                'user_agent': request.user_agent.string
            },
            'created_at': datetime.utcnow().isoformat()
        }
        if user_id:
            error_log['user_id'] = user_id
        
        auth_supabase.table('error_logs').insert([error_log]).execute()
    except Exception as e:
        logger.warning('Failed to log error to database: %s', e)
    
    if request.path.startswith('/api/'):
        return jsonify({'success': False, 'message': 'Internal server error'}), 500
    return render_template('error.html',
        error_code=500,
        error_title='Something Went Wrong',
        error_message="An unexpected error occurred on our end. Our team has been notified. Please try again in a few moments."
    ), 500

@app.errorhandler(403)
def forbidden_error(error):
    if request.path.startswith('/api/'):
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    return render_template('error.html',
        error_code=403,
        error_title='Access Denied',
        error_message="You don't have permission to access this page. If you believe this is an error, please contact support."
    ), 403


# ── CSRF Protection ──────────────────────────────────────────────────────
# API routes use Bearer token auth (inherently CSRF-safe).
# Session-based routes (admin login) get a double-submit cookie CSRF check.
import secrets

@app.before_request
def _csrf_protect():
    """Double-submit cookie CSRF protection for session-based form POSTs.

    Skipped for:
    - GET, HEAD, OPTIONS (safe methods)
    - /api/* routes (JWT-authenticated, CSRF-safe by design)
    - /api/billing/webhook (server-to-server callback)
    """
    if request.method in ('GET', 'HEAD', 'OPTIONS'):
        return None
    if request.path.startswith('/api/'):
        return None
    # For session-based POST routes (admin login, etc.), enforce CSRF token
    token_from_form = request.form.get('csrf_token') or (request.get_json(silent=True) or {}).get('csrf_token')
    token_from_cookie = request.cookies.get('csrf_token')
    if not token_from_form or not token_from_cookie or not hmac.compare_digest(token_from_form, token_from_cookie):
        logger.warning('CSRF validation failed for %s %s', request.method, request.path)
        return jsonify({'success': False, 'message': 'CSRF validation failed. Please refresh the page.'}), 403


@app.after_request
def _set_csrf_cookie(response):
    """Set a CSRF cookie if one doesn't exist or is about to expire."""
    if 'csrf_token' not in request.cookies:
        token = secrets.token_hex(32)
        response.set_cookie(
            'csrf_token', token,
            httponly=False,   # JS needs to read this for forms
            samesite='Lax',
            secure=os.getenv('FLASK_ENV') == 'production',
            max_age=86400
        )
    return response


def get_csrf_token() -> str:
    """Retrieve or generate a CSRF token for template injection."""
    token = request.cookies.get('csrf_token')
    if not token:
        token = secrets.token_hex(32)
    return token


_INCIDENT_STATE_CACHE = {
    'expires_at': 0.0,
    'state': {
        'maintenance_mode': {'enabled': False, 'config': {}},
        'kill_generate_preview': {'enabled': False, 'config': {}},
        'kill_scheduler': {'enabled': False, 'config': {}},
        'kill_kb_training': {'enabled': False, 'config': {}},
        'kill_linkedin_posting': {'enabled': False, 'config': {}},
    },
}


def _get_incident_state_cached() -> dict:
    now_ts = time.time()
    if now_ts < float(_INCIDENT_STATE_CACHE.get('expires_at', 0.0)):
        return _INCIDENT_STATE_CACHE.get('state', {})
    defaults = {
        'maintenance_mode': {'enabled': False, 'config': {}},
        'kill_generate_preview': {'enabled': False, 'config': {}},
        'kill_scheduler': {'enabled': False, 'config': {}},
        'kill_kb_training': {'enabled': False, 'config': {}},
        'kill_linkedin_posting': {'enabled': False, 'config': {}},
    }
    if not auth_supabase:
        _INCIDENT_STATE_CACHE['state'] = defaults
        _INCIDENT_STATE_CACHE['expires_at'] = now_ts + 15
        return defaults
    try:
        rows = auth_supabase.table('feature_flags').select('key,is_enabled_globally,config').in_('key', list(defaults.keys())).execute().data or []
        merged = dict(defaults)
        for row in rows:
            key = str(row.get('key') or '').strip()
            if key in merged:
                merged[key] = {
                    'enabled': bool(row.get('is_enabled_globally', False)),
                    'config': row.get('config', {}) or {},
                }
        _INCIDENT_STATE_CACHE['state'] = merged
        _INCIDENT_STATE_CACHE['expires_at'] = now_ts + 20
        return merged
    except Exception as e:
        logger.debug('Incident controls fetch failed: %s', e)
        _INCIDENT_STATE_CACHE['state'] = defaults
        _INCIDENT_STATE_CACHE['expires_at'] = now_ts + 10
        return defaults


@app.before_request
def _enforce_incident_controls():
    path = request.path or '/'
    if path.startswith('/admin') or path.startswith('/api/admin'):
        return None
    if path.startswith('/static/') or path.startswith('/assets/'):
        return None
    if path == '/maintenance':
        return None
    if path in {'/health', '/api/health'}:
        return None
    if path.startswith('/auth') or path.startswith('/login') or path.startswith('/signup'):
        return None

    controls = _get_incident_state_cached()
    maintenance = controls.get('maintenance_mode', {})
    maintenance_config = (maintenance.get('config', {}) or {})
    maintenance_enabled = bool(maintenance.get('enabled', False))
    maintenance_msg = str(maintenance_config.get('banner_message') or 'Scheduled maintenance is currently active. Please check back shortly.')
    maintenance_ends_at = str(maintenance_config.get('ends_at') or '').strip()
    try:
        retry_after_seconds = int(maintenance_config.get('retry_after_seconds') or 300)
    except Exception:
        retry_after_seconds = 300
    retry_after_seconds = max(30, min(retry_after_seconds, 86400))
    maintenance_headers = {
        'Retry-After': str(retry_after_seconds),
        'Cache-Control': 'no-store, no-cache, must-revalidate, max-age=0',
    }

    if maintenance_enabled:
        if path.startswith('/api/'):
            return jsonify({
                'success': False,
                'maintenance': True,
                'message': maintenance_msg,
                'ends_at': maintenance_ends_at,
                'retry_after_seconds': retry_after_seconds,
            }), 503, maintenance_headers
        return (
            render_template(
                'maintenance.html',
                maintenance_message=maintenance_msg,
                maintenance_ends_at=maintenance_ends_at,
                retry_after_seconds=retry_after_seconds,
            ),
            503,
            maintenance_headers,
        )

    if controls.get('kill_generate_preview', {}).get('enabled') and path == '/api/generate-preview':
        return jsonify({'success': False, 'message': 'Generation is temporarily disabled by incident control.'}), 503
    if controls.get('kill_scheduler', {}).get('enabled') and path.startswith('/api/scheduled-posts'):
        return jsonify({'success': False, 'message': 'Scheduling is temporarily disabled by incident control.'}), 503
    if controls.get('kill_kb_training', {}).get('enabled') and request.method in {'POST', 'PUT', 'PATCH'} and (
        'knowledge-base' in path or 'kb' in path
    ):
        return jsonify({'success': False, 'message': 'Knowledge base operations are temporarily disabled by incident control.'}), 503
    return None


@app.route('/maintenance')
def maintenance_page():
    controls = _get_incident_state_cached()
    maintenance = controls.get('maintenance_mode', {})
    maintenance_config = (maintenance.get('config', {}) or {})
    if not bool(maintenance.get('enabled', False)):
        return redirect('/')

    message = str(maintenance_config.get('banner_message') or 'Scheduled maintenance is currently active. Please check back shortly.')
    ends_at = str(maintenance_config.get('ends_at') or '').strip()
    try:
        retry_after_seconds = int(maintenance_config.get('retry_after_seconds') or 300)
    except Exception:
        retry_after_seconds = 300
    retry_after_seconds = max(30, min(retry_after_seconds, 86400))
    headers = {
        'Retry-After': str(retry_after_seconds),
        'Cache-Control': 'no-store, no-cache, must-revalidate, max-age=0',
    }
    return (
        render_template(
            'maintenance.html',
            maintenance_message=message,
            maintenance_ends_at=ends_at,
            retry_after_seconds=retry_after_seconds,
        ),
        503,
        headers,
    )

# Make csrf_token available in all templates
app.jinja_env.globals['csrf_token'] = get_csrf_token


def _safe_api_error(user_message: str, exc: Exception = None, status: int = 500) -> tuple:
    """Return a sanitised JSON error response.

    Logs the full exception server-side but sends only the generic *user_message*
    to the client — never str(e).
    """
    if exc is not None:
        logger.exception('%s: %s', user_message, exc)
    return jsonify({'success': False, 'message': user_message}), status


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
PDF_DIR = os.path.join(DATA_DIR, 'pdfs')
FEATURE_STORE_PATH = os.path.join(DATA_DIR, 'user_features.json')
POSTS_PATH = os.path.join(DATA_DIR, 'posts.json')
SCHEDULED_POSTS_PATH = os.path.join(DATA_DIR, 'scheduled_posts.json')
FEATURE_STORE_LOCK = threading.Lock()
BACKGROUND_SERVICES_LOCK = threading.Lock()
_BACKGROUND_SERVICES_STARTED = False
_BACKGROUND_SERVICES_LOCK_FD = None

# ── Register admin blueprint (extracted from app.py monolith — P1-6) ────────
from routes.admin import create_admin_blueprint as _create_admin_bp
_admin_bp = _create_admin_bp(limiter=limiter, logger=logger, data_dir=DATA_DIR)
app.register_blueprint(_admin_bp)

# ── Register admin features blueprint (notifications, errors, flags, revenue) ──
from routes.admin_features import create_admin_features_blueprint as _create_features_bp
_features_bp = _create_features_bp(auth_supabase=auth_supabase, limiter=limiter)
app.register_blueprint(_features_bp)

# ── Scheduler health tracking ───────────────────────────────────────────────
_SCHEDULER_HEARTBEAT: float = 0.0     # last time scheduler loop ran
_SCHEDULER_THREAD: Optional[threading.Thread] = None

# ── Password-reset OTP — backed by Supabase (survives restarts/deploys) ────────
_OTP_TTL_MINUTES: int = 10


def _otp_upsert(email: str, code: str, expiry: datetime) -> None:
    """Write or overwrite an OTP record in Supabase."""
    if not auth_supabase:
        raise RuntimeError('Supabase not configured')
    auth_supabase.table('password_reset_otps').upsert(
        {'email': email, 'code': code, 'expires_at': expiry.isoformat() + '+00:00'},
        on_conflict='email',
    ).execute()


def _otp_get(email: str) -> Optional[dict]:
    """Return {'code': str, 'expires_at': str} or None."""
    if not auth_supabase:
        return None
    try:
        res = auth_supabase.table('password_reset_otps') \
            .select('code,expires_at') \
            .eq('email', email) \
            .limit(1) \
            .execute()
        return res.data[0] if res.data else None
    except Exception as exc:
        logger.warning('OTP lookup failed for %s: %s', email, exc)
        return None


def _otp_delete(email: str) -> None:
    """Remove OTP record after use."""
    if not auth_supabase:
        return
    try:
        auth_supabase.table('password_reset_otps').delete().eq('email', email).execute()
    except Exception as exc:
        logger.warning('OTP delete failed for %s: %s', email, exc)


def _otp_expired(expires_at_str: str) -> bool:
    """True if the stored expiry (UTC ISO string) is in the past."""
    try:
        # Supabase returns e.g. "2026-04-13T12:00:00+00:00" — strip tz for comparison
        return datetime.utcnow() > datetime.fromisoformat(expires_at_str[:19])
    except Exception:
        return True  # treat unparseable as expired
_SCHEDULER_STALE_SEC = 120            # consider dead if no heartbeat for 2 min

# ── Initialise shared db_helper with auth_supabase client ────────────────────
try:
    if auth_supabase:
        _get_db_helper(client=auth_supabase)
        logger.info('db_helper initialised with shared auth_supabase client')
except Exception as _db_init_err:
    logger.warning('db_helper init failed (non-fatal): %s', _db_init_err)


def get_user_pdf_dir(user_id: str) -> str:
    return os.path.join(PDF_DIR, user_id)


def resolve_local_kb_path(storage_path: str, filename: str, user_id: str) -> str:
    if storage_path and isinstance(storage_path, str) and storage_path.startswith('local/'):
        rel_path = storage_path[len('local/'):].lstrip('/').replace('\\', '/')
        candidate = os.path.normpath(os.path.join(PDF_DIR, rel_path))
        if os.path.isfile(candidate):
            return candidate

    user_candidate = os.path.join(get_user_pdf_dir(user_id), filename)
    if os.path.isfile(user_candidate):
        return user_candidate

    legacy_candidate = os.path.join(PDF_DIR, filename)
    return legacy_candidate


def _read_feature_store() -> dict:
    """Read user features from Supabase user_features table (falls back to JSON file)."""
    try:
        if auth_supabase:
            result = auth_supabase.table('user_features').select('user_id, features').execute()
            if result.data:
                store = {}
                for row in result.data:
                    uid = str(row.get('user_id') or '').strip()
                    blob = row.get('features')
                    if uid and isinstance(blob, dict):
                        store[uid] = blob
                return store
    except Exception as e:
        logger.warning('user_features DB read failed, falling back to file: %s', e)
    # Fallback to JSON file
    if not os.path.exists(FEATURE_STORE_PATH):
        return {}
    try:
        with open(FEATURE_STORE_PATH, 'r') as fh:
            data = json.load(fh)
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _write_feature_store(payload: dict) -> None:
    """Write user features to Supabase (DB-only, no shared JSON file)."""
    try:
        if auth_supabase and isinstance(payload, dict):
            for uid, blob in payload.items():
                if not is_valid_uuid(str(uid)):
                    continue
                auth_supabase.table('user_features').upsert({
                    'user_id': uid,
                    'features': blob if isinstance(blob, dict) else {},
                    'updated_at': datetime.utcnow().isoformat() + 'Z',
                }, on_conflict='user_id').execute()
    except Exception as e:
        logger.warning('user_features DB write failed: %s', e)


def _read_feature_blob_for_user(user_id: str) -> dict:
    """Read a single user's feature blob directly from DB (per-tenant, no cross-user leak)."""
    try:
        if auth_supabase:
            result = auth_supabase.table('user_features').select('features').eq('user_id', user_id).execute()
            if result.data and isinstance(result.data[0].get('features'), dict):
                return result.data[0]['features']
    except Exception as e:
        logger.debug('Single-user feature read failed: %s', e)
    return {}


def _write_feature_blob_for_user(user_id: str, blob: dict) -> None:
    """Write a single user's feature blob directly to DB (per-tenant, no shared JSON)."""
    try:
        if auth_supabase and is_valid_uuid(str(user_id)):
            auth_supabase.table('user_features').upsert({
                'user_id': user_id,
                'features': blob if isinstance(blob, dict) else {},
                'updated_at': datetime.utcnow().isoformat() + 'Z',
            }, on_conflict='user_id').execute()
    except Exception as e:
        logger.warning('Single-user feature write failed: %s', e)


# ── Posts/Scheduled storage: Supabase-backed ──────────────────────────────

def _db_save_post(user_id: str, post_data: dict) -> None:
    """Persist a post row to Supabase posts table."""
    try:
        if not auth_supabase:
            return
        row = {
            'user_id': user_id,
            'content': post_data.get('content', ''),
            'hashtags': post_data.get('hashtags', []),
            'topic': post_data.get('theme', ''),
            'industry': post_data.get('audience_industry', ''),
            'role': post_data.get('professional_role', ''),
            'ai_provider': post_data.get('provider', ''),
            'status': 'posted' if post_data.get('posted') else 'draft',
            'posted': bool(post_data.get('posted')),
            'test_mode': bool(post_data.get('test_mode')),
            'linkedin_urn': post_data.get('linkedin_urn') or None,
            'kb_mode': post_data.get('kb_mode', ''),
            'workspace_id': post_data.get('workspace_id', ''),
            'analytics': post_data.get('analytics') or {},
            'metadata': {
                k: v for k, v in post_data.items()
                if k not in ('content', 'hashtags', 'theme', 'audience_industry',
                             'professional_role', 'provider', 'posted', 'test_mode',
                             'linkedin_urn', 'kb_mode', 'workspace_id', 'analytics',
                             'user_id', 'created_at')
            },
        }
        if post_data.get('created_at'):
            row['created_at'] = post_data['created_at']
        auth_supabase.table('posts').insert(row).execute()
    except Exception as e:
        logger.warning('DB post save failed (non-fatal): %s', e)


def _db_list_posts(user_id: str, limit: int = 50) -> list:
    """Retrieve user's posts from Supabase."""
    try:
        if not auth_supabase:
            return []
        result = auth_supabase.table('posts').select('*').eq(
            'user_id', user_id
        ).order('created_at', desc=True).limit(limit).execute()
        return result.data or []
    except Exception as e:
        logger.warning('DB posts list failed: %s', e)
        return []


def _db_update_post(post_id: str, updates: dict) -> None:
    """Update a post row in Supabase."""
    try:
        if auth_supabase and post_id:
            auth_supabase.table('posts').update(updates).eq('id', post_id).execute()
    except Exception as e:
        logger.debug('DB post update failed: %s', e)


def _db_delete_user_posts(user_id: str) -> int:
    """Delete all posts for a user from Supabase. Returns count deleted."""
    try:
        if not auth_supabase:
            return 0
        result = auth_supabase.table('posts').delete().eq('user_id', user_id).execute()
        return len(result.data) if result.data else 0
    except Exception as e:
        logger.warning('DB posts delete failed: %s', e)
        return 0


def _db_save_scheduled_post(user_id: str, sp: dict) -> None:
    """Save a scheduled post to Supabase scheduled_posts (flat, no FK to posts)."""
    try:
        if not auth_supabase:
            return
        row = {
            'user_id': user_id,
            'content': sp.get('content', ''),
            'hashtags': sp.get('hashtags', []),
            'schedule_time': sp.get('schedule_time', ''),
            'status': 'pending',
            'metadata': {k: v for k, v in sp.items() if k not in ('content', 'hashtags', 'schedule_time', 'user_id', 'id', 'created_at')},
        }
        if sp.get('id'):
            row['id'] = sp['id']
        auth_supabase.table('scheduled_posts_v2').upsert(row, on_conflict='id').execute()
    except Exception as e:
        logger.warning('DB scheduled post save failed: %s', e)


def _db_list_scheduled_posts(user_id: str) -> list:
    """List pending scheduled posts for user from Supabase."""
    try:
        if not auth_supabase:
            return []
        result = auth_supabase.table('scheduled_posts_v2').select('*').eq(
            'user_id', user_id
        ).eq('status', 'pending').order('schedule_time').execute()
        return result.data or []
    except Exception as e:
        logger.debug('DB scheduled posts list failed: %s', e)
        return []


def _db_delete_scheduled_post(post_id: str) -> None:
    """Delete a scheduled post from Supabase."""
    try:
        if auth_supabase and post_id:
            auth_supabase.table('scheduled_posts_v2').delete().eq('id', post_id).execute()
    except Exception as e:
        logger.debug('DB scheduled post delete failed: %s', e)


def _db_get_due_scheduled_posts() -> list:
    """Get all pending scheduled posts that are due now."""
    try:
        if not auth_supabase:
            return []
        now = datetime.utcnow().isoformat() + 'Z'
        result = auth_supabase.table('scheduled_posts_v2').select('*').eq(
            'status', 'pending'
        ).lte('schedule_time', now).execute()
        return result.data or []
    except Exception as e:
        logger.debug('DB due scheduled posts failed: %s', e)
        return []


def _db_mark_scheduled_post_done(post_id: str, status: str = 'published', error: str = '') -> None:
    """Mark a scheduled post as published or failed."""
    try:
        if auth_supabase and post_id:
            update = {'status': status}
            if error:
                update['error_message'] = error[:500]
            auth_supabase.table('scheduled_posts_v2').update(update).eq('id', post_id).execute()
    except Exception as e:
        logger.debug('DB scheduled post status update failed: %s', e)


def _read_json_list(file_path: str) -> list:
    if not os.path.exists(file_path):
        return []
    try:
        with open(file_path, 'r') as fh:
            raw = fh.read().strip()
        if not raw:
            return []
        data = json.loads(raw)
        return data if isinstance(data, list) else []
    except Exception:
        logger.warning("Failed to read list JSON file: %s", file_path)
        return []


def _write_json_list(file_path: str, items: list) -> None:
    """Atomically write a JSON list file (safe under multi-worker Gunicorn).

    Writes to a temp file first, then renames — this avoids partial/corrupt
    reads if another worker opens the same path concurrently.
    """
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    payload = items if isinstance(items, list) else []
    tmp_path = file_path + '.tmp'
    with open(tmp_path, 'w') as fh:
        json.dump(payload, fh, indent=2)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp_path, file_path)


def _parse_post_datetime(value) -> datetime:
    if isinstance(value, datetime):
        return value

    text = str(value or '').strip()
    if not text:
        return datetime.min


def _parse_schedule_datetime(value) -> datetime:
    text = str(value or '').strip()
    if not text:
        return datetime.min
    try:
        parsed = datetime.fromisoformat(text.replace('Z', '+00:00'))
        if parsed.tzinfo is not None:
            return parsed.astimezone().replace(tzinfo=None)
        return parsed
    except Exception:
        return datetime.min


def _find_fallback_user_with_linkedin_config() -> str:
    """Return a user_id that has LinkedIn credentials configured (DB-only, no full store scan)."""
    try:
        if auth_supabase:
            # Query only users whose features JSONB contains LinkedIn creds
            result = auth_supabase.table('user_features').select('user_id, features').execute()
            for row in (result.data or []):
                uid = str(row.get('user_id') or '').strip()
                if not uid or not is_valid_uuid(uid):
                    continue
                blob = row.get('features')
                if not isinstance(blob, dict):
                    continue
                cfg = blob.get('user_config') if isinstance(blob.get('user_config'), dict) else {}
                access_token = str(cfg.get('LINKEDIN_ACCESS_TOKEN') or '').strip()
                person_id = str(cfg.get('LINKEDIN_PERSON_ID') or '').strip()
                if access_token and person_id:
                    return uid
    except Exception:
        pass
    return ''

    try:
        normalized = text.replace('Z', '+00:00')
        return datetime.fromisoformat(normalized)
    except Exception:
        return datetime.min


def _extract_post_metrics(post: dict) -> dict:
    analytics_blob = post.get('analytics') if isinstance(post.get('analytics'), dict) else {}

    def _to_int(*keys):
        for key in keys:
            candidate = analytics_blob.get(key)
            if candidate is None:
                candidate = post.get(key)
            if candidate is None:
                continue
            try:
                return int(float(candidate))
            except Exception:
                continue
        return None

    def _to_float(*keys):
        for key in keys:
            candidate = analytics_blob.get(key)
            if candidate is None:
                candidate = post.get(key)
            if candidate is None:
                continue
            try:
                return float(candidate)
            except Exception:
                continue
        return None

    impressions = _to_int('impressions', 'reach')
    likes = _to_int('likes', 'reactions')
    comments = _to_int('comments')
    shares = _to_int('shares')
    engagement_rate = _to_float('engagement_rate', 'engagementRate')

    interactions = sum(x for x in [likes, comments, shares] if isinstance(x, int))
    if engagement_rate is None and isinstance(impressions, int) and impressions > 0 and interactions > 0:
        engagement_rate = round((interactions / impressions) * 100, 2)

    return {
        'impressions': impressions,
        'likes': likes,
        'comments': comments,
        'shares': shares,
        'engagement_rate': engagement_rate,
        'interactions': interactions
    }


def _calculate_real_analytics(posts: list, scheduled_posts: list = None) -> dict:
    normalized_posts = posts if isinstance(posts, list) else []
    scheduled = scheduled_posts if isinstance(scheduled_posts, list) else []
    scheduled_count = len(scheduled)

    if not normalized_posts:
        return {
            'total_posts': 0,
            'posts_this_month': 0,
            'live_posts': 0,
            'test_posts': 0,
            'posted_count': 0,
            'scheduled_count': scheduled_count,
            'best_day': '-',
            'posting_streak': 0,
            'avg_post_length': 0,
            'total_tracked_impressions': 0,
            'total_tracked_interactions': 0,
            'avg_engagement_rate': None,
            'top_post_engagement_rate': None,
            'tracked_posts_count': 0,
            'top_hashtags': [],
            'hourly_performance': {},
            'engagement_trend': [],
            'performance_history': [],
            'insights': ['No posts yet — generate and publish content to unlock analytics.']
        }

    # sorted_posts = sorted(normalized_posts, key=lambda p: _parse_post_datetime(p.get('created_at')), reverse=True)

    sorted_posts = sorted(normalized_posts, key=lambda p: _parse_post_datetime(p.get('created_at')) or datetime.min, reverse=True)

    day_counter = Counter()
    unique_days = set()
    hourly_performance = {}
    hashtag_counter = Counter()
    total_length = 0

    total_tracked_impressions = 0
    total_tracked_interactions = 0
    weighted_engagement_sum = 0.0
    weighted_engagement_denominator = 0
    tracked_posts_count = 0
    top_post_engagement_rate = None

    now = datetime.now()
    posts_this_month = 0

    performance_history = []

    for post in sorted_posts:
        post_dt = _parse_post_datetime(post.get('created_at'))
        if post_dt != datetime.min:
            day_key = post_dt.date().isoformat()
            day_counter[day_key] += 1
            unique_days.add(day_key)
            if post_dt.year == now.year and post_dt.month == now.month:
                posts_this_month += 1

            hour_key = str(post_dt.hour)
            if hour_key not in hourly_performance:
                hourly_performance[hour_key] = {
                    'posts': 0,
                    'tracked_impressions': 0,
                    'tracked_posts': 0
                }
            hourly_performance[hour_key]['posts'] += 1

        content = str(post.get('content') or '')
        total_length += len(content)

        for tag in post.get('hashtags') or []:
            normalized_tag = str(tag or '').strip()
            if normalized_tag:
                hashtag_counter[normalized_tag] += 1

        metrics = _extract_post_metrics(post)
        impressions = metrics['impressions']
        engagement_rate = metrics['engagement_rate']

        if isinstance(impressions, int) and impressions >= 0:
            tracked_posts_count += 1
            total_tracked_impressions += impressions
            total_tracked_interactions += metrics['interactions']
            if post_dt != datetime.min:
                hourly_performance[str(post_dt.hour)]['tracked_impressions'] += impressions
                hourly_performance[str(post_dt.hour)]['tracked_posts'] += 1

            if isinstance(engagement_rate, (int, float)):
                weight = impressions if impressions > 0 else 1
                weighted_engagement_sum += float(engagement_rate) * weight
                weighted_engagement_denominator += weight
                if top_post_engagement_rate is None or float(engagement_rate) > top_post_engagement_rate:
                    top_post_engagement_rate = float(engagement_rate)

        if len(performance_history) < 5:
            performance_history.append({
                'created_at': post.get('created_at'),
                'content': content,
                'posted': bool(post.get('posted')),
                'test_mode': bool(post.get('test_mode')),
                'impressions': impressions,
                'engagement_rate': engagement_rate,
                'interactions': metrics['interactions']
            })

    avg_engagement_rate = None
    if weighted_engagement_denominator > 0:
        avg_engagement_rate = round(weighted_engagement_sum / weighted_engagement_denominator, 2)

    # Best day by posting volume
    best_day = '-'
    if day_counter:
        best_iso_day = max(day_counter.items(), key=lambda kv: kv[1])[0]
        try:
            best_day = datetime.fromisoformat(best_iso_day).strftime('%a')
        except Exception:
            best_day = best_iso_day

    # Posting streak by consecutive active days, ending on most recent active day
    posting_streak = 0
    if unique_days:
        sorted_days = sorted(datetime.fromisoformat(d).date() for d in unique_days)
        cursor = sorted_days[-1]
        day_set = set(sorted_days)
        while cursor in day_set:
            posting_streak += 1
            cursor = cursor - timedelta(days=1)

    # Trend by last 7 active days
    trend_days = sorted(day_counter.keys())[-7:]
    engagement_trend = []
    for day_key in trend_days:
        day_posts = [p for p in normalized_posts if _parse_post_datetime(p.get('created_at')).date().isoformat() == day_key]
        day_impressions = 0
        day_engagement_weighted = 0.0
        day_weight = 0
        for post in day_posts:
            metrics = _extract_post_metrics(post)
            if isinstance(metrics['impressions'], int) and metrics['impressions'] >= 0:
                day_impressions += metrics['impressions']
                if isinstance(metrics['engagement_rate'], (int, float)):
                    weight = metrics['impressions'] if metrics['impressions'] > 0 else 1
                    day_engagement_weighted += float(metrics['engagement_rate']) * weight
                    day_weight += weight

        engagement_trend.append({
            'date': day_key,
            'posts': day_counter[day_key],
            'impressions': day_impressions,
            'engagement_rate': round(day_engagement_weighted / day_weight, 2) if day_weight > 0 else None
        })

    insights = []
    if posting_streak >= 3:
        insights.append(f'🔥 Strong consistency: {posting_streak}-day posting streak.')
    elif posting_streak == 1:
        insights.append('📅 You posted recently — keep momentum with daily or weekly consistency.')

    if tracked_posts_count == 0:
        insights.append('📡 No platform metrics tracked yet. Add impressions/engagement fields to post records or analytics sync to unlock true performance KPIs.')
    else:
        insights.append(f'📊 Tracked metrics available for {tracked_posts_count} post(s).')

    if hashtag_counter:
        top_tag, top_count = hashtag_counter.most_common(1)[0]
        insights.append(f'🏷️ Top hashtag so far: {top_tag} ({top_count} uses).')

    if not insights:
        insights.append('Start posting to generate analytics history.')

    return {
        'total_posts': len(normalized_posts),
        'posts_this_month': posts_this_month,
        'live_posts': sum(1 for p in normalized_posts if not p.get('test_mode')),
        'test_posts': sum(1 for p in normalized_posts if p.get('test_mode')),
        'posted_count': sum(1 for p in normalized_posts if p.get('posted')),
        'scheduled_count': scheduled_count,
        'best_day': best_day,
        'posting_streak': posting_streak,
        'avg_post_length': round(total_length / len(normalized_posts)) if normalized_posts else 0,
        'total_tracked_impressions': total_tracked_impressions,
        'total_tracked_interactions': total_tracked_interactions,
        'avg_engagement_rate': avg_engagement_rate,
        'top_post_engagement_rate': round(top_post_engagement_rate, 2) if isinstance(top_post_engagement_rate, (int, float)) else None,
        'tracked_posts_count': tracked_posts_count,
        'top_hashtags': [{'hashtag': h, 'count': c} for h, c in hashtag_counter.most_common(10)],
        'hourly_performance': hourly_performance,
        'engagement_trend': engagement_trend,
        'performance_history': performance_history,
        'insights': insights
    }


def _extract_linkedin_urn(post: dict) -> str:
    if not isinstance(post, dict):
        return ''

    direct = str(post.get('linkedin_urn') or '').strip()
    if direct:
        return direct

    publish_response = post.get('publish_response') if isinstance(post.get('publish_response'), dict) else {}
    response_blob = publish_response.get('response') if isinstance(publish_response.get('response'), dict) else {}

    for candidate in [
        publish_response.get('id'),
        publish_response.get('urn'),
        response_blob.get('id'),
        response_blob.get('urn'),
    ]:
        value = str(candidate or '').strip()
        if value:
            return value

    return ''


def _sync_linkedin_analytics(max_posts: int = 25, user_id: str = '') -> dict:
    config_obj = load_config(user_id)
    access_token = str(config_obj.get('LINKEDIN_ACCESS_TOKEN') or '').strip()
    person_id = str(config_obj.get('LINKEDIN_PERSON_ID') or '').strip()

    if not access_token:
        return {
            'success': False,
            'message': 'LinkedIn access token is missing. Configure it in Settings first.',
            'synced': 0,
            'eligible_posts': 0,
            'errors': []
        }

    # Try DB first, fall back to JSON
    db_posts = _db_list_posts(user_id, limit=200) if user_id else []
    posts = db_posts if db_posts else _read_json_list(POSTS_PATH)
    use_db = bool(db_posts)
    if not posts:
        return {
            'success': True,
            'message': 'No posts available to sync.',
            'synced': 0,
            'eligible_posts': 0,
            'errors': []
        }

    eligible_indices = []
    for idx in range(len(posts) - 1, -1, -1):
        post = posts[idx]
        if not bool(post.get('posted')):
            continue
        if bool(post.get('test_mode')):
            continue
        urn = _extract_linkedin_urn(post)
        if not urn:
            continue
        eligible_indices.append((idx, urn))

    eligible_indices = eligible_indices[:max(1, int(max_posts or 25))]

    if not eligible_indices:
        return {
            'success': True,
            'message': 'No posted LinkedIn items with URNs found to sync yet.',
            'synced': 0,
            'eligible_posts': 0,
            'errors': []
        }

    poster = LinkedInPoster(test_mode=False, access_token=access_token, person_id=person_id)
    synced = 0
    errors = []
    forbidden_count = 0
    not_found_count = 0

    for idx, urn in eligible_indices:
        try:
            metrics = poster.fetch_post_analytics(urn)
        except Exception as exc:
            errors.append({'urn': urn, 'error': str(exc)})
            continue

        status = str(metrics.get('status') or '').lower()
        if status == 'ok':
            likes = int(metrics.get('likes') or 0)
            comments = int(metrics.get('comments') or 0)
            shares = int(metrics.get('shares') or 0)
            interactions = int(metrics.get('interactions') or (likes + comments + shares))

            post = posts[idx]
            analytics = post.get('analytics') if isinstance(post.get('analytics'), dict) else {}
            analytics.update({
                'linkedin_urn': urn,
                'likes': likes,
                'comments': comments,
                'shares': shares,
                'interactions': interactions,
                'fetched_at': datetime.utcnow().isoformat() + 'Z',
                'source': 'linkedin_social_actions',
            })

            post['analytics'] = analytics
            post['linkedin_urn'] = urn
            post['likes'] = likes
            post['comments'] = comments
            post['shares'] = shares
            post['interactions'] = interactions
            synced += 1
            continue

        if status == 'forbidden':
            forbidden_count += 1
        elif status == 'not_found':
            not_found_count += 1
        else:
            errors.append({'urn': urn, 'error': metrics.get('error') or 'Unknown sync error'})

    if synced > 0:
        if use_db:
            # Update analytics in DB for each synced post
            for idx, urn in eligible_indices:
                post = posts[idx]
                if post.get('analytics') and post.get('id'):
                    _db_update_post(post['id'], {
                        'analytics': post['analytics'],
                        'linkedin_urn': urn,
                    })
        _write_json_list(POSTS_PATH, posts)

    message_parts = [f'Synced {synced} of {len(eligible_indices)} eligible posts.']
    if forbidden_count:
        message_parts.append(
            f'{forbidden_count} blocked by LinkedIn API permissions for analytics on member content.'
        )
    if not_found_count:
        message_parts.append(f'{not_found_count} posts could not be resolved on LinkedIn with current token access.')
    if errors:
        message_parts.append(f'{len(errors)} post(s) failed due to API/runtime errors.')

    return {
        'success': True,
        'message': ' '.join(message_parts),
        'synced': synced,
        'eligible_posts': len(eligible_indices),
        'forbidden_count': forbidden_count,
        'not_found_count': not_found_count,
        'errors': errors[:10]
    }


def _kb_usage_label(kb_mode: str, kb_used) -> str:
    mode = str(kb_mode or '').strip().lower()
    if mode == 'specific_files':
        return 'Selected KB files'
    if mode == 'no_kb':
        return 'General context'
    if kb_used is False:
        return 'General context'
    return 'All KB files'


def _extract_post_metadata(payload: dict) -> dict:
    raw = payload if isinstance(payload, dict) else {}
    generation_context = raw.get('generation_context') if isinstance(raw.get('generation_context'), dict) else {}
    settings_applied = raw.get('settings_applied') if isinstance(raw.get('settings_applied'), dict) else {}

    audience_industry = (
        raw.get('audience_industry')
        or raw.get('industry')
        or generation_context.get('audience_industry')
        or generation_context.get('industry')
        or settings_applied.get('industry')
        or ''
    )
    professional_role = (
        raw.get('professional_role')
        or raw.get('role')
        or generation_context.get('professional_role')
        or generation_context.get('role')
        or settings_applied.get('role')
        or ''
    )

    kb_mode = (
        raw.get('kb_mode')
        or generation_context.get('kb_mode')
        or settings_applied.get('kb_mode')
        or 'use_kb'
    )
    kb_used = raw.get('kb_used')
    if kb_used is None:
        kb_used = generation_context.get('kb_used')
    if kb_used is None:
        kb_used = settings_applied.get('kb_used')

    knowledge_base_used = (
        raw.get('knowledge_base_used')
        or generation_context.get('knowledge_base_used')
        or _kb_usage_label(kb_mode, kb_used)
    )

    workspace_id = (
        raw.get('workspace_id')
        or generation_context.get('workspace_id')
        or settings_applied.get('workspace_id')
        or ''
    )

    return {
        'audience_industry': str(audience_industry or '').strip(),
        'professional_role': str(professional_role or '').strip(),
        'knowledge_base_used': str(knowledge_base_used or '').strip(),
        'kb_mode': str(kb_mode or 'use_kb').strip(),
        'workspace_id': str(workspace_id or '').strip()
    }


def _default_presets() -> list:
    return [
        {
            'id': 'preset_thought_leadership',
            'name': 'Thought leadership',
            'settings': {
                'hashtags': 4,
                'emojis': 'minimal',
                'topics': ['trends', 'questions'],
                'word_count_mode': 'custom_range',
                'min_words': 140,
                'max_words': 190,
                'kb_mode': 'use_kb'
            }
        },
        {
            'id': 'preset_technical_deep_dive',
            'name': 'Technical deep dive',
            'settings': {
                'hashtags': 3,
                'emojis': 'none',
                'topics': ['tips', 'product'],
                'word_count_mode': 'custom_range',
                'min_words': 180,
                'max_words': 260,
                'kb_mode': 'use_kb'
            }
        },
        {
            'id': 'preset_short_punchy',
            'name': 'Short punchy',
            'settings': {
                'hashtags': 3,
                'emojis': 'minimal',
                'topics': ['questions'],
                'word_count_mode': 'custom_range',
                'min_words': 70,
                'max_words': 120,
                'kb_mode': 'no_kb'
            }
        }
    ]


def _normalize_workspace_payload(payload: dict, existing_id: str = None) -> dict:
    name = (payload.get('name') or '').strip()
    if not name:
        name = 'New Workspace'
    name = name[:60]

    raw_file_ids = payload.get('file_ids') or []
    if not isinstance(raw_file_ids, list):
        raw_file_ids = []
    file_ids = []
    seen = set()
    for file_id in raw_file_ids:
        val = str(file_id or '').strip()
        if not val or val in seen:
            continue
        seen.add(val)
        file_ids.append(val)

    use_all_files = bool(payload.get('use_all_files', False))
    workspace_id = existing_id or f"ws_{uuid4().hex[:12]}"

    return {
        'id': workspace_id,
        'name': name,
        'use_all_files': use_all_files,
        'file_ids': [] if use_all_files else file_ids,
        'updated_at': int(time.time())
    }


def _ensure_user_feature_blob(user_id: str) -> dict:
    with FEATURE_STORE_LOCK:
        blob = _read_feature_blob_for_user(user_id)

        if not blob.get('kb_workspaces'):
            blob['kb_workspaces'] = [
                {
                    'id': 'ws_all_files',
                    'name': 'All Files',
                    'use_all_files': True,
                    'file_ids': [],
                    'updated_at': int(time.time())
                }
            ]

        if not blob.get('generation_presets'):
            blob['generation_presets'] = _default_presets()

        blob['updated_at'] = int(time.time())
        _write_feature_blob_for_user(user_id, blob)
        return blob


def _save_user_feature_blob(user_id: str, blob: dict) -> dict:
    with FEATURE_STORE_LOCK:
        blob['updated_at'] = int(time.time())
        _write_feature_blob_for_user(user_id, blob)
        return blob


def _get_workspace(blob: dict, workspace_id: str) -> dict:
    for ws in blob.get('kb_workspaces', []):
        if str(ws.get('id')) == str(workspace_id):
            return ws
    return {}


# ============= KNOWLEDGE BASE CONFIGURATION =============
MAX_DOCUMENTS_PER_USER = 100        # Maximum documents allowed
MAX_PDF_SIZE = 50 * 1024 * 1024     # 50 MB per file
MAX_TOTAL_FILE_SIZE = 500 * 1024 * 1024  # 500 MB total
MAX_TRAINING_TIME = 300             # 5 minutes timeout
KB_CHUNK_SIZE = 1800
KB_CHUNK_OVERLAP = 200
KB_MAX_CHUNKS_PER_FILE = 250
DEFAULT_TEST_USER_ID = '00000000-0000-0000-0000-000000000000'


# Track KB training per user to avoid concurrent heavy jobs
KB_TRAINING_LOCK = threading.Lock()
KB_TRAINING_USERS = set()
KB_TRAINING_STATE = {}


def is_kb_training(user_id: str) -> bool:
    with KB_TRAINING_LOCK:
        state = KB_TRAINING_STATE.get(user_id) or {}
        if user_id in KB_TRAINING_USERS:
            started_at = state.get('started_at')
            if isinstance(started_at, (int, float)) and (time.time() - started_at) > MAX_TRAINING_TIME:
                KB_TRAINING_USERS.discard(user_id)
                KB_TRAINING_STATE[user_id] = {
                    **state,
                    'in_progress': False,
                    'status': 'timeout',
                    'error': f'Training timed out after {MAX_TRAINING_TIME} seconds',
                    'finished_at': time.time()
                }
                return False
            return True
        return False


def get_kb_training_state(user_id: str) -> dict:
    with KB_TRAINING_LOCK:
        state = KB_TRAINING_STATE.get(user_id, {})
        return {
            'in_progress': user_id in KB_TRAINING_USERS,
            'status': state.get('status', 'idle'),
            'error': state.get('error'),
            'started_at': state.get('started_at'),
            'finished_at': state.get('finished_at')
        }


def set_kb_training(user_id: str, training: bool) -> None:
    with KB_TRAINING_LOCK:
        state = KB_TRAINING_STATE.get(user_id, {})
        if training:
            KB_TRAINING_USERS.add(user_id)
            KB_TRAINING_STATE[user_id] = {
                **state,
                'in_progress': True,
                'status': 'running',
                'error': None,
                'started_at': time.time(),
                'finished_at': None
            }
        else:
            KB_TRAINING_USERS.discard(user_id)
            KB_TRAINING_STATE[user_id] = {
                **state,
                'in_progress': False,
                'finished_at': time.time()
            }


def start_kb_training_job(user_id: str, target, *args, **kwargs) -> bool:
    """Start a background KB training/indexing job if one is not already running for the user."""
    if is_kb_training(user_id):
        return False

    set_kb_training(user_id, True)

    def runner():
        try:
            target(*args, **kwargs)
            with KB_TRAINING_LOCK:
                state = KB_TRAINING_STATE.get(user_id, {})
                KB_TRAINING_STATE[user_id] = {
                    **state,
                    'status': 'completed',
                    'error': None
                }
        except Exception as e:
            logger.exception("KB training job failed for user %s: %s", user_id, e)
            with KB_TRAINING_LOCK:
                state = KB_TRAINING_STATE.get(user_id, {})
                KB_TRAINING_STATE[user_id] = {
                    **state,
                    'status': 'failed',
                    'error': str(e)
                }
        finally:
            set_kb_training(user_id, False)

    threading.Thread(target=runner, daemon=True).start()
    return True


def _run_local_kb_training(user_id: str, mode: str = 'full', filepaths: list = None) -> None:
    from rag_system_pgvector import RAGStore
    from pdf_processor import load_document, chunk_text

    rag = RAGStore(user_id=user_id)
    mode_value = str(mode or 'full').strip().lower()

    if mode_value == 'full':
        existing_records = rag.db.list_kb_files(user_id)
        paths_to_process = []
        for record in existing_records:
            filepath = resolve_local_kb_path(
                record.get('storage_path') or '',
                record.get('filename') or '',
                user_id,
            )
            if filepath and os.path.isfile(filepath):
                paths_to_process.append(filepath)

        for existing in existing_records:
            rag.db.delete_kb_file(existing['id'])
    else:
        paths_to_process = [p for p in (filepaths or []) if p and os.path.isfile(p)]

    for filepath in paths_to_process:
        filename = os.path.basename(filepath)
        file_size = os.path.getsize(filepath)
        ext_lower = filename.lower()
        if ext_lower.endswith('.docx'):
            file_type = 'docx'
        elif ext_lower.endswith('.pptx'):
            file_type = 'pptx'
        elif ext_lower.endswith('.csv'):
            file_type = 'csv'
        elif ext_lower.endswith(('.txt', '.md')):
            file_type = 'txt'
        else:
            file_type = 'pdf'

        if mode_value == 'incremental':
            existing_records = [
                row for row in rag.db.list_kb_files(user_id)
                if row.get('filename') == filename
            ]
            for record in existing_records:
                rag.db.delete_kb_file(record['id'])

        file_record = rag.db.create_kb_file(user_id, {
            'filename': filename,
            'file_size_bytes': file_size,
            'file_type': file_type,
            'storage_path': f'local/pdfs/{user_id}/{filename}',
            'upload_status': 'processing',
        })

        source, text = load_document(filepath)
        if not text or not text.strip():
            rag.db.update_kb_file(file_record['id'], {
                'upload_status': 'failed',
                'error_message': 'No text could be extracted from document',
            })
            continue

        chunks = chunk_text(text, chunk_size=KB_CHUNK_SIZE, overlap=KB_CHUNK_OVERLAP)
        if len(chunks) > KB_MAX_CHUNKS_PER_FILE:
            chunks = chunks[:KB_MAX_CHUNKS_PER_FILE]

        docs_for_rag = [
            (source, chunk, {'filename': filename, 'chunk_number': idx + 1})
            for idx, chunk in enumerate(chunks)
        ]
        rag.build_from_documents(docs_for_rag, file_record['id'])


def _enqueue_or_start_kb_training(user_id: str, mode: str, filepaths: list = None) -> dict:
    queue_result = enqueue_kb_training_job(user_id, mode=mode, filepaths=filepaths or [])
    if queue_result.get('success'):
        return {
            'success': True,
            'via_queue': True,
            'training_job_id': queue_result.get('job_id'),
            'message': 'Training queued in worker'
        }

    if queue_result.get('already_running'):
        return {
            'success': False,
            'already_running': True,
            'message': queue_result.get('message', 'Training is already in progress. Please wait and refresh status.')
        }

    started = start_kb_training_job(user_id, _run_local_kb_training, user_id, mode, filepaths or [])
    if started:
        return {
            'success': True,
            'via_queue': False,
            'training_job_id': None,
            'message': 'Auto-indexing started in background mode'
        }

    return {
        'success': False,
        'already_running': True,
        'message': 'Training is already running in local background mode. Please wait and refresh status.'
    }

# ============= CONFIGURATION HELPERS =============

CONFIG_DEFAULTS = {
    'AI_PROVIDER': 'deepseek',
    'GOOGLE_API_KEY': '',
    'OPENAI_API_KEY': '',
    'ANTHROPIC_API_KEY': '',
    'LINKEDIN_ACCESS_TOKEN': '',
    'LINKEDIN_PERSON_ID': '',
    'LINKEDIN_CLIENT_ID': '',
    'LINKEDIN_CLIENT_SECRET': '',
    'TEST_MODE': 'true',
    'POST_TIME_HOUR': '11',
    'POST_TIME_MINUTE': '0',
    'TIMEZONE': 'Asia/Kolkata',
    'MIN_POST_LENGTH': '150',
    'MAX_POST_LENGTH': '1000',
    'MIN_POST_WORDS': '120',
    'MAX_POST_WORDS': '220',
    'POST_LENGTH_MODE': 'custom_range',
    'ENABLE_MARKET_GROUNDING': 'true',
    'ACTIVE_PERSONA': 'professional',
    'TONE': 'professional',
    'STYLE': 'formal',
    'EMOJI_USAGE': 'moderate',
    'HASHTAG_COUNT': '3',
    'LANGUAGE': 'English',
    'AUDIENCE_KEYWORDS': '',
    'CONTENT_TOPICS': '',
    'CONTENT_INDUSTRY': 'tech',
    'USER_ROLE': 'cto',
    'CUSTOM_TOPICS': '',
    'CONTENT_MAX_LENGTH': '1000',
    'ENABLE_EMOJI': 'true'
}

SENSITIVE_USER_CONFIG_KEYS = {
    'LINKEDIN_ACCESS_TOKEN', 'LINKEDIN_PERSON_ID'
}

PLATFORM_MANAGED_AI_KEYS = {
    'AI_PROVIDER',
    'GOOGLE_API_KEY',
    'OPENAI_API_KEY',
    'ANTHROPIC_API_KEY',
    'DEEPSEEK_API_KEY',
    'XAI_API_KEY',
}

USER_CONFIG_KEYS = set(CONFIG_DEFAULTS.keys()) - {
    'TEST_MODE', 'LINKEDIN_CLIENT_ID', 'LINKEDIN_CLIENT_SECRET'
} - PLATFORM_MANAGED_AI_KEYS


def _platform_ai_provider() -> str:
    return str(os.getenv('AI_PROVIDER', CONFIG_DEFAULTS.get('AI_PROVIDER', 'deepseek')) or 'deepseek').strip().lower()


def _build_platform_ai_provider() -> AIProvider:
    return AIProvider(_platform_ai_provider())


def _apply_platform_ai_config(config: dict) -> dict:
    config['AI_PROVIDER'] = _platform_ai_provider()
    config['GOOGLE_API_KEY'] = ''
    config['OPENAI_API_KEY'] = ''
    config['ANTHROPIC_API_KEY'] = ''
    return config


def _read_env_config_raw() -> dict:
    config = {}
    if os.path.exists('.env'):
        with open('.env', 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    config[key.strip()] = value.strip()

    for key, default in CONFIG_DEFAULTS.items():
        if key not in config:
            config[key] = default
    return config


def _normalize_config_types(config: dict) -> dict:
    normalized = dict(config or {})
    normalized['TEST_MODE'] = str(normalized.get('TEST_MODE', 'true')).lower() in ('true', '1')
    normalized['POST_TIME_HOUR'] = int(normalized.get('POST_TIME_HOUR', 11))
    normalized['POST_TIME_MINUTE'] = int(normalized.get('POST_TIME_MINUTE', 0))
    normalized['MIN_POST_LENGTH'] = int(normalized.get('MIN_POST_LENGTH', 150))
    normalized['MAX_POST_LENGTH'] = int(normalized.get('MAX_POST_LENGTH', 1000))
    normalized['MIN_POST_WORDS'] = int(normalized.get('MIN_POST_WORDS', 120))
    normalized['MAX_POST_WORDS'] = int(normalized.get('MAX_POST_WORDS', 220))
    if normalized['MAX_POST_WORDS'] < normalized['MIN_POST_WORDS']:
        normalized['MAX_POST_WORDS'] = normalized['MIN_POST_WORDS']
    normalized['ENABLE_MARKET_GROUNDING'] = str(normalized.get('ENABLE_MARKET_GROUNDING', 'true')).lower() in ('true', '1')
    return normalized


def _serialize_config_value(key: str, value):
    if isinstance(value, bool):
        return 'true' if value else 'false'
    return str(value if value is not None else CONFIG_DEFAULTS.get(key, ''))


def _is_user_config_eligible(user_id: str) -> bool:
    return bool(user_id and is_valid_uuid(user_id))


def _get_user_config_overrides(user_id: str) -> dict:
    if not _is_user_config_eligible(user_id):
        return {}
    blob = _ensure_user_feature_blob(user_id)
    overrides = blob.get('user_config') if isinstance(blob.get('user_config'), dict) else {}
    # Decrypt sensitive keys on read
    result = dict(overrides)
    for key in SENSITIVE_USER_CONFIG_KEYS:
        if key in result and is_encrypted(result[key]):
            result[key] = decrypt_value(result[key])
    return result


def _save_user_config_overrides(user_id: str, config: dict) -> None:
    if not _is_user_config_eligible(user_id):
        return
    blob = _ensure_user_feature_blob(user_id)
    existing = blob.get('user_config') if isinstance(blob.get('user_config'), dict) else {}
    updated = dict(existing)
    for key in USER_CONFIG_KEYS:
        if key in config:
            value = _serialize_config_value(key, config.get(key))
            # Encrypt sensitive keys before persisting
            if key in SENSITIVE_USER_CONFIG_KEYS and value:
                value = encrypt_value(value)
            updated[key] = value
    blob['user_config'] = updated
    _save_user_feature_blob(user_id, blob)


def load_config(user_id: str = ''):
    """Load configuration from .env, with per-user overrides when user_id is provided."""
    config = _read_env_config_raw()

    if _is_user_config_eligible(user_id):
        for key in USER_CONFIG_KEYS:
            config[key] = CONFIG_DEFAULTS.get(key, '')
        user_overrides = _get_user_config_overrides(user_id)
        for key, value in user_overrides.items():
            if key in USER_CONFIG_KEYS and key in CONFIG_DEFAULTS:
                config[key] = value

    config = _normalize_config_types(config)
    return _apply_platform_ai_config(config)


def save_config(config, user_id: str = ''):
    """Save configuration to per-user overrides (preferred) or global .env."""
    if _is_user_config_eligible(user_id):
        _save_user_config_overrides(user_id, config)
        return

    env_content = f"""AI_PROVIDER={_serialize_config_value('AI_PROVIDER', config.get('AI_PROVIDER'))}
GOOGLE_API_KEY={_serialize_config_value('GOOGLE_API_KEY', config.get('GOOGLE_API_KEY'))}
OPENAI_API_KEY={_serialize_config_value('OPENAI_API_KEY', config.get('OPENAI_API_KEY'))}
ANTHROPIC_API_KEY={_serialize_config_value('ANTHROPIC_API_KEY', config.get('ANTHROPIC_API_KEY'))}
LINKEDIN_ACCESS_TOKEN={_serialize_config_value('LINKEDIN_ACCESS_TOKEN', config.get('LINKEDIN_ACCESS_TOKEN'))}
LINKEDIN_PERSON_ID={_serialize_config_value('LINKEDIN_PERSON_ID', config.get('LINKEDIN_PERSON_ID'))}
LINKEDIN_CLIENT_ID={_serialize_config_value('LINKEDIN_CLIENT_ID', config.get('LINKEDIN_CLIENT_ID'))}
LINKEDIN_CLIENT_SECRET={_serialize_config_value('LINKEDIN_CLIENT_SECRET', config.get('LINKEDIN_CLIENT_SECRET'))}
TEST_MODE={_serialize_config_value('TEST_MODE', config.get('TEST_MODE'))}
POST_TIME_HOUR={_serialize_config_value('POST_TIME_HOUR', config.get('POST_TIME_HOUR'))}
POST_TIME_MINUTE={_serialize_config_value('POST_TIME_MINUTE', config.get('POST_TIME_MINUTE'))}
TIMEZONE={_serialize_config_value('TIMEZONE', config.get('TIMEZONE'))}
MIN_POST_LENGTH={_serialize_config_value('MIN_POST_LENGTH', config.get('MIN_POST_LENGTH'))}
MAX_POST_LENGTH={_serialize_config_value('MAX_POST_LENGTH', config.get('MAX_POST_LENGTH'))}
MIN_POST_WORDS={_serialize_config_value('MIN_POST_WORDS', config.get('MIN_POST_WORDS', 120))}
MAX_POST_WORDS={_serialize_config_value('MAX_POST_WORDS', config.get('MAX_POST_WORDS', 220))}
POST_LENGTH_MODE={_serialize_config_value('POST_LENGTH_MODE', config.get('POST_LENGTH_MODE', 'custom_range'))}
ENABLE_MARKET_GROUNDING={_serialize_config_value('ENABLE_MARKET_GROUNDING', config.get('ENABLE_MARKET_GROUNDING'))}
ACTIVE_PERSONA={_serialize_config_value('ACTIVE_PERSONA', config.get('ACTIVE_PERSONA', 'professional'))}
TONE={_serialize_config_value('TONE', config.get('TONE', 'professional'))}
STYLE={_serialize_config_value('STYLE', config.get('STYLE', 'formal'))}
EMOJI_USAGE={_serialize_config_value('EMOJI_USAGE', config.get('EMOJI_USAGE', 'moderate'))}
HASHTAG_COUNT={_serialize_config_value('HASHTAG_COUNT', config.get('HASHTAG_COUNT', '3'))}
LANGUAGE={_serialize_config_value('LANGUAGE', config.get('LANGUAGE', 'English'))}
AUDIENCE_KEYWORDS={_serialize_config_value('AUDIENCE_KEYWORDS', config.get('AUDIENCE_KEYWORDS', ''))}
CONTENT_TOPICS={_serialize_config_value('CONTENT_TOPICS', config.get('CONTENT_TOPICS', ''))}
CONTENT_INDUSTRY={_serialize_config_value('CONTENT_INDUSTRY', config.get('CONTENT_INDUSTRY', 'tech'))}
USER_ROLE={_serialize_config_value('USER_ROLE', config.get('USER_ROLE', 'cto'))}
CUSTOM_TOPICS={_serialize_config_value('CUSTOM_TOPICS', config.get('CUSTOM_TOPICS', ''))}
CONTENT_MAX_LENGTH={_serialize_config_value('CONTENT_MAX_LENGTH', config.get('CONTENT_MAX_LENGTH', '1000'))}
ENABLE_EMOJI={_serialize_config_value('ENABLE_EMOJI', config.get('ENABLE_EMOJI', 'true'))}
"""
    with open('.env', 'w') as f:
        f.write(env_content)

# ============= SCHEDULER FUNCTIONS =============

def scheduled_post_job():
    """Job to run daily automated posting"""
    try:
        logger.info("Running daily scheduled post job")
        
        # Generate and post new content (existing logic)
        config_obj = load_config()
        if config_obj['TEST_MODE']:
            logger.info("Skipping daily post generation - TEST_MODE is enabled")
            return
            
        # Generate content directly (simplified version)
        user_industry = str(config_obj.get('CONTENT_INDUSTRY', '') or '').strip()
        user_role = str(config_obj.get('USER_ROLE', '') or '').strip()
        ai = AIProvider()
        neutral_themes = [
            f"{user_industry or 'business'} trends and practical insights",
            f"{user_role or 'leadership'} execution strategies",
            "team productivity and process improvement",
            "scaling operations with better systems",
        ]
        theme = random.choice(neutral_themes)
        fmt = random.choice(POST_FORMATS)
        services = f"Professional insights for {user_industry or 'business'} audiences, {user_role or 'leadership'} perspective."

        # Simple prompt for post generation
        prompt = f"""Write a short LinkedIn post about: {theme}

Context: {services}
Format: {fmt}

Rules:\n- 120-180 words\n- Short punchy paragraphs (1-2 sentences each)\n- Natural human tone, no buzzwords\n- No markdown (no **, no bullets)\n- No hashtags in body\n- End with one open question to the reader"""

        result = ai.generate(prompt, max_tokens=500)
        content = result['text'].strip()
        
        # Generate some basic hashtags
        hashtags = ['#LinkedIn', '#Business', '#Innovation']
        if 'crypto' in theme.lower():
            hashtags.extend(['#Crypto', '#Blockchain', '#DigitalAssets'])
        if 'arab' in theme.lower():
            hashtags.extend(['#MiddleEast', '#UAE', '#Dubai'])
        
        # Post to LinkedIn
        poster = LinkedInPoster(test_mode=config_obj['TEST_MODE'])
        post_result = poster.post(content)
        
        # Save to posts history
        post_data = {
            'content': content,
            'hashtags': hashtags,
            'theme': theme,
            'created_at': datetime.now().isoformat(),
            'posted': post_result.get('status') == 'posted',
            'test_mode': config_obj['TEST_MODE'],
            'scheduled': True,
            'provider': post_result.get('provider') or 'linkedin',
            'linkedin_urn': post_result.get('linkedin_urn'),
            'publish_result': post_result.get('status'),
            'publish_response': post_result.get('response') if isinstance(post_result.get('response'), dict) else None,
            'audience_industry': str(config_obj.get('CONTENT_INDUSTRY', '') or '').strip(),
            'professional_role': str(config_obj.get('USER_ROLE', '') or '').strip(),
            'target_audience': str(config_obj.get('AUDIENCE_KEYWORDS', '') or '').strip(),
            'knowledge_base_used': 'General context',
            'kb_mode': 'no_kb',
            'workspace_id': ''
        }
        
        # Load existing posts
        posts = _read_json_list(POSTS_PATH)
        
        posts.append(post_data)
        
        # Save to DB (primary) + JSON (backup)
        _db_save_post('', post_data)
        _write_json_list(POSTS_PATH, posts)
        
        logger.info("Scheduled post completed: %s", "Posted" if post_result.get('status') == 'posted' else "Test mode")
        
    except Exception as e:
        logger.exception("Scheduled post job failed: %s", e)


def _prewarm_embedding_model():
    """Pre-warm the SentenceTransformer model in a background thread to avoid cold-start latency."""
    def _warm():
        try:
            from rag_system_pgvector import RAGStore
            dummy = RAGStore(user_id='00000000-0000-0000-0000-000000000000')
            model = dummy._get_model()
            if model is not None:
                logger.info('SentenceTransformer model pre-warmed successfully')
            else:
                logger.info('Embedding backend is hash-mode; no model to pre-warm')
        except Exception as e:
            logger.warning('SentenceTransformer pre-warm failed (non-fatal): %s', e)

    threading.Thread(target=_warm, daemon=True, name='embedding-prewarm').start()


def _run_subscription_expiry_reminder_batch():
    """Daily batch: send expiry reminders independent of user login."""
    try:
        if not auth_supabase:
            return

        result = auth_supabase.table('subscriptions').select(
            'user_id,plan,status,current_period_end,cancel_at_period_end'
        ).limit(2000).execute()
        rows = result.data or []
        if not rows:
            logger.info('Expiry reminder batch: no subscriptions found')
            return

        scanned = 0
        considered = 0
        sent = 0
        for sub in rows:
            scanned += 1
            user_id = str(sub.get('user_id') or '').strip()
            if not is_valid_uuid(user_id):
                continue

            status = str(sub.get('status') or '').strip().lower()
            if status not in {'active', 'trialing'}:
                continue

            plan = str(sub.get('plan') or '').strip().lower()
            if not plan or plan == 'free':
                continue

            period_end = _parse_iso_utc(sub.get('current_period_end'))
            if not period_end:
                continue

            now = datetime.utcnow()
            seconds_left = (period_end - now).total_seconds()
            days_remaining = 0 if seconds_left < 0 else int(seconds_left // 86400)
            if days_remaining not in {7, 3, 1, 0}:
                continue

            blob = _read_feature_blob_for_user(user_id)
            email = _resolve_notification_email(user_id, str((blob.get('user_config') or {}).get('email') or '').strip())
            if not email:
                continue

            reminders = blob.get('billing_reminders') if isinstance(blob.get('billing_reminders'), dict) else {}
            today_key = now.date().isoformat()
            last_sent_date = str(reminders.get('expiry_last_sent_date') or '').strip()
            last_sent_bucket = reminders.get('expiry_last_sent_days')
            if last_sent_date == today_key and int(last_sent_bucket or -1) == int(days_remaining):
                continue

            considered += 1
            _send_subscription_expiry_reminder(
                email,
                plan=plan,
                days_remaining=days_remaining,
                renewal_url=(os.getenv('APP_BASE_URL') or 'https://app.velank.io').rstrip('/') + '/#settings?tab=billing',
            )
            reminders['expiry_last_sent_date'] = today_key
            reminders['expiry_last_sent_days'] = int(days_remaining)
            blob['billing_reminders'] = reminders
            _write_feature_blob_for_user(user_id, blob)
            sent += 1

        logger.info(
            'Expiry reminder batch complete: scanned=%s considered=%s sent=%s',
            scanned,
            considered,
            sent,
        )
    except Exception as e:
        logger.exception('Expiry reminder batch failed: %s', e)


def _minor_to_display_amount(amount_minor: int) -> float:
    try:
        return round((int(amount_minor or 0) / 100.0), 2)
    except Exception:
        return 0.0


def _plan_price_minor(plan: str, currency: str = 'INR') -> int:
    normalized_currency = str(currency or 'INR').strip().upper()
    major_amount = _plan_price_inr(plan) if normalized_currency == 'INR' else _plan_price_usd(plan)
    return max(0, int(major_amount or 0) * 100)


def _subscription_transition_payload(subscription: dict):
    if not isinstance(subscription, dict):
        return None

    period_end = _parse_iso_utc(subscription.get('current_period_end'))
    if not period_end or period_end > datetime.utcnow():
        return None

    now = datetime.utcnow()
    scheduled_plan = str(subscription.get('scheduled_plan') or '').strip().lower()
    cancel_at_period_end = bool(subscription.get('cancel_at_period_end'))
    current_currency = str(subscription.get('current_plan_currency') or 'INR').strip().upper() or 'INR'

    if scheduled_plan:
        normalized = _normalize_subscription_plan(scheduled_plan)
        if normalized and normalized[0] != 'free':
            new_plan, months = normalized
            next_period_end = _add_months_utc(period_end, months)
            return {
                'plan': new_plan,
                'status': 'active',
                'current_period_start': period_end.isoformat() + 'Z',
                'current_period_end': next_period_end.isoformat() + 'Z',
                'cancel_at_period_end': False,
                'scheduled_plan': None,
                'current_plan_currency': current_currency,
                'current_plan_price_minor': _plan_price_minor(new_plan, current_currency),
                'updated_at': now.isoformat() + 'Z',
            }

    if cancel_at_period_end:
        return {
            'plan': 'free',
            'status': 'cancelled',
            'cancel_at_period_end': False,
            'scheduled_plan': None,
            'current_plan_currency': current_currency,
            'current_plan_price_minor': 0,
            'updated_at': now.isoformat() + 'Z',
        }

    if str(subscription.get('status') or '').strip().lower() in {'active', 'trialing'}:
        return {
            'status': 'expired',
            'updated_at': now.isoformat() + 'Z',
        }
    return None


def _apply_subscription_transition_if_due(subscription: dict) -> dict:
    payload = _subscription_transition_payload(subscription)
    if not payload or not auth_supabase:
        return subscription

    user_id = str(subscription.get('user_id') or '').strip()
    if not is_valid_uuid(user_id):
        return subscription

    try:
        auth_supabase.table('subscriptions').update(payload).eq('user_id', user_id).execute()
        updated = dict(subscription)
        updated.update(payload)
        return updated
    except Exception as e:
        logger.warning('Subscription transition apply failed for user %s: %s', user_id, e)
        return subscription


def _run_subscription_transition_batch():
    """Apply due cancel/downgrade/expiry transitions independent of user activity."""
    try:
        if not auth_supabase:
            return
        rows = auth_supabase.table('subscriptions').select('*').limit(2000).execute().data or []
        transitioned = 0
        for subscription in rows:
            payload = _subscription_transition_payload(subscription)
            if not payload:
                continue
            updated = _apply_subscription_transition_if_due(subscription)
            if updated is not subscription:
                transitioned += 1
        logger.info('Subscription transition batch complete: scanned=%s transitioned=%s', len(rows), transitioned)
    except Exception as e:
        logger.exception('Subscription transition batch failed: %s', e)


def start_scheduler():
    """Start the background scheduler - runs even in TEST_MODE but marks posts appropriately"""
    global _SCHEDULER_THREAD, _SCHEDULER_HEARTBEAT

    def scheduler_thread():
        global _SCHEDULER_HEARTBEAT
        config = load_config()
        tz = pytz.timezone(config['TIMEZONE'])
        schedule_time = f"{config['POST_TIME_HOUR']:02d}:{config['POST_TIME_MINUTE']:02d}"
        reminder_batch_time = str(os.getenv('EXPIRY_REMINDER_BATCH_TIME', '09:15')).strip()

        # Guard against invalid HH:MM env value.
        if not re.match(r'^\d{2}:\d{2}$', reminder_batch_time):
            reminder_batch_time = '09:15'
        
        # Always schedule daily jobs - TEST_MODE will be respected in the job itself
        schedule.every().day.at(schedule_time).do(scheduled_post_job)
        schedule.every().day.at(reminder_batch_time).do(_run_subscription_expiry_reminder_batch)
        schedule.every(30).minutes.do(_run_subscription_transition_batch)
        logger.info("✓ Daily scheduler started - will post daily at %s %s (TEST_MODE: %s)", schedule_time, config['TIMEZONE'], config['TEST_MODE'])
        logger.info(
            "✓ Expiry reminder batch scheduled daily at %s %s (ENV EXPIRY_REMINDER_BATCH_TIME=%s)",
            reminder_batch_time,
            config['TIMEZONE'],
            os.getenv('EXPIRY_REMINDER_BATCH_TIME', '09:15'),
        )
        logger.info("✓ Subscription transition batch scheduled every 30 minutes")
        
        while True:
            _SCHEDULER_HEARTBEAT = time.time()
            try:
                # Always check for UI-scheduled posts
                config = load_config()  # Reload config
                check_scheduled_posts()  # Always check - function respects TEST_MODE
                
                # Run any pending scheduled jobs (daily posts)
                schedule.run_pending()
            except Exception as loop_err:
                logger.exception('Scheduler loop iteration failed (will retry): %s', loop_err)
            time.sleep(20)  # Check every 20 seconds for better schedule precision
    
    def check_scheduled_posts():
        """Check and post any due scheduled posts"""
        try:
            scheduled_posts = _read_json_list(SCHEDULED_POSTS_PATH)
            current_time = datetime.now()
            pending_posts = []
            due_count = 0
            posted_count = 0

            for post in scheduled_posts:
                schedule_time = _parse_schedule_datetime(post.get('schedule_time'))
                if schedule_time == datetime.min or current_time < schedule_time:
                    pending_posts.append(post)
                    continue

                due_count += 1

                try:
                    from linkedin_poster import LinkedInPoster

                    scheduled_user_id = str(post.get('user_id') or '').strip()
                    user_cfg = load_config(scheduled_user_id) if scheduled_user_id else load_config()
                    access_token = str(user_cfg.get('LINKEDIN_ACCESS_TOKEN') or '').strip()
                    person_id = str(user_cfg.get('LINKEDIN_PERSON_ID') or '').strip()

                    # Backward compatibility for legacy scheduled rows without owner id
                    if not access_token or not person_id:
                        fallback_user_id = _find_fallback_user_with_linkedin_config()
                        if fallback_user_id:
                            fallback_cfg = load_config(fallback_user_id)
                            fallback_token = str(fallback_cfg.get('LINKEDIN_ACCESS_TOKEN') or '').strip()
                            fallback_person_id = str(fallback_cfg.get('LINKEDIN_PERSON_ID') or '').strip()
                            if fallback_token and fallback_person_id:
                                scheduled_user_id = fallback_user_id
                                post['user_id'] = fallback_user_id
                                access_token = fallback_token
                                person_id = fallback_person_id

                    if not access_token or not person_id:
                        post['last_error'] = 'Missing LinkedIn credentials for the scheduled post owner'
                        post['last_attempt_at'] = datetime.utcnow().isoformat() + 'Z'
                        pending_posts.append(post)
                        logger.warning("Scheduled post skipped (missing creds). id=%s user_id=%s", post.get('id'), scheduled_user_id)
                        continue

                    poster = LinkedInPoster(
                        test_mode=False,
                        access_token=access_token,
                        person_id=person_id
                    )
                    result = poster.post(post['content'])

                    logger.info("Posted scheduled post id=%s result=%s", post.get('id'), result.get('status'))

                    post_data = {
                        'content': post['content'],
                        'hashtags': post.get('hashtags', []),
                        'theme': 'scheduled',
                        'created_at': datetime.now().isoformat(),
                        'posted': result.get('status') == 'posted',
                        'test_mode': False,
                        'scheduled': True,
                        'provider': result.get('provider') or 'linkedin',
                        'linkedin_urn': result.get('linkedin_urn'),
                        'publish_result': result.get('status'),
                        'publish_response': result.get('response') if isinstance(result.get('response'), dict) else None,
                        'user_id': scheduled_user_id,
                        **_extract_post_metadata(post)
                    }

                    posts = _read_json_list(POSTS_PATH)
                    posts.append(post_data)
                    _db_save_post(scheduled_user_id, post_data)
                    _write_json_list(POSTS_PATH, posts)
                    # Mark scheduled post done in DB
                    _db_mark_scheduled_post_done(post.get('id'), status='published')
                    posted_count += 1
                    # ── Notify user about published post ──────────────────────
                    try:
                        _s_user_blob = _read_feature_blob_for_user(scheduled_user_id)
                        _s_email = str((_s_user_blob.get('user_config') or {}).get('email') or '').strip()
                        if _s_email:
                            _send_post_published(
                                _s_email,
                                post_title=str(post.get('content') or '')[:80],
                                post_url=str(result.get('linkedin_urn') or ''),
                            )
                    except Exception:
                        pass  # notification is best-effort
                except Exception as post_error:
                    post['last_error'] = str(post_error)
                    post['last_attempt_at'] = datetime.utcnow().isoformat() + 'Z'
                    pending_posts.append(post)
                    _db_mark_scheduled_post_done(post.get('id'), status='failed', error=str(post_error))
                    logger.exception("Scheduled post failed id=%s: %s", post.get('id'), post_error)

            _write_json_list(SCHEDULED_POSTS_PATH, pending_posts)
            if due_count > 0:
                logger.info("Scheduled posts processed. due=%s posted=%s remaining=%s", due_count, posted_count, len(pending_posts))
                    
        except Exception as e:
            logger.exception("Error processing scheduled posts: %s", e)
    
    thread = threading.Thread(target=scheduler_thread, daemon=True, name='mantraj-scheduler')
    thread.start()
    _SCHEDULER_THREAD = thread
    logger.info("Scheduler thread started")


def start_auth_keepalive():
    """Keep auth upstream warm to reduce idle-time login failures."""
    enabled_raw = (os.getenv('AUTH_KEEPALIVE_ENABLED') or 'true').strip().lower()
    if enabled_raw not in {'1', 'true', 'yes', 'on'}:
        logger.info("Auth keepalive disabled")
        return

    interval_raw = (os.getenv('AUTH_KEEPALIVE_INTERVAL_SEC') or '900').strip()
    try:
        interval_sec = max(60, int(interval_raw))
    except Exception:
        interval_sec = 900

    def keepalive_loop():
        ok, detail = auth_healthcheck()
        if ok:
            logger.info("Auth keepalive startup check passed: %s", detail)
        else:
            logger.warning("Auth keepalive startup check failed: %s", detail)

        while True:
            time.sleep(interval_sec)
            try:
                ok, detail = auth_healthcheck()
                if ok:
                    logger.debug("Auth keepalive ok: %s", detail)
                else:
                    logger.warning("Auth keepalive warning: %s", detail)
            except Exception as exc:
                logger.warning("Auth keepalive exception: %s", exc)

    thread = threading.Thread(target=keepalive_loop, daemon=True)
    thread.start()
    logger.info("Auth keepalive thread started (interval=%ss)", interval_sec)


def _should_auto_start_background_services() -> bool:
    """Detect gunicorn/systemd execution without affecting normal imports or tests."""
    argv0 = os.path.basename((sys.argv or [''])[0] or '').lower()
    server_software = (os.getenv('SERVER_SOFTWARE') or '').strip().lower()
    return 'gunicorn' in argv0 or 'gunicorn' in server_software


def ensure_background_services_started() -> bool:
    """
    Start scheduler/keepalive once per host process group.

    Production runs gunicorn with 2 workers under systemd. If every worker starts
    its own scheduler thread, scheduled posts and keepalive checks run multiple
    times. Use a non-blocking file lock so exactly one gunicorn worker owns the
    background threads, while plain `python app.py` keeps working as before.
    """
    global _BACKGROUND_SERVICES_STARTED, _BACKGROUND_SERVICES_LOCK_FD

    with BACKGROUND_SERVICES_LOCK:
        if _BACKGROUND_SERVICES_STARTED:
            return True

        lock_fd = None
        if fcntl is not None:
            lock_path = os.getenv('BACKGROUND_SERVICES_LOCK_PATH', '/tmp/mantraj-background-services.lock')
            try:
                lock_fd = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o644)
                fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError:
                if lock_fd is not None:
                    try:
                        os.close(lock_fd)
                    except OSError:
                        pass
                logger.info("Background services already owned by another process; skipping startup in pid=%s", os.getpid())
                return False

        start_scheduler()
        start_auth_keepalive()

        # Pre-warm SentenceTransformer model to avoid cold-start latency on first KB query
        _prewarm_embedding_model()

        _BACKGROUND_SERVICES_STARTED = True
        _BACKGROUND_SERVICES_LOCK_FD = lock_fd
        logger.info("Background services started in pid=%s", os.getpid())
        return True


if _should_auto_start_background_services():
    ensure_background_services_started()


def get_current_user_id():
    """Get current authenticated user_id; optional test fallback only when explicitly enabled."""
    try:
        if hasattr(g, 'user_id'):
            return g.user_id
    except (RuntimeError, AttributeError):
        pass

    # Try resolving from Bearer token when route is not decorated with @require_auth
    try:
        auth_header = request.headers.get('Authorization', '')
        if auth_header.lower().startswith('bearer '):
            token = auth_header[7:].strip()
            user = verify_token(token)
            if user and is_valid_uuid(user.get('id')):
                return user['id']
    except Exception:
        pass
    
    # Optional fallback for local-only testing. Disabled by default for production safety.
    allow_test_fallback = (os.getenv('ALLOW_TEST_USER_FALLBACK', '').strip().lower() in ('1', 'true', 'yes', 'on'))
    test_mode_enabled = (os.getenv('TEST_MODE', '').strip().lower() in ('1', 'true', 'yes', 'on'))
    if allow_test_fallback and test_mode_enabled:
        fallback_user_id = os.getenv('TEST_USER_ID', DEFAULT_TEST_USER_ID)
        if not is_valid_uuid(fallback_user_id):
            logger.warning("Invalid TEST_USER_ID '%s'; using default UUID test user", fallback_user_id)
            return DEFAULT_TEST_USER_ID
        return fallback_user_id

    return ''


def ensure_kb_user_id() -> str:
    """Return a valid authenticated user_id for KB operations, else empty string."""
    user_id = get_current_user_id()
    if not is_valid_uuid(user_id):
        return ''
    if user_id == DEFAULT_TEST_USER_ID:
        return ''
    return user_id


def is_valid_uuid(value: str) -> bool:
    try:
        UUID(str(value))
        return True
    except Exception:
        return False


def _add_months_utc(start_dt: datetime, months: int) -> datetime:
    base = start_dt
    year = base.year + (base.month - 1 + months) // 12
    month = (base.month - 1 + months) % 12 + 1
    day = min(base.day, calendar.monthrange(year, month)[1])
    return base.replace(year=year, month=month, day=day)


def _normalize_subscription_plan(plan_raw: str):
    value = str(plan_raw or '').strip().lower()
    plan_map = {
        'free': ('free', 0),
        # Canonical plan names
        'starter': ('starter', 1),
        'creator': ('creator', 2),
        'pro': ('pro', 3),
        # Legacy / billing-period aliases
        '1m': ('starter', 1),
        '1_month': ('starter', 1),
        'monthly': ('starter', 1),
        '3m': ('creator', 2),
        '3_month': ('creator', 2),
        'quarterly': ('creator', 2),
        '12m': ('pro', 3),
        '12_month': ('pro', 3),
        'yearly': ('pro', 3),
        'annual': ('pro', 3),
        'agency': ('pro', 3),
    }
    return plan_map.get(value)


PLAN_LIMITS = load_freemium_plan_limits()


def _plan_price_inr(plan: str, region: str = 'IN') -> int:
    normalized = _normalize_subscription_plan(plan)
    key = normalized[0] if normalized else 'starter'
    # Map canonical plan names to env vars (reuse existing env var names)
    env_map = {
        'starter': 'PLAN_PRICE_STARTER_INR',
        'creator': 'PLAN_PRICE_CREATOR_INR',
        'pro': 'PLAN_PRICE_PRO_INR',
    }
    default_map = {
        'starter': int(os.getenv('PLAN_PRICE_STARTER_INR', 599)),
        'creator': int(os.getenv('PLAN_PRICE_CREATOR_INR', 1299)),
        'pro': int(os.getenv('PLAN_PRICE_PRO_INR', 4999)),
    }
    env_key = env_map.get(key)
    if not env_key:
        return 0
    try:
        value = int(str(os.getenv(env_key, default_map[key])).strip())
        return max(0, value)
    except Exception:
        return default_map[key]


def _plan_price_usd(plan: str) -> int:
    normalized = _normalize_subscription_plan(plan)
    key = normalized[0] if normalized else 'starter'
    env_map = {
        'starter': 'PLAN_PRICE_STARTER_USD',
        'creator': 'PLAN_PRICE_CREATOR_USD',
        'pro': 'PLAN_PRICE_PRO_USD',
    }
    default_map = {
        'starter': int(os.getenv('PLAN_PRICE_STARTER_USD', 19)),
        'creator': int(os.getenv('PLAN_PRICE_CREATOR_USD', 29)),
        'pro': int(os.getenv('PLAN_PRICE_PRO_USD', 49)),
    }
    env_key = env_map.get(key)
    if not env_key:
        return 0
    try:
        value = int(str(os.getenv(env_key, default_map[key])).strip())
        return max(0, value)
    except Exception:
        return default_map[key]


def _plan_checkout_price(plan: str, region: str = 'IN') -> tuple:
    region_key = str(region or 'IN').strip().upper()
    if region_key == 'ROW':
        return _plan_price_usd(plan), 'USD'
    return _plan_price_inr(plan), 'INR'


def _get_plan_limits(plan: str) -> dict:
    normalized = _normalize_subscription_plan(plan)
    key = normalized[0] if normalized else 'free'
    # Try canonical key first (e.g. 'starter', 'creator')
    if key in PLAN_LIMITS:
        return PLAN_LIMITS[key]
    # Fallback: try legacy keys that may exist in older plan_limits.json on server
    legacy_map = {'starter': '1_month', 'creator': '3_month', 'pro': '12_month'}
    legacy_key = legacy_map.get(key)
    if legacy_key and legacy_key in PLAN_LIMITS:
        return PLAN_LIMITS[legacy_key]
    return PLAN_LIMITS.get('free', {})


def _plan_limit_int(limits: dict, key: str, default_value: int) -> int:
    if not isinstance(limits, dict):
        return max(0, int(default_value))
    raw = limits.get(key)
    if raw is None:
        return max(0, int(default_value))
    text = str(raw).strip()
    if text == '':
        return max(0, int(default_value))
    try:
        return max(0, int(text))
    except Exception:
        return max(0, int(default_value))


def _single_value(raw_value: str) -> str:
    text = str(raw_value or '').strip()
    if not text:
        return ''
    first = re.split(r'[,|;\n]+', text)[0].strip()
    return first[:80]


_INDUSTRY_LABELS = {
    'tech': 'Technology & Software',
    'technology': 'Technology & Software',
    'technology_software': 'Technology & Software',
    'finance': 'Finance & Banking',
    'financial_services': 'Finance & Banking',
    'healthcare': 'Healthcare & Pharma',
    'health': 'Healthcare & Pharma',
    'ecommerce': 'E-Commerce & Retail',
    'e_commerce': 'E-Commerce & Retail',
    'retail': 'E-Commerce & Retail',
    'crypto': 'Cryptocurrency & Blockchain',
    'cryptocurrency': 'Cryptocurrency & Blockchain',
    'web3': 'Cryptocurrency & Blockchain',
    'blockchain': 'Cryptocurrency & Blockchain',
    'saas': 'SaaS & Startups',
    'startups': 'SaaS & Startups',
    'startup': 'SaaS & Startups',
    'genai': 'GenAI',
    'generative_ai': 'GenAI',
    'virtual_assistant': 'Virtual Assistant',
    'supply_chain': 'Supply Chain & Logistics',
}

_ROLE_LABELS = {
    'ceo': 'CEO / Founder',
    'founder': 'CEO / Founder',
    'ceo_founder': 'CEO / Founder',
    'cto': 'CTO / VP Engineering',
    'vp_engineering': 'CTO / VP Engineering',
    'dev': 'Software Developer',
    'developer': 'Software Developer',
    'software_developer': 'Software Developer',
    'engineer': 'Software Developer',
    'pm': 'Product Manager',
    'product_manager': 'Product Manager',
    'hr': 'HR / People Ops',
    'people_ops': 'HR / People Ops',
    'finance': 'Finance / CFO',
    'cfo': 'Finance / CFO',
    'ops': 'Operations',
    'operations': 'Operations',
    'marketing': 'Marketing / Growth',
    'growth': 'Marketing / Growth',
    'sales': 'Sales / BD',
    'bd': 'Sales / BD',
    'bde': 'Sales / BD',
    'business_development': 'Sales / BD',
}

_GOAL_KEY_TO_LABEL = {
    'spark_comments': 'Spark Comments & Discussion',
    'drive_profile_visits': 'Drive Profile Visits',
    'generate_leads': 'Generate Leads',
    'build_authority': 'Build Thought Leadership',
    'grow_network': 'Grow Network',
    'educate_audience': 'Educate Audience',
    'brand_awareness': 'Brand Awareness',
    'general_engagement': 'General Engagement',
}

_GOAL_ALIASES = {
    'spark_comments': 'spark_comments',
    'spark_comments_discussion': 'spark_comments',
    'spark_discussion': 'spark_comments',
    'comments': 'spark_comments',
    'drive_visits': 'drive_profile_visits',
    'drive_profile_visits': 'drive_profile_visits',
    'profile_visits': 'drive_profile_visits',
    'drive_visibility': 'drive_profile_visits',
    'generate_leads': 'generate_leads',
    'lead_gen': 'generate_leads',
    'build_authority': 'build_authority',
    'build_thought_leadership': 'build_authority',
    'thought_leadership': 'build_authority',
    'grow_network': 'grow_network',
    'network_growth': 'grow_network',
    'educate': 'educate_audience',
    'educate_audience': 'educate_audience',
    'brand_awareness': 'brand_awareness',
    'awareness': 'brand_awareness',
    'general_engagement': 'general_engagement',
}


def _normalize_taxonomy_label(raw_value: str, label_map: dict) -> str:
    text = _single_value(raw_value)
    if not text:
        return ''
    normalized_key = re.sub(r'[^a-z0-9]+', '_', text.strip().lower()).strip('_')
    if normalized_key in label_map:
        return label_map[normalized_key]
    return text


def _normalize_tone_value(raw_tone: str) -> str:
    tone = str(raw_tone or 'professional').strip().lower().replace('-', '_').replace(' ', '_')
    tone_aliases = {
        'thoughtleader': 'authoritative',
        'authoritative': 'authoritative',
        'professional': 'professional',
        'conversational': 'conversational',
        'contrarian': 'contrarian',
        'educational': 'educational',
        'storytelling': 'storytelling',
        'inspirational': 'professional',  # Map legacy inspirational to professional
    }
    return tone_aliases.get(tone, 'professional')


def _normalize_goal(raw_goal: str):
    text = str(raw_goal or '').strip()
    if not text:
        return 'general_engagement', _GOAL_KEY_TO_LABEL['general_engagement']
    key = re.sub(r'[^a-z0-9]+', '_', text.lower()).strip('_')
    canonical = _GOAL_ALIASES.get(key, key)
    if canonical not in _GOAL_KEY_TO_LABEL:
        return 'general_engagement', text
    return canonical, _GOAL_KEY_TO_LABEL[canonical]


def _normalize_style_clone_mode(raw_mode: str) -> str:
    mode = str(raw_mode or 'hybrid').strip().lower().replace(' ', '_').replace('-', '_')
    if mode in {'off', 'disabled', 'none'}:
        return 'off'
    if mode in {'strict', 'full'}:
        return 'strict'
    return 'hybrid'


# ── Instruction Pack Loader ────────────────────────────────────────────────────
_INSTRUCTION_PACKS = None
_PACK_PATH = Path(__file__).resolve().parent / 'data' / 'instruction_packs.json'
_pack_save_lock = threading.Lock()


def _load_instruction_packs():
    """Load instruction packs JSON once, cache in module global."""
    global _INSTRUCTION_PACKS
    if _INSTRUCTION_PACKS is not None:
        return _INSTRUCTION_PACKS
    try:
        with open(_PACK_PATH, 'r', encoding='utf-8') as f:
            _INSTRUCTION_PACKS = json.load(f)
    except Exception as e:
        logger.warning('Could not load instruction_packs.json: %s', e)
        _INSTRUCTION_PACKS = {}
    return _INSTRUCTION_PACKS


def _save_instruction_packs():
    """Persist the in-memory instruction packs back to disk (thread-safe)."""
    if not _INSTRUCTION_PACKS:
        return
    try:
        with _pack_save_lock:
            with open(_PACK_PATH, 'w', encoding='utf-8') as f:
                json.dump(_INSTRUCTION_PACKS, f, indent=2, ensure_ascii=False)
            logger.info('Instruction packs saved (%d industries, %d roles, %d goals)',
                        len(_INSTRUCTION_PACKS.get('industries', {})),
                        len(_INSTRUCTION_PACKS.get('roles', {})),
                        len(_INSTRUCTION_PACKS.get('goals', {})))
    except Exception as e:
        logger.warning('Could not save instruction_packs.json: %s', e)


def _resolve_pack_key(raw_value: str, section: dict) -> str:
    """Find the best matching key in a pack section for a raw value."""
    if not raw_value or not section:
        return ''
    key = re.sub(r'[^a-z0-9]+', '_', raw_value.strip().lower()).strip('_')
    if key in section:
        return key
    # Fuzzy: try to match by label substring
    for k, v in section.items():
        label = str(v.get('label', '')).lower()
        if key in label or label in raw_value.lower():
            return k
    return ''


def _auto_generate_pack_entry(entry_type: str, raw_label: str, config_obj: dict) -> dict:
    """Use AI to generate a new instruction pack entry for an unknown industry or role.

    entry_type: 'industry' or 'role'
    raw_label:  the human-readable name (e.g. 'Real Estate', 'Data Scientist')
    config_obj: user config dict (needed for AI provider + keys)

    Returns the generated entry dict (already inserted into _INSTRUCTION_PACKS and saved).
    On failure, returns the fallback entry.
    """
    packs = _load_instruction_packs()
    fallbacks = packs.get('_fallbacks', {})
    fallback_entry = fallbacks.get(entry_type, {})

    key = re.sub(r'[^a-z0-9]+', '_', raw_label.strip().lower()).strip('_')
    section_name = 'industries' if entry_type == 'industry' else 'roles'

    # Double-check: another thread may have generated it while we waited
    if key in packs.get(section_name, {}):
        return packs[section_name][key]

    if entry_type == 'industry':
        schema_prompt = f"""Generate a JSON object for the LinkedIn content industry "{raw_label}".
The object must have EXACTLY these keys (no extras):
{{
  "label": "<human-readable industry name>",
  "vocabulary": ["<10-14 domain-specific terms/acronyms professionals in this industry use daily>"],
  "proof_types": ["<4-5 types of evidence that readers in this industry trust>"],
  "metrics_readers_respect": ["<4-5 KPIs or metrics that earn credibility in this industry>"],
  "angles": ["<4 strong content angles for LinkedIn posts in this industry>"],
  "banned_cliches": ["<3-4 overused buzzwords/phrases to avoid in this industry>"],
  "audience_context": "<1-2 sentences describing who reads LinkedIn posts about this industry and what they value>"
}}
Return ONLY the JSON object, no markdown fences, no explanation."""
    else:
        schema_prompt = f"""Generate a JSON object for the LinkedIn content role "{raw_label}".
The object must have EXACTLY these keys (no extras):
{{
  "label": "<human-readable role name>",
  "perspective": "<1-2 sentences on how this role's unique vantage point shapes their LinkedIn writing>",
  "authority_signals": ["<3-4 ways someone in this role demonstrates credibility in a LinkedIn post>"],
  "audience_relationship": "<1 sentence: who reads this person's posts and what they expect>",
  "writing_style": "<1 sentence defining the ideal writing style for this role on LinkedIn>"
}}
Return ONLY the JSON object, no markdown fences, no explanation."""

    try:
        from ai_provider import AIProvider
        ai = _build_platform_ai_provider()
        result = ai.generate(schema_prompt, max_tokens=600, temperature=0.3)
        raw_text = (result.get('text') or '').strip()

        # Strip any accidental markdown fences
        if raw_text.startswith('```'):
            raw_text = re.sub(r'^```[a-zA-Z]*\n?', '', raw_text)
            raw_text = re.sub(r'\n?```$', '', raw_text)

        entry = json.loads(raw_text)

        # Validate minimum keys
        if entry_type == 'industry' and 'vocabulary' not in entry:
            raise ValueError('Generated industry entry missing vocabulary key')
        if entry_type == 'role' and 'perspective' not in entry:
            raise ValueError('Generated role entry missing perspective key')

        # Insert into memory + persist
        if section_name not in packs:
            packs[section_name] = {}
        packs[section_name][key] = entry
        _save_instruction_packs()

        logger.info('Auto-generated instruction pack %s entry for "%s" (key=%s)', entry_type, raw_label, key)
        return entry

    except Exception as e:
        logger.warning('Failed to auto-generate %s pack for "%s": %s — using fallback', entry_type, raw_label, e)
        return fallback_entry


def _build_instruction_pack_text(industry_raw: str, role_raw: str, goal_key: str, config_obj: dict = None) -> str:
    """Build rich instruction text for a given (industry, role, goal) combination.

    If the industry or role is not found in the packs, it will be auto-generated
    via a one-time AI call and cached permanently (requires config_obj).
    """
    packs = _load_instruction_packs()
    if not packs:
        return ''

    industries = packs.get('industries', {})
    roles = packs.get('roles', {})
    goals = packs.get('goals', {})

    # Resolve keys
    ind_key = _resolve_pack_key(industry_raw, industries)
    role_key = _resolve_pack_key(role_raw, roles)

    # Goal key comes in normalized already (e.g. 'spark_comments')
    goal_data_key = goal_key.replace('-', '_') if goal_key else ''
    if goal_data_key and goal_data_key not in goals:
        _goal_pack_aliases = {
            'spark_comments': 'spark_comments',
            'drive_profile_visits': 'drive_visibility',
            'drive_visits': 'drive_visibility',
            'generate_leads': 'generate_leads',
            'build_authority': 'build_authority',
            'educate_audience': 'educate_audience',
            'brand_awareness': 'brand_awareness',
            'grow_network': 'grow_network',
        }
        goal_data_key = _goal_pack_aliases.get(goal_data_key, goal_data_key)

    # ── Industry: auto-generate if missing ──
    if ind_key:
        ind = industries[ind_key]
    elif config_obj:
        ind = _auto_generate_pack_entry('industry', industry_raw, config_obj)
    else:
        ind = packs.get('_fallbacks', {}).get('industry', {})

    # ── Role: auto-generate if missing ──
    if role_key:
        role = roles[role_key]
    elif config_obj:
        role = _auto_generate_pack_entry('role', role_raw, config_obj)
    else:
        role = packs.get('_fallbacks', {}).get('role', {})

    # Goals are fixed set — just use fallback if missing
    goal = goals.get(goal_data_key, packs.get('_fallbacks', {}).get('goal', {}))

    sections = []

    # ── Industry Section ──
    vocab = ', '.join(ind.get('vocabulary', [])[:12])
    proofs = ', '.join(ind.get('proof_types', [])[:4])
    metrics = ', '.join(ind.get('metrics_readers_respect', [])[:4])
    angles_list = ind.get('angles', [])
    angles = '\n'.join(f'  - {a}' for a in angles_list[:4])
    ind_banned = ', '.join(ind.get('banned_cliches', []))
    aud_ctx = ind.get('audience_context', '')

    sections.append(f"""INDUSTRY PLAYBOOK ({ind.get('label', industry_raw)}):
- Domain vocabulary to use naturally: {vocab or 'general business terms'}
- Proof types readers trust: {proofs or 'real examples with outcomes'}
- Metrics that earn credibility: {metrics or 'revenue impact, time saved'}
- Strong angles for this industry:
{angles or '  - what most people get wrong'}
{f'- Industry-specific clichés to AVOID: {ind_banned}' if ind_banned else ''}
- Reader context: {aud_ctx or 'Professionals who value specifics.'}""")

    # ── Role Section ──
    perspective = role.get('perspective', '')
    auth_signals = role.get('authority_signals', [])
    aud_rel = role.get('audience_relationship', '')
    writing = role.get('writing_style', '')

    auth_str = '\n'.join(f'  - {s}' for s in auth_signals[:4])
    sections.append(f"""ROLE PLAYBOOK ({role.get('label', role_raw)}):
- Perspective: {perspective or 'Write as a knowledgeable professional with hands-on experience.'}
- How to demonstrate authority:
{auth_str or '  - share real decisions and outcomes'}
- Your relationship with readers: {aud_rel or 'Peers who respect substance.'}
- Writing style for this role: {writing or 'Clear, direct, human.'}""")

    # ── Goal Section ──
    struct_mod = goal.get('structural_modifier', '')
    hook = goal.get('hook_style', '')
    cta = goal.get('cta_pattern', '')

    sections.append(f"""GOAL PLAYBOOK ({goal.get('label', 'Engagement')}):
- Structure: {struct_mod or 'Deliver one clear, valuable idea.'}
- Hook approach: {hook or 'Open with the most interesting sentence you can.'}
- CTA pattern: {cta or 'Close with something the reader can act on or reflect on.'}""")

    return '\n\n'.join(sections)


# Removed _resolve_target_audience_hint as target_audience and audience_type logic is deprecated.


def _month_start_date_utc(now: datetime = None) -> date:
    current = now or datetime.utcnow()
    return date(current.year, current.month, 1)


def _parse_iso_utc(value: str):
    text = str(value or '').strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace('Z', '+00:00'))
        if parsed.tzinfo is not None:
            return parsed.astimezone(timezone.utc).replace(tzinfo=None)
        return parsed
    except Exception:
        return None


def _get_subscription_row(user_id: str) -> dict:
    if not auth_supabase or not is_valid_uuid(user_id):
        return {'plan': 'free', 'status': 'active'}
    try:
        rows = auth_supabase.table('subscriptions').select('*').eq('user_id', user_id).order('updated_at', desc=True).limit(1).execute().data or []
        if not rows:
            return {'plan': 'free', 'status': 'active'}
        return _apply_subscription_transition_if_due(rows[0])
    except Exception as e:
        logger.warning("Subscription lookup failed for user %s: %s", user_id, e)
        return {'plan': 'free', 'status': 'active'}


def _is_subscription_active(subscription: dict) -> bool:
    status = str(subscription.get('status') or 'inactive').strip().lower()
    if status not in {'active', 'trialing'}:
        return False
    period_end = _parse_iso_utc(subscription.get('current_period_end'))
    if period_end and period_end < datetime.utcnow():
        return False
    return True


def _get_effective_plan(user_id: str) -> str:
    subscription = _get_subscription_row(user_id)
    normalized = _normalize_subscription_plan(subscription.get('plan'))
    plan = normalized[0] if normalized else 'free'
    if plan == 'free':
        return 'free'
    if _is_subscription_active(subscription):
        return plan
    return 'free'


def _resolve_notification_email(user_id: str, preferred_email: str = '') -> str:
    """Resolve user's email for notifications with fallback to Supabase Auth profile."""
    email = str(preferred_email or '').strip()
    if email:
        return email

    # Primary: user_features.user_config.email
    blob = _read_feature_blob_for_user(user_id)
    cfg = blob.get('user_config') if isinstance(blob.get('user_config'), dict) else {}
    email = str((cfg or {}).get('email') or '').strip()
    if email:
        return email

    # Fallback: Supabase Auth user email via admin API
    try:
        if auth_supabase and is_valid_uuid(user_id):
            resp = auth_supabase.auth.admin.get_user_by_id(user_id)
            candidate = ''

            if isinstance(resp, dict):
                user_obj = resp.get('user') or resp.get('data') or {}
                if isinstance(user_obj, dict):
                    candidate = str(user_obj.get('email') or '').strip()
                else:
                    candidate = str(getattr(user_obj, 'email', '') or '').strip()
            else:
                user_obj = getattr(resp, 'user', None) or getattr(resp, 'data', None)
                if isinstance(user_obj, dict):
                    candidate = str(user_obj.get('email') or '').strip()
                else:
                    candidate = str(getattr(user_obj, 'email', '') or '').strip()

            if candidate:
                # Cache recovered email in user_features for future reads.
                cfg['email'] = candidate
                blob['user_config'] = cfg
                _write_feature_blob_for_user(user_id, blob)
                return candidate
    except Exception:
        pass

    return ''


def _maybe_send_subscription_expiry_reminder(user_id: str, subscription: dict, plan: str, user_email: str = '') -> None:
    """Best-effort reminder email for manual-renewal plans (7d, 3d, 1d, 0d)."""
    try:
        if not subscription or plan == 'free':
            return
        if not _is_subscription_active(subscription):
            return

        period_end = _parse_iso_utc(subscription.get('current_period_end'))
        if not period_end:
            return

        now = datetime.utcnow()
        seconds_left = (period_end - now).total_seconds()
        if seconds_left < 0:
            days_remaining = 0
        else:
            days_remaining = int(seconds_left // 86400)

        if days_remaining not in {7, 3, 1, 0}:
            return

        email = _resolve_notification_email(user_id, str(user_email or '').strip())
        if not email:
            return

        blob = _read_feature_blob_for_user(user_id)
        reminders = blob.get('billing_reminders') if isinstance(blob.get('billing_reminders'), dict) else {}
        today_key = now.date().isoformat()
        last_sent_date = str(reminders.get('expiry_last_sent_date') or '').strip()
        last_sent_bucket = reminders.get('expiry_last_sent_days')

        # Prevent duplicate sends from repeated dashboard polls on same day and same bucket.
        if last_sent_date == today_key and int(last_sent_bucket or -1) == int(days_remaining):
            return

        _send_subscription_expiry_reminder(
            email,
            plan=plan,
            days_remaining=days_remaining,
            renewal_url=(os.getenv('APP_BASE_URL') or 'https://app.velank.io').rstrip('/') + '/#settings?tab=billing',
        )

        reminders['expiry_last_sent_date'] = today_key
        reminders['expiry_last_sent_days'] = int(days_remaining)
        blob['billing_reminders'] = reminders
        _write_feature_blob_for_user(user_id, blob)
    except Exception:
        # Reminders are best-effort and should never break billing APIs.
        pass


def _get_monthly_usage_row(user_id: str, month_start: date = None) -> dict:
    month_key = (month_start or _month_start_date_utc()).isoformat()
    if not auth_supabase or not is_valid_uuid(user_id):
        return {
            'user_id': user_id,
            'month': month_key,
            'posts_generated': 0,
            'posts_published': 0,
            'kb_files_uploaded': 0,
            'kb_storage_bytes': 0,
            'api_calls': 0
        }
    try:
        rows = auth_supabase.table('usage_monthly').select('*').eq('user_id', user_id).eq('month', month_key).limit(1).execute().data or []
        if rows:
            return rows[0]
    except Exception as e:
        logger.warning("Usage lookup failed for user %s: %s", user_id, e)
    return {
        'user_id': user_id,
        'month': month_key,
        'posts_generated': 0,
        'posts_published': 0,
        'kb_files_uploaded': 0,
        'kb_storage_bytes': 0,
        'api_calls': 0
    }


def _increment_monthly_usage(user_id: str, **increments) -> None:
    if not auth_supabase or not is_valid_uuid(user_id):
        return
    month_start = _month_start_date_utc()
    current = _get_monthly_usage_row(user_id, month_start)

    allowed_fields = {'posts_generated', 'posts_published', 'kb_files_uploaded', 'kb_storage_bytes', 'api_calls',
                      'ai_prompt_tokens', 'ai_completion_tokens', 'ai_total_tokens', 'ai_cost_usd_micros'}
    update_payload = {}
    for field, increment in increments.items():
        if field not in allowed_fields:
            continue
        try:
            add_value = int(increment)
        except Exception:
            continue
        if add_value <= 0:
            continue
        base_value = int(current.get(field) or 0)
        update_payload[field] = base_value + add_value

    if not update_payload:
        return

    try:
        rows = auth_supabase.table('usage_monthly').select('id').eq('user_id', user_id).eq('month', month_start.isoformat()).limit(1).execute().data or []
        if rows:
            auth_supabase.table('usage_monthly').update(update_payload).eq('id', rows[0]['id']).execute()
        else:
            auth_supabase.table('usage_monthly').insert({
                'user_id': user_id,
                'month': month_start.isoformat(),
                **update_payload
            }).execute()
        # ── Quota-warning email (80 % and 90 %) ──────────────────────────────
        if 'posts_generated' in update_payload:
            try:
                plan = _get_effective_plan(user_id)
                limits = _get_plan_limits(plan)
                limit = _plan_limit_int(limits, 'posts_generated', 0)
                if limit > 0:
                    new_used = update_payload['posts_generated']
                    pct = int(new_used * 100 / limit)
                    remaining = max(0, limit - new_used)
                    if pct >= 90 or pct >= 80:
                        blob = _read_feature_blob_for_user(user_id)
                        user_email = str((blob.get('user_config') or {}).get('email') or '').strip()
                        if user_email:
                            _send_quota_warning(user_email, plan=plan, percent_used=pct, posts_remaining=remaining)
            except Exception:
                pass  # quota warning is best-effort
    except Exception as e:
        logger.warning("Usage increment failed for user %s: %s", user_id, e)


def _get_user_scheduled_count(user_id: str) -> int:
    db_posts = _db_list_scheduled_posts(user_id)
    if db_posts:
        return len(db_posts)
    scheduled_posts = _read_json_list(SCHEDULED_POSTS_PATH)
    return sum(1 for row in scheduled_posts if str(row.get('user_id') or '').strip() == str(user_id))


def _check_generation_guardrail(user_id: str):
    plan = _get_effective_plan(user_id)
    limits = _get_plan_limits(plan)
    usage = _get_monthly_usage_row(user_id)
    used = int(usage.get('posts_generated') or 0)
    limit = _plan_limit_int(limits, 'posts_generated', 0)
    if limit <= 0:
        return False, {
            'plan': plan,
            'metric': 'posts_generated',
            'used': used,
            'limit': limit,
            'message': 'Post generation is not available on your current plan. Please upgrade to continue.'
        }
    if used >= limit:
        return False, {
            'plan': plan,
            'metric': 'posts_generated',
            'used': used,
            'limit': limit,
            'message': f'Monthly post generation limit reached ({used}/{limit}) for your {plan.replace("_", " ")} plan.'
        }
    return True, {
        'plan': plan,
        'metric': 'posts_generated',
        'used': used,
        'limit': limit
    }


def _activate_subscription_from_payment(user_id: str, plan: str, payment_id: str = '', order_id: str = '', amount_minor: int = None, currency: str = 'INR'):
    normalized = _normalize_subscription_plan(plan)
    if not normalized or normalized[0] == 'free':
        return None
    if not auth_supabase or not is_valid_uuid(user_id):
        return None

    normalized_plan, months = normalized
    now = datetime.utcnow()
    normalized_currency = str(currency or 'INR').strip().upper() or 'INR'
    billed_amount_minor = max(0, int(amount_minor if amount_minor is not None else _plan_price_minor(normalized_plan, normalized_currency)))
    
    # Check if this is an upgrade (user already has an active subscription)
    is_upgrade = False
    existing_period_end = None
    try:
        rows = auth_supabase.table('subscriptions').select('*').eq('user_id', user_id).limit(1).execute()
        existing_sub = rows.data[0] if rows.data else None
        if existing_sub and _is_subscription_active(existing_sub):
            is_upgrade = True
            existing_period_end = existing_sub.get('current_period_end')
    except Exception:
        pass
    
    # For upgrades, keep the existing period_end. For new subscriptions, set new period_end
    if is_upgrade and existing_period_end:
        period_end = existing_period_end  # Keep existing end date
    else:
        period_end = _add_months_utc(now, months)
    
    payload = {
        'user_id': user_id,
        'plan': normalized_plan,
        'status': 'active',
        'current_period_start': now.isoformat() + 'Z',
        'current_period_end': period_end if isinstance(period_end, str) else (period_end.isoformat() + 'Z'),
        'cancel_at_period_end': False,
        'scheduled_plan': None,
        'current_plan_currency': normalized_currency,
        'current_plan_price_minor': billed_amount_minor if not is_upgrade else _plan_price_minor(normalized_plan, normalized_currency),
        'updated_at': now.isoformat() + 'Z',
        'billing_provider': 'razorpay'
    }
    if payment_id:
        payload['provider_payment_id'] = payment_id
    if order_id:
        payload['provider_order_id'] = order_id

    try:
        auth_supabase.table('subscriptions').upsert(payload, on_conflict='user_id').execute()
    except Exception:
        fallback_payload = {
            'user_id': user_id,
            'plan': normalized_plan,
            'status': 'active',
            'current_period_start': now.isoformat() + 'Z',
            'current_period_end': period_end if isinstance(period_end, str) else (period_end.isoformat() + 'Z'),
            'cancel_at_period_end': False,
            'updated_at': now.isoformat() + 'Z'
        }
        if payment_id:
            fallback_payload['stripe_subscription_id'] = payment_id
        if order_id:
            fallback_payload['stripe_customer_id'] = order_id
        auth_supabase.table('subscriptions').upsert(fallback_payload, on_conflict='user_id').execute()
    return {
        'plan': normalized_plan,
        'current_period_start': payload['current_period_start'],
        'current_period_end': payload['current_period_end'],
        'is_upgrade': is_upgrade,
        'current_plan_price_minor': payload.get('current_plan_price_minor', 0),
        'current_plan_currency': payload.get('current_plan_currency', normalized_currency),
    }


def _calculate_proration(user_id: str, new_plan: str, region: str = 'ROW') -> dict:
    """
    Calculate prorated charge for plan upgrade.
    
    Returns: {
        'prorated_amount': float,          # Amount user owes (or 0 if downgrade/same plan)
        'current_plan': str,              # Current plan name
        'new_plan': str,                  # New plan name
        'days_remaining': int,            # Days left in current billing period
        'current_plan_daily_rate': float, # Cost per day of current plan
        'new_plan_daily_rate': float      # Cost per day of new plan
    }
    """
    if not auth_supabase or not is_valid_uuid(user_id):
        return {'prorated_amount': 0, 'error': 'Invalid user'}
    
    # Get current subscription
    try:
        rows = auth_supabase.table('subscriptions').select('*').eq('user_id', user_id).limit(1).execute()
        current_sub = rows.data[0] if rows.data else None
    except Exception:
        return {'prorated_amount': 0, 'error': 'Could not fetch subscription'}
    
    if not current_sub:
        return {'prorated_amount': 0, 'error': 'No active subscription'}
    
    current_plan = str(current_sub.get('plan') or 'free').lower().strip()
    new_plan = str(new_plan or '').lower().strip()
    
    # Only allow upgrades, not downgrades
    plan_order = {'free': 0, 'starter': 1, 'creator': 2, 'pro': 3}
    current_level = plan_order.get(current_plan, 0)
    new_level = plan_order.get(new_plan, 0)
    
    if new_level <= current_level:
        return {'prorated_amount': 0, 'reason': 'Downgrade not allowed, same plan, or invalid plan'}
    
    # Check if subscription is actually active
    if not _is_subscription_active(current_sub):
        return {'prorated_amount': 0, 'error': 'Current subscription not active'}
    
    # Calculate remaining share of current period
    period_end = _parse_iso_utc(current_sub.get('current_period_end'))
    period_start = _parse_iso_utc(current_sub.get('current_period_start'))
    now = datetime.utcnow()
    
    if not period_end:
        return {'prorated_amount': 0, 'error': 'Could not determine period end'}
    remaining_seconds = max(0.0, (period_end - now).total_seconds())
    if period_start and period_end > period_start:
        cycle_seconds = max(1.0, (period_end - period_start).total_seconds())
    else:
        cycle_seconds = float(30 * 24 * 60 * 60)

    remaining_ratio = min(1.0, remaining_seconds / cycle_seconds)
    days_remaining = max(1, int((remaining_seconds + 86399) // 86400)) if remaining_seconds > 0 else 0

    currency = str(current_sub.get('current_plan_currency') or ('INR' if region.upper() == 'IN' else 'USD')).strip().upper() or 'INR'
    current_price_minor = int(current_sub.get('current_plan_price_minor') or 0)
    if current_price_minor <= 0:
        current_price_minor = _plan_price_minor(current_plan, currency)
    new_price_minor = _plan_price_minor(new_plan, currency)

    if current_price_minor <= 0:
        prorated_minor = new_price_minor
    else:
        credit_minor = int(round(current_price_minor * remaining_ratio))
        new_charge_minor = int(round(new_price_minor * remaining_ratio))
        prorated_minor = max(0, new_charge_minor - credit_minor)
    
    return {
        'success': True,
        'prorated_amount': _minor_to_display_amount(prorated_minor),
        'prorated_amount_minor': prorated_minor,
        'current_plan': current_plan,
        'new_plan': new_plan,
        'days_remaining': days_remaining,
        'currency': currency,
        'price_current_plan': _minor_to_display_amount(current_price_minor),
        'price_new_plan': _minor_to_display_amount(new_price_minor),
        'price_current_plan_minor': current_price_minor,
        'price_new_plan_minor': new_price_minor,
    }


def _razorpay_keys():
    key_id = str(os.getenv('RAZORPAY_KEY_ID') or '').strip()
    key_secret = str(os.getenv('RAZORPAY_KEY_SECRET') or '').strip()
    return key_id, key_secret


def _razorpay_webhook_secret() -> str:
    return str(os.getenv('RAZORPAY_WEBHOOK_SECRET') or '').strip()


def _create_razorpay_order(amount_major: int = None, currency: str = 'INR', receipt: str = '', user_id: str = '', plan: str = '', amount_minor: int = None, extra_notes: dict = None) -> dict:
    key_id, key_secret = _razorpay_keys()
    if not key_id or not key_secret:
        raise RuntimeError('Razorpay keys are not configured')

    normalized_currency = str(currency or 'INR').upper()
    resolved_amount_minor = int(amount_minor) if amount_minor is not None else int(max(0, int(amount_major or 0)) * 100)
    notes = {
        'user_id': user_id,
        'plan': plan
    }
    if isinstance(extra_notes, dict):
        notes.update({k: str(v) for k, v in extra_notes.items() if v is not None})

    payload = {
        'amount': resolved_amount_minor,
        'currency': normalized_currency,
        'receipt': receipt,
        'notes': notes
    }
    response = requests.post(
        'https://api.razorpay.com/v1/orders',
        json=payload,
        auth=(key_id, key_secret),
        timeout=20
    )
    if response.status_code >= 400:
        raise RuntimeError(f'Razorpay order create failed: {response.status_code} {response.text[:300]}')
    return response.json()


def _verify_razorpay_payment_signature(order_id: str, payment_id: str, signature: str) -> bool:
    _, key_secret = _razorpay_keys()
    if not key_secret:
        return False
    payload = f"{order_id}|{payment_id}".encode('utf-8')
    expected = hmac.new(key_secret.encode('utf-8'), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, str(signature or '').strip())


def _verify_razorpay_webhook_signature(raw_body: bytes, signature: str) -> bool:
    secret = _razorpay_webhook_secret()
    if not secret:
        return False
    expected = hmac.new(secret.encode('utf-8'), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, str(signature or '').strip())

# ============= AUTHENTICATION ROUTES =============

@app.route('/api/auth/signup', methods=['POST'])
@limiter.limit("5 per minute")
def auth_signup():
    """User registration"""
    try:
        data = request.get_json() or {}
        email = (data.get('email') or '').strip()
        password = data.get('password', '')
        confirm_password = data.get('confirm_password', '')
        first_name = (data.get('first_name') or '').strip()
        last_name = (data.get('last_name') or '').strip()
        country = (data.get('country') or '').strip()
        
        if not email or not password or not first_name or not last_name or not country:
            return jsonify({'success': False, 'message': 'First name, last name, country, email and password are required'}), 400

        if confirm_password and confirm_password != password:
            return jsonify({'success': False, 'message': 'Password and confirm password do not match'}), 400

        if len(password) < 8:
            return jsonify({'success': False, 'message': 'Password must be at least 8 characters'}), 400

        if '@' not in email:
            return jsonify({'success': False, 'message': 'Invalid email format'}), 400

        role = (data.get('role') or '').strip()
        industry = (data.get('industry') or '').strip()
        referred_by = (data.get('referred_by') or '').strip() or None  # referrer's user_id

        metadata = {
            'email': email,
            'first_name': first_name,
            'last_name': last_name,
            'country': country,
            'role': role,
            'industry': industry
        }

        success, message, user_data = signup_user(email, password, metadata)
        if success and email:
            _send_welcome_email(email, display_name=first_name)

        # Write referred_by to user_profiles and increment referrer's count
        if success and referred_by and user_data and auth_supabase:
            try:
                new_user_id = user_data.get('id')
                if new_user_id and is_valid_uuid(str(new_user_id)) and is_valid_uuid(str(referred_by)):
                    auth_supabase.table('user_profiles').upsert({
                        'user_id': str(new_user_id),
                        'referred_by': str(referred_by),
                    }, on_conflict='user_id').execute()
                    # Increment referrer's referral_count
                    ref_profile = auth_supabase.table('user_profiles').select('id,referral_count').eq('user_id', str(referred_by)).execute()
                    if ref_profile.data:
                        current_count = int((ref_profile.data[0] or {}).get('referral_count') or 0)
                        auth_supabase.table('user_profiles').update({'referral_count': current_count + 1}).eq('user_id', str(referred_by)).execute()
            except Exception as _ref_err:
                logger.warning("Could not write referral info: %s", _ref_err)
        status_code = 200 if success else 400
        lowered = (message or '').lower()
        if not success and ('temporarily unavailable' in lowered or 'timeout' in lowered):
            status_code = 503

        return jsonify({
            'success': success,
            'message': message,
            'user': user_data
        }), status_code
        
    except Exception as e:
        logger.exception("Signup failed")
        return _safe_api_error('Signup failed', e)


@app.route('/api/auth/login', methods=['POST'])
@limiter.limit("10 per minute")
def auth_login():
    """User login"""
    try:
        data = request.get_json() or {}
        email = (data.get('email') or '').strip()
        password = data.get('password', '')
        
        if not email or not password:
            return jsonify({'success': False, 'message': 'Email and password required'}), 400
        
        success, message, auth_data = login_user(email, password)

        if success:
            # Extra verification (best-effort): do not block successful login
            # if Supabase is experiencing transient timeout issues.
            token = auth_data.get('access_token')
            verified = None
            try:
                if token:
                    verified = verify_token(token)
            except Exception as verify_exc:
                logger.warning("Post-login token verification failed (non-blocking): %s", verify_exc)
                verified = None

            if token and not verified:
                logger.warning("Post-login token verification returned no user (non-blocking); proceeding with login response")

            return jsonify({
                'success': True,
                'message': message,
                'access_token': auth_data.get('access_token'),
                'refresh_token': auth_data.get('refresh_token'),
                'user': auth_data.get('user')
            }), 200
        else:
            lowered = (message or '').lower()
            status_code = 401
            
            # Check for OAuth-only account (no password set)
            if message and message.startswith('no_password|'):
                error_msg = message.replace('no_password|', '')
                status_code = 400
                return jsonify({
                    'success': False,
                    'message': error_msg,
                    'error_type': 'oauth_only_account',
                    'action': 'Use OAuth login or reset password',
                    'can_reset_password': True
                }), status_code
            
            if 'temporarily unavailable' in lowered or 'timeout' in lowered:
                status_code = 503
            return jsonify({'success': False, 'message': message}), status_code
            
    except Exception as e:
        logger.exception("Login failed")
        return _safe_api_error('Login failed', e)


@app.route('/api/auth/google/start', methods=['GET', 'POST'])
def auth_google_start():
    """Start Google OAuth sign-in via Supabase hosted auth."""
    try:
        supabase_url = (os.getenv('SUPABASE_URL') or '').strip().rstrip('/')
        supabase_key = (os.getenv('SUPABASE_ANON_KEY') or os.getenv('SUPABASE_KEY') or '').strip()
        if not supabase_url or not supabase_key:
            return jsonify({'success': False, 'message': 'Supabase is not configured on server'}), 500

        payload = request.get_json(silent=True) or {}
        requested_redirect = (payload.get('redirect_to') or request.args.get('redirect_to') or '').strip()
        if requested_redirect:
            redirect_to = requested_redirect
        else:
            base_url = (os.getenv('APP_BASE_URL') or 'http://127.0.0.1:5050').strip().rstrip('/')
            redirect_to = f"{base_url}/auth/callback"

        # Build OAuth URL for Supabase (Supabase handles Google OAuth internally)
        # Supabase validates redirect_to against registered URIs in the console
        query = urlencode({
            'provider': 'google',
            'redirect_to': redirect_to,
            'response_type': 'code',
            'scope': 'openid email profile'
        })
        auth_url = f"{supabase_url}/auth/v1/authorize?{query}"
        return jsonify({'success': True, 'auth_url': auth_url})
    except Exception as e:
        logger.exception("Failed to start Google OAuth")
        return _safe_api_error('Failed to start Google sign-in', e)


def _linkedin_oauth_scopes() -> str:
    # w_member_social is required for posting; openid/profile/email enables stable user identity fetch.
    return 'openid profile email w_member_social r_liteprofile'


def _linkedin_state_sign(raw_payload: dict) -> str:
    payload = dict(raw_payload or {})
    payload['ts'] = int(time.time())
    blob = json.dumps(payload, separators=(',', ':'), sort_keys=True).encode('utf-8')
    blob_b64 = base64.urlsafe_b64encode(blob).decode('ascii').rstrip('=')
    signature = hmac.new(app.secret_key.encode('utf-8'), blob_b64.encode('utf-8'), hashlib.sha256).hexdigest()
    return f"{blob_b64}.{signature}"


def _linkedin_state_verify(token: str, max_age_seconds: int = 900) -> dict:
    raw = str(token or '').strip()
    if '.' not in raw:
        raise ValueError('Missing state signature')
    blob_b64, signature = raw.rsplit('.', 1)
    expected = hmac.new(app.secret_key.encode('utf-8'), blob_b64.encode('utf-8'), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise ValueError('Invalid state signature')

    padded = blob_b64 + '=' * ((4 - len(blob_b64) % 4) % 4)
    decoded = base64.urlsafe_b64decode(padded.encode('ascii')).decode('utf-8')
    payload = json.loads(decoded)

    ts = int(payload.get('ts') or 0)
    if ts <= 0 or (int(time.time()) - ts) > max_age_seconds:
        raise ValueError('State expired')
    return payload


def _linkedin_exchange_code_for_token(code: str, redirect_uri: str, client_id: str, client_secret: str) -> dict:
    response = requests.post(
        'https://www.linkedin.com/oauth/v2/accessToken',
        data={
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': redirect_uri,
            'client_id': client_id,
            'client_secret': client_secret,
        },
        timeout=25,
    )
    if response.status_code >= 400:
        body_preview = (response.text or '')[:250]
        raise RuntimeError(f'LinkedIn token exchange failed ({response.status_code}): {body_preview}')
    data = response.json() if response.content else {}
    access_token = str(data.get('access_token') or '').strip()
    if not access_token:
        raise RuntimeError('LinkedIn token exchange succeeded but access_token is missing')
    return data


def _linkedin_fetch_person_id(access_token: str) -> str:
    headers = {'Authorization': f'Bearer {access_token}'}

    # OpenID userinfo provides a stable subject id for the member.
    try:
        r = requests.get('https://api.linkedin.com/v2/userinfo', headers=headers, timeout=20)
        if r.status_code < 400:
            data = r.json() if r.content else {}
            subject_id = str(data.get('sub') or '').strip()
            if subject_id:
                return subject_id
    except Exception:
        pass

    # Fallback to classic v2/me endpoint.
    try:
        r = requests.get('https://api.linkedin.com/v2/me', headers=headers, timeout=20)
        if r.status_code < 400:
            data = r.json() if r.content else {}
            member_id = str(data.get('id') or '').strip()
            if member_id:
                return member_id
    except Exception:
        pass

    raise RuntimeError('Connected to LinkedIn but could not resolve member id')


def _linkedin_callback_redirect(success: bool, action: str = '', error_msg: str = '') -> str:
    normalized_action = str(action or '').strip().lower()
    if normalized_action not in {'publish', 'schedule'}:
        normalized_action = ''

    params = {'li_connected': '1' if success else '0'}
    if normalized_action:
        params['li_action'] = normalized_action
    if error_msg and not success:
        params['li_error'] = str(error_msg)[:220]

    return f"/?{urlencode(params)}"


@app.route('/api/linkedin/oauth/start', methods=['POST'])
@require_auth
def linkedin_oauth_start():
    """Start LinkedIn OAuth connect flow for publish/schedule actions."""
    try:
        user_id = get_current_user_id()
        if not is_valid_uuid(user_id):
            return jsonify({'success': False, 'message': 'Unauthorized'}), 401

        payload = request.get_json(silent=True) or {}
        pending_action = str(payload.get('action') or '').strip().lower()
        if pending_action not in {'publish', 'schedule', 'settings'}:
            pending_action = 'publish'

        user_cfg = load_config(user_id)
        client_id = str(user_cfg.get('LINKEDIN_CLIENT_ID') or os.getenv('LINKEDIN_CLIENT_ID') or '').strip()
        client_secret = str(user_cfg.get('LINKEDIN_CLIENT_SECRET') or os.getenv('LINKEDIN_CLIENT_SECRET') or '').strip()
        if not client_id or not client_secret:
            return jsonify({
                'success': False,
                'message': 'LinkedIn OAuth is not configured on server (missing LINKEDIN_CLIENT_ID / LINKEDIN_CLIENT_SECRET).'
            }), 400

        base_url = (os.getenv('APP_BASE_URL') or request.host_url or '').strip().rstrip('/')
        if not base_url:
            base_url = request.host_url.rstrip('/')
        redirect_uri = f"{base_url}/api/linkedin/oauth/callback"

        state = _linkedin_state_sign({'uid': user_id, 'action': pending_action})
        auth_url = 'https://www.linkedin.com/oauth/v2/authorization?' + urlencode({
            'response_type': 'code',
            'client_id': client_id,
            'redirect_uri': redirect_uri,
            'state': state,
            'scope': _linkedin_oauth_scopes(),
        })
        return jsonify({'success': True, 'auth_url': auth_url})
    except Exception as exc:
        logger.exception('Failed to start LinkedIn OAuth')
        return _safe_api_error('Could not start LinkedIn connect flow', exc)


@app.route('/api/linkedin/oauth/callback', methods=['GET'])
def linkedin_oauth_callback():
    """Handle LinkedIn OAuth callback and persist token/member id for posting."""
    code = str(request.args.get('code') or '').strip()
    state = str(request.args.get('state') or '').strip()
    oauth_error = str(request.args.get('error') or '').strip()
    oauth_error_desc = str(request.args.get('error_description') or '').strip()

    action = ''
    if state:
        try:
            verified_state = _linkedin_state_verify(state)
            action = str(verified_state.get('action') or '').strip().lower()
        except Exception:
            pass

    if oauth_error:
        msg = oauth_error_desc or oauth_error
        return redirect(_linkedin_callback_redirect(False, action=action, error_msg=msg))

    if not code or not state:
        return redirect(_linkedin_callback_redirect(False, action=action, error_msg='Missing OAuth code/state'))

    try:
        verified_state = _linkedin_state_verify(state)
        user_id = str(verified_state.get('uid') or '').strip()
        action = str(verified_state.get('action') or '').strip().lower()
        if not is_valid_uuid(user_id):
            return redirect(_linkedin_callback_redirect(False, action=action, error_msg='Invalid OAuth state user'))

        user_cfg = load_config(user_id)
        client_id = str(user_cfg.get('LINKEDIN_CLIENT_ID') or os.getenv('LINKEDIN_CLIENT_ID') or '').strip()
        client_secret = str(user_cfg.get('LINKEDIN_CLIENT_SECRET') or os.getenv('LINKEDIN_CLIENT_SECRET') or '').strip()
        if not client_id or not client_secret:
            return redirect(_linkedin_callback_redirect(False, action=action, error_msg='LinkedIn OAuth server keys missing'))

        base_url = (os.getenv('APP_BASE_URL') or request.host_url or '').strip().rstrip('/')
        if not base_url:
            base_url = request.host_url.rstrip('/')
        redirect_uri = f"{base_url}/api/linkedin/oauth/callback"

        token_data = _linkedin_exchange_code_for_token(code, redirect_uri, client_id, client_secret)
        access_token = str(token_data.get('access_token') or '').strip()
        member_id = _linkedin_fetch_person_id(access_token)

        updated_cfg = load_config(user_id)
        updated_cfg['LINKEDIN_ACCESS_TOKEN'] = access_token
        updated_cfg['LINKEDIN_PERSON_ID'] = member_id
        save_config(updated_cfg, user_id=user_id)

        logger.info('LinkedIn connected for user=%s (action=%s)', user_id, action or '-')
        return redirect(_linkedin_callback_redirect(True, action=action))
    except Exception as exc:
        logger.exception('LinkedIn OAuth callback failed')
        return redirect(_linkedin_callback_redirect(False, action=action, error_msg=str(exc)))


@app.route('/api/auth/logout', methods=['POST'])
@require_auth
def auth_logout():
    """User logout"""
    try:
        success, message = logout_user(None)
        return jsonify({'success': success, 'message': message}), 200 if success else 500
    except Exception as e:
        logger.exception("Logout failed")
        return _safe_api_error('Logout failed', e)


@app.route('/api/auth/me', methods=['GET'])
@require_auth
def auth_me():
    """Get current user info"""
    try:
        return jsonify({
            'success': True,
            'user': {
                'id': g.user_id,
                'email': g.user_email,
                'first_name': getattr(g, 'user', {}).get('first_name', ''),
                'last_name': getattr(g, 'user', {}).get('last_name', ''),
                'country': getattr(g, 'user', {}).get('country', '')
            }
        }), 200
    except Exception as e:
        logger.exception("Failed to get user info")
        return _safe_api_error('An unexpected error occurred', e)


@app.route('/api/auth/verify-token', methods=['POST'])
def auth_verify():
    """Verify if token is valid"""
    try:
        data = request.get_json() or {}
        token = data.get('token', '')
        
        if not token:
            return jsonify({'success': False, 'message': 'Token required'}), 400
        
        user = verify_token(token)
        
        if user:
            return jsonify({
                'success': True,
                'user': user
            }), 200
        else:
            return jsonify({'success': False, 'message': 'Invalid or expired token'}), 401
            
    except Exception as e:
        logger.exception("Token verification failed")
        return _safe_api_error('An unexpected error occurred', e)


@app.route('/api/auth/refresh', methods=['POST'])
def auth_refresh():
    """Refresh access token using refresh token"""
    try:
        data = request.get_json() or {}
        refresh_token = (data.get('refresh_token') or '').strip()

        if not refresh_token:
            return jsonify({'success': False, 'message': 'Refresh token required'}), 400

        success, message, auth_data = refresh_access_token(refresh_token)
        if not success:
            return jsonify({'success': False, 'message': message}), 401

        return jsonify({
            'success': True,
            'message': message,
            'access_token': auth_data.get('access_token'),
            'refresh_token': auth_data.get('refresh_token') or refresh_token,
            'expires_in': auth_data.get('expires_in')
        }), 200
    except Exception as e:
        logger.exception("Token refresh failed")
        return _safe_api_error('Token refresh failed', e)


@app.route('/api/auth/health', methods=['GET'])
def auth_health():
    """Auth configuration and readiness health check."""
    if (os.getenv('TEST_MODE') or '').strip().lower() == 'true':
        return jsonify({
            'success': True,
            'configured': True,
            'missing': [],
            'message': 'Auth test mode is enabled'
        }), 200

    supabase_url = (os.getenv('SUPABASE_URL') or '').strip()
    anon_key = (os.getenv('SUPABASE_ANON_KEY') or '').strip()
    generic_key = (os.getenv('SUPABASE_KEY') or '').strip()
    service_key = (os.getenv('SUPABASE_SERVICE_ROLE_KEY') or '').strip()

    missing = []
    if not supabase_url:
        missing.append('SUPABASE_URL')
    if not (anon_key or generic_key or service_key):
        missing.append('SUPABASE_ANON_KEY|SUPABASE_KEY|SUPABASE_SERVICE_ROLE_KEY')

    configured = len(missing) == 0
    if not configured:
        return jsonify({
            'success': False,
            'configured': False,
            'upstream_ok': False,
            'missing': missing,
            'message': 'Auth is not configured'
        }), 503

    upstream_ok, upstream_message = auth_healthcheck()
    status = 200 if upstream_ok else 503

    return jsonify({
        'success': upstream_ok,
        'configured': True,
        'upstream_ok': upstream_ok,
        'missing': missing,
        'message': upstream_message
    }), status


# ============================================================================
# ACCOUNT LINKING ROUTES
# Manage multiple authentication methods (email/password + OAuth) on same account
# ============================================================================

@app.route('/api/auth/linked-providers', methods=['GET'])
@require_auth
def get_linked_providers():
    """Get all authentication methods linked to the current user's account"""
    try:
        from auth import get_user_linked_providers
        
        user_id = get_current_user_id()
        success, providers = get_user_linked_providers(user_id)
        
        if success:
            return jsonify({
                'success': True,
                'providers': providers,
                'message': f'Found {len(providers)} linked authentication method(s)'
            }), 200
        else:
            return jsonify({
                'success': False,
                'providers': [],
                'message': 'Could not retrieve linked providers'
            }), 200  # Return 200 even if no providers found
    except Exception as e:
        logger.exception("Failed to get linked providers")
        return _safe_api_error('Failed to get linked providers', e)


@app.route('/api/auth/link-oauth', methods=['POST'])
@require_auth
def link_oauth_identity():
    """Link an OAuth identity to the current user's account"""
    try:
        from auth import link_oauth_to_account
        
        data = request.get_json() or {}
        provider = (data.get('provider') or '').strip().lower()
        provider_user_id = (data.get('provider_user_id') or '').strip()
        email = (data.get('email') or '').strip()
        
        if not provider or not provider_user_id:
            return jsonify({
                'success': False,
                'message': 'Provider and provider_user_id required'
            }), 400
        
        user_id = get_current_user_id()
        success, message = link_oauth_to_account(user_id, provider, provider_user_id, email)
        
        status_code = 200 if success else 400
        return jsonify({
            'success': success,
            'message': message,
            'provider': provider
        }), status_code
    except Exception as e:
        logger.exception("Failed to link OAuth identity")
        return _safe_api_error('Failed to link OAuth identity', e)


@app.route('/api/auth/account-linking-status', methods=['GET'])
@require_auth
def check_account_linking_status():
    """
    Check if account linking is available and get current status
    Returns what auth methods the user can link
    """
    try:
        from auth import get_user_linked_providers
        
        user_id = get_current_user_id()
        success, providers = get_user_linked_providers(user_id)
        
        # Determine what methods can be linked
        current_providers = [p.get('provider', '').lower() for p in providers] if providers else []
        
        available_methods = {
            'email': 'email' not in current_providers,
            'google': 'google' not in current_providers,
            'github': 'github' not in current_providers,
            'discord': 'discord' not in current_providers
        }
        
        return jsonify({
            'success': True,
            'current_providers': current_providers,
            'available_methods': available_methods,
            'can_link': any(available_methods.values()),
            'message': 'Account linking available'
        }), 200
    except Exception as e:
        logger.exception("Failed to check account linking status")
        return _safe_api_error('Failed to check account linking status', e)


@app.route('/api/auth/user/profile', methods=['GET'])
@require_auth
def get_auth_user_profile():
    """Get authenticated user's profile with auth method information"""
    try:
        user = verify_token(request.headers.get('Authorization', '').replace('Bearer ', ''))
        
        if not user:
            return jsonify({'success': False, 'message': 'Invalid token'}), 401
        
        from auth import get_user_linked_providers
        
        success, providers = get_user_linked_providers(user.get('id'))
        
        return jsonify({
            'success': True,
            'user': user,
            'linked_providers': providers if success else [],
            'auth_method': user.get('auth_provider', 'unknown')
        }), 200
    except Exception as e:
        logger.exception("Failed to get user auth profile")
        return _safe_api_error('Failed to get user auth profile', e)


@app.route('/api/user/profile', methods=['GET'])
@require_auth
def get_user_profile():
    """Return user_profiles row for the current user (includes referral_count, referral_code)."""
    try:
        user_id = get_current_user_id()
        if not auth_supabase or not is_valid_uuid(str(user_id)):
            return jsonify({'success': False, 'message': 'Not available'}), 503
        res = auth_supabase.table('user_profiles').select(
            'referral_code,referral_count,referred_by,industry,role,timezone'
        ).eq('user_id', str(user_id)).execute()
        profile = (res.data or [{}])[0] if res.data else {}
        return jsonify({'success': True, 'profile': profile})
    except Exception as e:
        return _safe_api_error('Failed to get profile', e)


@app.route('/api/auth/account/update', methods=['POST'])
@require_auth
def auth_account_update():
    """Update signed-in user account details (email + profile metadata)."""
    try:
        if not auth_supabase:
            return jsonify({'success': False, 'message': 'Authentication service not configured'}), 500

        data = request.get_json() or {}
        new_email = (data.get('email') or '').strip()
        first_name = (data.get('first_name') or '').strip()
        last_name = (data.get('last_name') or '').strip()
        country = (data.get('country') or '').strip()

        auth_header = request.headers.get('Authorization', '')
        current_email = getattr(g, 'user_email', '')
        if auth_header.lower().startswith('bearer '):
            current_user = verify_token(auth_header[7:].strip())
            current_email = (current_user or {}).get('email', current_email)

        update_payload = {
            'user_metadata': {
                'first_name': first_name,
                'last_name': last_name,
                'country': country
            }
        }

        if new_email and new_email != current_email:
            update_payload['email'] = new_email

        if not is_valid_uuid(g.user_id):
            return jsonify({
                'success': True,
                'message': 'Account details updated in test mode',
                'user': {
                    'id': g.user_id,
                    'email': new_email or current_email,
                    'first_name': first_name,
                    'last_name': last_name,
                    'country': country
                }
            })

        auth_supabase.auth.admin.update_user_by_id(g.user_id, update_payload)

        return jsonify({
            'success': True,
            'message': 'Account details updated successfully',
            'user': {
                'id': g.user_id,
                'email': new_email or current_email,
                'first_name': first_name,
                'last_name': last_name,
                'country': country
            }
        })
    except Exception as e:
        logger.exception("Account update failed")
        return _safe_api_error('Failed to update account', e, 400)


@app.route('/api/auth/password/reset-request', methods=['POST'])
@limiter.limit("3 per minute")
@require_auth
def auth_password_reset_request():
    """Send password reset email to current signed-in user."""
    try:
        success, message = request_password_reset(g.user_email)
        return jsonify({'success': success, 'message': message}), 200 if success else 400
    except Exception as e:
        logger.exception("Password reset email failed")
        return _safe_api_error('An unexpected error occurred', e)


@app.route('/api/auth/password/update', methods=['POST'])
@require_auth
def auth_password_update():
    """Update password directly for signed-in user."""
    try:
        if not auth_supabase:
            return jsonify({'success': False, 'message': 'Authentication service not configured'}), 500

        data = request.get_json() or {}
        new_password = data.get('new_password', '')
        confirm_password = data.get('confirm_password', '')

        if not new_password:
            return jsonify({'success': False, 'message': 'New password is required'}), 400
        if len(new_password) < 8:
            return jsonify({'success': False, 'message': 'Password must be at least 8 characters'}), 400
        if confirm_password and new_password != confirm_password:
            return jsonify({'success': False, 'message': 'Password confirmation does not match'}), 400

        if not is_valid_uuid(g.user_id):
            return jsonify({'success': True, 'message': 'Password updated in test mode'})

        auth_supabase.auth.admin.update_user_by_id(g.user_id, {'password': new_password})
        return jsonify({'success': True, 'message': 'Password updated successfully'})
    except Exception as e:
        logger.exception("Password update failed")
        return _safe_api_error('Failed to update password', e, 400)


# ── Forgot-password OTP flow (unauthenticated) ────────────────────────────────

def _get_uid_by_email(email: str) -> Optional[str]:
    """Look up Supabase auth user ID by email via admin REST API."""
    import requests as _http
    service_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY', '').strip()
    supabase_url = os.getenv('SUPABASE_URL', '').strip().rstrip('/')
    if not service_key or not supabase_url:
        return None
    try:
        resp = _http.get(
            f"{supabase_url}/auth/v1/admin/users",
            headers={'apikey': service_key, 'Authorization': f'Bearer {service_key}'},
            params={'email': email, 'page': 1, 'per_page': 500},
            timeout=10,
        )
        data = resp.json() or {}
        users = data.get('users', [])
        match = next((u for u in users if isinstance(u, dict) and u.get('email', '').lower() == email.lower()), None)
        return match['id'] if match else None
    except Exception as e:
        logger.warning('Email->UID lookup failed: %s', e)
        return None


@app.route('/api/auth/forgot', methods=['POST'])
@limiter.limit("10 per hour")
def auth_forgot():
    """Step 1: generate a 6-digit OTP, store in Supabase, and email it."""
    data = request.get_json(silent=True) or {}
    email = (data.get('email') or '').strip().lower()
    allow_supabase_reset_fallback = str(
        os.getenv('PASSWORD_RESET_SUPABASE_FALLBACK', 'false')
    ).strip().lower() in {'1', 'true', 'yes', 'on'}
    if not email or '@' not in email:
        return jsonify({'success': False, 'message': 'A valid email address is required.'}), 400
    otp = str(secrets.randbelow(10 ** 6)).zfill(6)
    expiry = datetime.utcnow() + timedelta(minutes=_OTP_TTL_MINUTES)
    try:
        _otp_upsert(email, otp, expiry)
        logger.info('[FORGOT_PASSWORD] OTP generated for %s, attempting email send', email)
    except Exception as exc:
        logger.exception('[FORGOT_PASSWORD] OTP upsert failed for %s: %s', email, exc)
        return jsonify({'success': False, 'message': 'Could not generate reset code. Please try again.'}), 500
    try:
        sent = _send_otp_email_sync(email, otp)
        if not sent:
            logger.error('[FORGOT_PASSWORD] OTP email failed to send to %s', email)
            if allow_supabase_reset_fallback:
                fallback_ok, fallback_msg = request_password_reset(email)
                if fallback_ok:
                    logger.info('[FORGOT_PASSWORD] Supabase fallback reset email sent for %s', email)
                    return jsonify({
                        'success': True,
                        'message': 'Reset email sent via backup provider. Please check your inbox.',
                        'reset_mode': 'link'
                    })
                logger.error('[FORGOT_PASSWORD] Supabase fallback failed for %s: %s', email, fallback_msg)
            else:
                logger.info('[FORGOT_PASSWORD] Supabase fallback disabled for %s', email)
            return jsonify({'success': False, 'message': 'Could not send reset code right now. Please try again in a minute.'}), 502
        logger.info('[FORGOT_PASSWORD] OTP email sent to %s', email)
        return jsonify({'success': True, 'message': 'Reset code sent – check your inbox.', 'reset_mode': 'otp'})
    except Exception as e:
        logger.error('[FORGOT_PASSWORD] Email send failed for %s: %s', email, e)
        if allow_supabase_reset_fallback:
            fallback_ok, fallback_msg = request_password_reset(email)
            if fallback_ok:
                logger.info('[FORGOT_PASSWORD] Supabase fallback reset email sent for %s after exception', email)
                return jsonify({
                    'success': True,
                    'message': 'Reset email sent via backup provider. Please check your inbox.',
                    'reset_mode': 'link'
                })
            logger.error('[FORGOT_PASSWORD] Supabase fallback failed after exception for %s: %s', email, fallback_msg)
        else:
            logger.info('[FORGOT_PASSWORD] Supabase fallback disabled after exception for %s', email)
        return jsonify({'success': False, 'message': 'Could not send reset code right now. Please try again in a minute.'}), 502


@app.route('/api/auth/verify-otp', methods=['POST'])
@limiter.limit("20 per hour")
def auth_verify_otp():
    """Step 2: validate the 6-digit OTP against Supabase record."""
    data = request.get_json(silent=True) or {}
    email = (data.get('email') or '').strip().lower()
    otp_in = (data.get('otp') or '').strip()
    entry = _otp_get(email)
    if not entry:
        return jsonify({'success': False, 'message': 'Code not found – please request a new one.'}), 400
    if _otp_expired(entry['expires_at']):
        _otp_delete(email)
        return jsonify({'success': False, 'message': 'Code expired – please request a new one.'}), 400
    if otp_in != entry['code']:
        return jsonify({'success': False, 'message': 'Incorrect code – please try again.'}), 400
    return jsonify({'success': True})


@app.route('/api/auth/reset-password', methods=['POST'])
@limiter.limit("10 per hour")
def auth_reset_password():
    """Step 3: verify OTP then update password via Supabase admin API."""
    data = request.get_json(silent=True) or {}
    email = (data.get('email') or '').strip().lower()
    otp_in = (data.get('otp') or '').strip()
    new_password = (data.get('newPassword') or '').strip()
    if not new_password or len(new_password) < 8:
        return jsonify({'success': False, 'message': 'Password must be at least 8 characters.'}), 400
    entry = _otp_get(email)
    if not entry or _otp_expired(entry['expires_at']) or otp_in != entry['code']:
        return jsonify({'success': False, 'message': 'Code invalid or expired – please restart the reset flow.'}), 400
    if not auth_supabase:
        return jsonify({'success': False, 'message': 'Auth service not configured.'}), 500
    user_id = _get_uid_by_email(email)
    if not user_id:
        return jsonify({'success': False, 'message': 'No account found for that email address.'}), 404
    try:
        current_meta = {}
        try:
            user_resp = auth_supabase.auth.admin.get_user_by_id(user_id)
            user_obj = getattr(user_resp, 'user', None) or getattr(user_resp, 'data', None) or user_resp
            if isinstance(user_obj, dict):
                current_meta = dict(user_obj.get('user_metadata') or {})
            else:
                current_meta = dict(getattr(user_obj, 'user_metadata', {}) or {})
        except Exception:
            current_meta = {}
        current_meta['has_password'] = True
        auth_supabase.auth.admin.update_user_by_id(user_id, {
            'password': new_password,
            'user_metadata': current_meta,
        })
        _otp_delete(email)
        logger.info('Password reset complete for %s', email)
        return jsonify({'success': True, 'message': 'Password updated successfully.'})
    except Exception as e:
        logger.exception('Password reset via admin API failed for %s', email)
        return _safe_api_error('Failed to update password', e, 500)


@app.route('/api/auth/reset-password-link', methods=['POST'])
@limiter.limit("10 per hour")
def auth_reset_password_link():
    """Set new password using Supabase recovery access token from reset link flow."""
    data = request.get_json(silent=True) or {}
    access_token = (data.get('access_token') or '').strip()
    new_password = (data.get('newPassword') or '').strip()

    if not access_token:
        return jsonify({'success': False, 'message': 'Missing recovery token.'}), 400
    if not new_password or len(new_password) < 8:
        return jsonify({'success': False, 'message': 'Password must be at least 8 characters.'}), 400

    user = verify_token(access_token)
    if not user:
        return jsonify({'success': False, 'message': 'Recovery link is invalid or expired.'}), 401

    base_url = (os.getenv('SUPABASE_URL') or '').strip().rstrip('/')
    anon_key = (os.getenv('SUPABASE_ANON_KEY') or os.getenv('SUPABASE_KEY') or '').strip()
    if not base_url or not anon_key:
        return jsonify({'success': False, 'message': 'Auth service not configured.'}), 500

    try:
        resp = requests.put(
            f"{base_url}/auth/v1/user",
            headers={
                'apikey': anon_key,
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json',
            },
            json={'password': new_password},
            timeout=(10, 30),
        )
        if resp.status_code >= 400:
            msg = 'Failed to update password from recovery link.'
            try:
                body = resp.json() if resp.content else {}
                if isinstance(body, dict):
                    msg = body.get('msg') or body.get('error_description') or body.get('error') or msg
            except Exception:
                pass
            logger.warning('Recovery password update failed: status=%s body=%s', resp.status_code, resp.text[:300])
            return jsonify({'success': False, 'message': msg}), 400 if resp.status_code < 500 else 502

        try:
            if auth_supabase and user.get('id'):
                current_meta = {}
                try:
                    user_resp = auth_supabase.auth.admin.get_user_by_id(user.get('id'))
                    user_obj = getattr(user_resp, 'user', None) or getattr(user_resp, 'data', None) or user_resp
                    if isinstance(user_obj, dict):
                        current_meta = dict(user_obj.get('user_metadata') or {})
                    else:
                        current_meta = dict(getattr(user_obj, 'user_metadata', {}) or {})
                except Exception:
                    current_meta = {}
                current_meta['has_password'] = True
                auth_supabase.auth.admin.update_user_by_id(user.get('id'), {'user_metadata': current_meta})
        except Exception:
            logger.warning('Could not persist has_password marker for %s', user.get('email', 'unknown'))

        logger.info('Password reset complete via recovery link for %s', user.get('email', 'unknown'))
        return jsonify({'success': True, 'message': 'Password updated successfully.'})
    except Exception as exc:
        logger.exception('Password reset via recovery link failed: %s', exc)
        return jsonify({'success': False, 'message': 'Could not update password right now. Please try again.'}), 502


@app.route('/login')
def login_page():
    """Serve login/signup page"""
    supabase_url = (os.getenv('SUPABASE_URL') or '').strip().rstrip('/')
    anon_key = (os.getenv('SUPABASE_ANON_KEY') or os.getenv('SUPABASE_KEY') or '').strip()
    return render_template('auth.html', supabase_url=supabase_url, supabase_anon_key=anon_key)


@app.route('/auth/callback')
def auth_callback_page():
    """Supabase email verification callback handler page."""
    supabase_url = (os.getenv('SUPABASE_URL') or '').strip().rstrip('/')
    anon_key = (os.getenv('SUPABASE_ANON_KEY') or os.getenv('SUPABASE_KEY') or '').strip()
    return render_template('auth_callback.html', supabase_url=supabase_url, supabase_anon_key=anon_key)


@app.route('/auth/reset-callback')
def auth_reset_callback_page():
    """Supabase password recovery callback handler page."""
    supabase_url = (os.getenv('SUPABASE_URL') or '').strip().rstrip('/')
    anon_key = (os.getenv('SUPABASE_ANON_KEY') or os.getenv('SUPABASE_KEY') or '').strip()
    return render_template('auth_callback.html', supabase_url=supabase_url, supabase_anon_key=anon_key)


@app.route('/auth/logout')
def logout_page():
    """Logout page (clears token and redirects)"""
    # Token is stored on client-side, just redirect to login
    return redirect(url_for('login_page'))

# ── Admin routes moved to routes/admin.py Blueprint (P1-6) ──────────────────

@app.route('/api/account/link_request', methods=['POST'])
def account_link_request():
    """Users can request account-linking (OAuth -> existing email account). This creates a system log entry for admins to act."""
    try:
        payload = request.get_json(silent=True) or {}
        email = (payload.get('email') or '').strip()
        provider = (payload.get('provider') or '').strip()
        provider_user_id = (payload.get('provider_user_id') or '').strip()
        if not email or not provider or not provider_user_id:
            return jsonify({'success': False, 'message': 'email, provider and provider_user_id are required'}), 400

        # record a system_logs entry for admins to review
        if auth_supabase:
            try:
                auth_supabase.table('system_logs').insert({
                    'level': 'info',
                    'message': 'account_link_request',
                    'request_path': request.path,
                    'request_method': request.method,
                    'metadata': {
                        'email': email,
                        'provider': provider,
                        'provider_user_id': provider_user_id,
                        'remote_addr': request.remote_addr
                    }
                }).execute()
            except Exception:
                pass

        logger.info('Account link request: %s %s', email, provider)
        return jsonify({'success': True, 'message': 'Link request recorded. An admin will review and link accounts.'})
    except Exception as e:
        logger.error('Link request failed: %s', e)
        return _safe_api_error('An unexpected error occurred', e)


@app.route('/api/billing/plans', methods=['GET'])
@require_auth
def billing_plans():
    plans = []
    for plan_code in ('starter', 'creator'):
        normalized = _normalize_subscription_plan(plan_code)
        plans.append({
            'plan': plan_code,
            'duration_months': normalized[1] if normalized else 0,
            'amount_inr': _plan_price_inr(plan_code),
            'amount_usd': _plan_price_usd(plan_code),
            'limits': _get_plan_limits(plan_code)
        })
    return jsonify({'success': True, 'plans': plans})


@app.route('/api/billing/status', methods=['GET'])
@require_auth
def billing_status():
    user_id = get_current_user_id()
    subscription = _get_subscription_row(user_id)
    effective_plan = _get_effective_plan(user_id)
    limits = _get_plan_limits(effective_plan)
    usage_row = _get_monthly_usage_row(user_id)
    scheduled_count = _get_user_scheduled_count(user_id)

    # Best-effort reminder: manual renewal warning near plan expiry.
    _maybe_send_subscription_expiry_reminder(user_id, subscription, effective_plan, getattr(g, 'user_email', ''))

    return jsonify({
        'success': True,
        'billing': {
            'effective_plan': effective_plan,
            'subscription': {
                'plan': subscription.get('plan') or 'free',
                'status': subscription.get('status') or 'inactive',
                'current_period_start': subscription.get('current_period_start'),
                'current_period_end': subscription.get('current_period_end'),
                'cancel_at_period_end': bool(subscription.get('cancel_at_period_end')),
                'scheduled_plan': subscription.get('scheduled_plan') or None,
                'current_plan_currency': subscription.get('current_plan_currency') or None,
                'current_plan_price_minor': int(subscription.get('current_plan_price_minor') or 0),
            },
            'limits': limits,
            'usage': {
                'posts_generated': int(usage_row.get('posts_generated') or 0),
                'posts_published': int(usage_row.get('posts_published') or 0),
                'kb_files_uploaded': int(usage_row.get('kb_files_uploaded') or 0),
                'kb_storage_bytes': int(usage_row.get('kb_storage_bytes') or 0),
                'scheduled_posts': int(scheduled_count)
            },
            'razorpay': {
                'key_id': os.getenv('RAZORPAY_KEY_ID', ''),
                'configured': bool((os.getenv('RAZORPAY_KEY_ID') or '').strip() and (os.getenv('RAZORPAY_KEY_SECRET') or '').strip())
            }
        }
    })


def _validate_coupon_code(code: str) -> dict:
    """Validate a discount code against the DB. Returns {'valid': bool, 'discount_pct': int, 'message': str}"""
    if not auth_supabase or not code:
        return {'valid': False, 'discount_pct': 0, 'message': 'Invalid code'}
    try:
        res = auth_supabase.table('discount_codes').select(
            'id,code,discount_pct,max_uses,uses,valid_from,valid_until,is_active'
        ).eq('code', code.upper().strip()).execute()
        rows = res.data or []
        if not rows:
            return {'valid': False, 'discount_pct': 0, 'message': 'Code not found'}
        row = rows[0]
        if not row.get('is_active'):
            return {'valid': False, 'discount_pct': 0, 'message': 'Code is no longer active'}
        if row.get('uses', 0) >= row.get('max_uses', 0):
            return {'valid': False, 'discount_pct': 0, 'message': 'Code has reached its usage limit'}
        now_utc = datetime.utcnow().isoformat()
        valid_from = row.get('valid_from')
        valid_until = row.get('valid_until')
        if valid_from and now_utc < valid_from:
            return {'valid': False, 'discount_pct': 0, 'message': 'Code is not yet active'}
        if valid_until and now_utc > valid_until:
            return {'valid': False, 'discount_pct': 0, 'message': 'Code has expired'}
        return {'valid': True, 'discount_pct': int(row['discount_pct']), 'code_id': row['id'], 'message': 'Code applied'}
    except Exception as e:
        logger.error("Coupon validation error: %s", e)
        return {'valid': False, 'discount_pct': 0, 'message': 'Code validation failed'}


def _redeem_coupon_code(code: str) -> bool:
    """Atomically increment uses count for a coupon code. Returns True on success."""
    if not auth_supabase or not code:
        return False
    try:
        res = auth_supabase.table('discount_codes').select('id,uses,max_uses').eq('code', code.upper().strip()).execute()
        rows = res.data or []
        if not rows:
            return False
        row = rows[0]
        new_uses = int(row.get('uses', 0)) + 1
        auth_supabase.table('discount_codes').update({'uses': new_uses}).eq('id', row['id']).execute()
        return True
    except Exception as e:
        logger.error("Coupon redeem error: %s", e)
        return False


@app.route('/api/billing/validate-coupon', methods=['POST'])
@require_auth
def billing_validate_coupon():
    """Validate a discount/coupon code without redeeming it."""
    try:
        data = request.get_json(silent=True) or {}
        code = str(data.get('code') or '').strip()
        if not code:
            return jsonify({'success': False, 'valid': False, 'message': 'Coupon code is required'}), 400
        result = _validate_coupon_code(code)
        return jsonify({'success': True, **result})
    except Exception as e:
        logger.exception("Coupon validation endpoint failed")
        return _safe_api_error('Validation failed', e)


@app.route('/api/billing/create-order', methods=['POST'])
@require_auth
def billing_create_order():
    try:
        user_id = get_current_user_id()
        data = request.get_json(silent=True) or {}
        normalized = _normalize_subscription_plan(data.get('plan'))
        if not normalized or normalized[0] == 'free':
            return jsonify({'success': False, 'message': 'Invalid plan. Use starter or creator.'}), 400

        plan = normalized[0]
        region = str(data.get('region', 'IN') or 'IN').strip().upper()
        amount_major, currency = _plan_checkout_price(plan, region)
        if amount_major <= 0:
            return jsonify({'success': False, 'message': 'Invalid plan price configuration'}), 500

        # --- Coupon / discount ---
        coupon_code = str(data.get('coupon_code') or '').strip().upper() or None
        discount_pct = 0
        coupon_message = ''
        if coupon_code:
            coupon_result = _validate_coupon_code(coupon_code)
            if coupon_result['valid']:
                discount_pct = coupon_result['discount_pct']
                amount_major = int(amount_major * (100 - discount_pct) // 100)
                coupon_message = f"{discount_pct}% discount applied"
            else:
                return jsonify({'success': False, 'message': coupon_result['message']}), 400

        key_id, key_secret = _razorpay_keys()
        if not key_id or not key_secret:
            return jsonify({'success': False, 'message': 'Razorpay is not configured on server'}), 503

        receipt = f"sub_{plan}_{user_id[:8]}_{int(time.time())}"
        order = _create_razorpay_order(
            amount_major=amount_major,
            currency=currency,
            receipt=receipt,
            user_id=user_id,
            plan=plan,
            extra_notes={
                'current_plan_currency': currency,
                'current_plan_price_minor': int(amount_major * 100),
            },
        )
        return jsonify({
            'success': True,
            'order': order,
            'plan': plan,
            'amount': amount_major,
            'amount_minor': int(amount_major * 100),
            'currency': currency,
            'razorpay_key_id': key_id,
            'discount_pct': discount_pct,
            'coupon_code': coupon_code,
            'coupon_message': coupon_message,
        })
    except Exception as e:
        logger.exception("Billing create order failed")
        return _safe_api_error('An unexpected error occurred', e)


@app.route('/api/billing/cancel', methods=['POST'])
@require_auth
def billing_cancel():
    """
    Cancel subscription at end of current billing period.
    User keeps their paid plan until period_end, then drops to free.
    Does NOT immediately downgrade.
    """
    try:
        user_id = get_current_user_id()
        if not auth_supabase or not is_valid_uuid(user_id):
            return jsonify({'success': False, 'message': 'Invalid session'}), 401

        rows = auth_supabase.table('subscriptions').select('*').eq('user_id', user_id).limit(1).execute()
        sub = rows.data[0] if rows.data else None

        if not sub or not _is_subscription_active(sub):
            return jsonify({'success': False, 'message': 'No active subscription to cancel'}), 400

        period_end = sub.get('current_period_end', '')
        now = datetime.utcnow()

        auth_supabase.table('subscriptions').update({
            'cancel_at_period_end': True,
            'scheduled_plan': 'free',
            'updated_at': now.isoformat() + 'Z'
        }).eq('user_id', user_id).execute()

        return jsonify({
            'success': True,
            'message': f'Subscription will be cancelled at end of billing period.',
            'cancel_at_period_end': True,
            'current_period_end': period_end
        })
    except Exception as e:
        logger.exception("Billing cancel failed")
        return _safe_api_error('An unexpected error occurred', e)


@app.route('/api/billing/schedule-downgrade', methods=['POST'])
@require_auth
def billing_schedule_downgrade_live():
    try:
        user_id = get_current_user_id()
        if not auth_supabase or not is_valid_uuid(user_id):
            return jsonify({'success': False, 'message': 'Invalid session'}), 401

        data = request.get_json(silent=True) or {}
        new_plan = str(data.get('new_plan') or '').strip().lower()
        if new_plan not in {'starter', 'free'}:
            return jsonify({'success': False, 'message': 'Invalid plan for downgrade. Use starter or free.'}), 400

        rows = auth_supabase.table('subscriptions').select('*').eq('user_id', user_id).limit(1).execute()
        sub = rows.data[0] if rows.data else None
        if not sub or not _is_subscription_active(sub):
            return jsonify({'success': False, 'message': 'No active subscription found'}), 400

        current_plan = str(sub.get('plan') or 'free').lower()
        plan_order = {'free': 0, 'starter': 1, 'creator': 2, 'pro': 3}
        if plan_order.get(new_plan, 0) >= plan_order.get(current_plan, 0):
            return jsonify({'success': False, 'message': 'That is not a downgrade from your current plan'}), 400

        period_end = sub.get('current_period_end', '')
        now = datetime.utcnow()
        auth_supabase.table('subscriptions').update({
            'scheduled_plan': new_plan,
            'cancel_at_period_end': (new_plan == 'free'),
            'updated_at': now.isoformat() + 'Z'
        }).eq('user_id', user_id).execute()

        return jsonify({
            'success': True,
            'message': f'Downgrade to {new_plan.capitalize()} scheduled.',
            'scheduled_plan': new_plan,
            'effective_from': period_end
        })
    except Exception as e:
        logger.exception("Billing schedule downgrade failed")
        return _safe_api_error('An unexpected error occurred', e)


@app.route('/api/billing/upgrade-plan', methods=['POST'])
@require_auth
def billing_upgrade_plan():
    """
    Upgrade current plan to a better plan with proration.
    
    Request: {
        "new_plan": "creator",  # "starter" or "creator"
        "region": "IN"          # "IN" or "ROW" (defaults to IN)
    }
    
    Response: {
        "success": true,
        "prorated_amount": 67,
        "currency": "INR",
        "upgrade_type": "free_charge" | "prorated_charge" | "free_upgrade",
        "order": { ... },  // Only if prorated_amount > 0
        "message": "..."
    }
    """
    try:
        user_id = get_current_user_id()
        data = request.get_json(silent=True) or {}
        new_plan = str(data.get('new_plan') or '').strip().lower()
        region = str(data.get('region') or 'IN').strip().upper()
        
        if not new_plan or new_plan not in {'starter', 'creator', 'pro'}:
            return jsonify({'success': False, 'message': 'Invalid plan. Use starter or creator.'}), 400
        
        # Calculate proration
        proration = _calculate_proration(user_id, new_plan, region)
        
        if 'error' in proration:
            return jsonify({'success': False, 'message': proration['error']}), 400
        
        if 'reason' in proration:
            return jsonify({
                'success': False,
                'message': proration['reason'],
                'can_upgrade': False
            }), 400
        
        prorated_amount = proration['prorated_amount']
        currency = proration['currency']
        
        # If prorated amount is 0 or very small, it's a free upgrade
        if prorated_amount <= 0:
            # Free upgrade: directly activate new plan
            period_end_str = str(proration.get('period_end') or '')  # Keep existing end date
            try:
                rows = auth_supabase.table('subscriptions').select('current_period_end').eq('user_id', user_id).limit(1).execute()
                if rows.data:
                    period_end_str = rows.data[0].get('current_period_end', '')
            except Exception:
                pass
            
            normalized = _normalize_subscription_plan(new_plan)
            if normalized:
                now = datetime.utcnow()
                payload = {
                    'user_id': user_id,
                    'plan': normalized[0],
                    'status': 'active',
                    'current_period_start': now.isoformat() + 'Z',
                    # Keep same end date, just update plan
                    'scheduled_plan': None,
                    'current_plan_currency': currency,
                    'current_plan_price_minor': proration.get('price_new_plan_minor', 0),
                    'updated_at': now.isoformat() + 'Z',
                    'billing_provider': 'razorpay'
                }
                if period_end_str:
                    payload['current_period_end'] = period_end_str
                
                try:
                    auth_supabase.table('subscriptions').upsert(payload, on_conflict='user_id').execute()
                    auth_supabase.table('billing_events').insert({
                        'event_type': 'plan_upgrade',
                        'user_id': user_id,
                        'plan': new_plan,
                        'prorated_amount': 0,
                        'upgrade_type': 'free_upgrade',
                    }).execute()
                except Exception as e:
                    logger.warning(f"Free upgrade activation failed: {e}")
            
            return jsonify({
                'success': True,
                'prorated_amount': 0,
                'currency': currency,
                'upgrade_type': 'free_upgrade',
                'message': f'Upgraded to {new_plan} at no additional cost!'
            })
        
        # Prorated charge required: create Razorpay order
        key_id, key_secret = _razorpay_keys()
        if not key_id or not key_secret:
            return jsonify({'success': False, 'message': 'Razorpay is not configured on server'}), 503

        # amount_major is in major currency units (₹ or $).
        # _create_razorpay_order multiplies by 100 internally to get paise/cents.
        # Round to nearest integer (Razorpay requires whole paise amounts).
        amount_minor = int(proration.get('prorated_amount_minor') or 0)

        # If rounding brings it to zero, treat as free upgrade
        if amount_minor <= 0:
            return jsonify({
                'success': True,
                'prorated_amount': 0,
                'currency': currency,
                'upgrade_type': 'free_upgrade',
                'message': f'Upgraded to {new_plan} at no additional cost!'
            })
        
        receipt = f"upg_{new_plan}_{user_id[:8]}_{int(time.time())}"
        order = _create_razorpay_order(
            amount_minor=amount_minor,
            currency=currency,
            receipt=receipt,
            user_id=user_id,
            plan=new_plan,
            extra_notes={
                'current_plan_currency': currency,
                'current_plan_price_minor': proration.get('price_new_plan_minor', 0),
                'prorated_amount_minor': amount_minor,
            },
        )
        
        return jsonify({
            'success': True,
            'prorated_amount': prorated_amount,
            'prorated_amount_minor': amount_minor,
            'currency': currency,
            'upgrade_type': 'prorated_charge',
            'order': order,
            'razorpay_key_id': key_id,
            'message': f'Prorated charge: {prorated_amount} {currency} for {proration["days_remaining"]} days remaining'
        })
        
    except Exception as e:
        logger.exception("Billing upgrade plan failed")
        return _safe_api_error('An unexpected error occurred', e)


@app.route('/api/billing/verify-payment', methods=['POST'])
@require_auth
def billing_verify_payment():
    try:
        user_id = get_current_user_id()
        data = request.get_json(silent=True) or {}
        order_id = str(data.get('order_id') or data.get('razorpay_order_id') or '').strip()
        payment_id = str(data.get('payment_id') or data.get('razorpay_payment_id') or '').strip()
        signature = str(data.get('signature') or data.get('razorpay_signature') or '').strip()
        plan = str(data.get('plan') or '').strip()
        currency = str(data.get('currency') or 'INR').strip().upper() or 'INR'
        amount_minor = int(data.get('amount_minor') or 0)
        coupon_code = str(data.get('coupon_code') or '').strip().upper() or None

        if not order_id or not payment_id or not signature or not plan:
            return jsonify({'success': False, 'message': 'order_id, payment_id, signature, and plan are required'}), 400

        normalized = _normalize_subscription_plan(plan)
        if not normalized or normalized[0] == 'free':
            return jsonify({'success': False, 'message': 'Invalid plan'}), 400

        if not _verify_razorpay_payment_signature(order_id, payment_id, signature):
            return jsonify({'success': False, 'message': 'Invalid Razorpay payment signature'}), 400

        activated = _activate_subscription_from_payment(
            user_id,
            normalized[0],
            payment_id=payment_id,
            order_id=order_id,
            amount_minor=amount_minor if amount_minor > 0 else None,
            currency=currency,
        )
        if not activated:
            return jsonify({'success': False, 'message': 'Failed to activate subscription'}), 500

        # Redeem coupon code if one was supplied with this payment
        if coupon_code:
            _redeem_coupon_code(coupon_code)

        return jsonify({
            'success': True,
            'message': 'Subscription activated successfully',
            'subscription': activated
        })
    except Exception as e:
        logger.exception("Billing verify payment failed")
        return _safe_api_error('An unexpected error occurred', e)


@app.route('/api/billing/webhook', methods=['POST'])
def billing_webhook():
    try:
        raw_body = request.get_data(cache=False)
        signature = request.headers.get('X-Razorpay-Signature', '')
        if not _verify_razorpay_webhook_signature(raw_body, signature):
            return jsonify({'success': False, 'message': 'Invalid webhook signature'}), 401

        payload = request.get_json(silent=True) or {}
        event = str(payload.get('event') or '').strip().lower()

        payment_entity = ((payload.get('payload') or {}).get('payment') or {}).get('entity') or {}
        order_entity = ((payload.get('payload') or {}).get('order') or {}).get('entity') or {}
        notes = payment_entity.get('notes') or order_entity.get('notes') or {}

        user_id = str(notes.get('user_id') or '').strip()
        plan = str(notes.get('plan') or '').strip()
        payment_id = str(payment_entity.get('id') or '').strip()
        order_id = str(payment_entity.get('order_id') or order_entity.get('id') or '').strip()
        currency = str(payment_entity.get('currency') or order_entity.get('currency') or 'INR').strip().upper() or 'INR'
        amount_minor = int(payment_entity.get('amount') or order_entity.get('amount') or 0)

        if event in {'payment.captured', 'order.paid'} and is_valid_uuid(user_id):
            # ── Idempotency check: skip if this (payment_id, event) was already processed
            if payment_id and auth_supabase:
                try:
                    existing = auth_supabase.table('billing_events').select('id').eq(
                        'payment_id', payment_id
                    ).eq('event_type', event).limit(1).execute()
                    if existing.data:
                        logger.info('Billing webhook duplicate skipped: payment_id=%s event=%s', payment_id, event)
                        return jsonify({'success': True, 'duplicate': True})
                except Exception as dup_err:
                    logger.debug('Billing idempotency check failed (proceeding): %s', dup_err)

            _activate_subscription_from_payment(
                user_id,
                plan,
                payment_id=payment_id,
                order_id=order_id,
                amount_minor=amount_minor if amount_minor > 0 else None,
                currency=currency,
            )

            # ── Record billing event for idempotency
            if payment_id and auth_supabase:
                try:
                    auth_supabase.table('billing_events').insert({
                        'payment_id': payment_id,
                        'event_type': event,
                        'user_id': user_id,
                        'plan': plan,
                        'order_id': order_id,
                        'raw_payload': payload,
                    }).execute()
                except Exception as rec_err:
                    logger.debug('Billing event record failed (non-fatal): %s', rec_err)

        return jsonify({'success': True})
    except Exception as e:
        logger.exception("Billing webhook failed")
        return _safe_api_error('An unexpected error occurred', e)

# ============= ROUTES =============

@app.route('/health', methods=['GET'])
def health_check():
    """Liveness / readiness probe for load-balancers & monitoring."""
    checks = {}
    overall = True

    # 1. Supabase DB
    try:
        if auth_supabase:
            auth_supabase.table('posts').select('id').limit(1).execute()
            checks['database'] = 'ok'
        else:
            checks['database'] = 'not_configured'
            overall = False
    except Exception as e:
        checks['database'] = f'error: {str(e)[:120]}'
        overall = False

    # 2. Redis (optional — used for rate-limiting)
    try:
        redis_url = os.getenv('REDIS_URL', '').strip()
        if redis_url:
            import redis as _redis_mod
            r = _redis_mod.from_url(redis_url, socket_connect_timeout=3, socket_timeout=3)
            r.ping()
            checks['redis'] = 'ok'
        else:
            checks['redis'] = 'not_configured'
    except Exception as e:
        checks['redis'] = f'error: {str(e)[:120]}'
        # Redis failure is non-fatal for overall health
        logger.debug('Health check: Redis ping failed: %s', e)

    # 3. Scheduler thread health
    if _SCHEDULER_THREAD is not None:
        if _SCHEDULER_THREAD.is_alive():
            stale = (time.time() - _SCHEDULER_HEARTBEAT) > _SCHEDULER_STALE_SEC if _SCHEDULER_HEARTBEAT else True
            if stale:
                checks['scheduler'] = 'stale'
                logger.warning('Scheduler heartbeat stale (last=%.0fs ago)', time.time() - _SCHEDULER_HEARTBEAT)
            else:
                checks['scheduler'] = 'ok'
        else:
            checks['scheduler'] = 'dead'
            overall = False
    else:
        checks['scheduler'] = 'not_started'

    status_code = 200 if overall else 503
    return jsonify({
        'status': 'healthy' if overall else 'degraded',
        'checks': checks,
        'version': os.getenv('APP_VERSION', 'unknown'),
        'uptime_seconds': int(time.time() - _APP_START_TIME),
    }), status_code


@app.route('/api/app-version', methods=['GET'])
def app_version_info():
    """Expose app boot/version info so clients can detect new deployments."""
    return jsonify({
        'success': True,
        'boot_id': _APP_BOOT_ID,
        'version': os.getenv('APP_VERSION', os.getenv('GIT_SHA', 'unknown')),
        'started_at_unix': int(_APP_START_TIME),
    }), 200


@app.route('/')
def dashboard():
    """Main dashboard (enterprise)"""
    config = load_config()
    return render_template('dashboard_enterprise.html', config=config)

@app.route('/dashboard-enterprise')
def dashboard_enterprise():
    """Legacy enterprise URL: redirect to main dashboard"""
    return redirect(url_for('dashboard'))

@app.route('/api/config', methods=['GET'])
@require_auth
def get_config():
    """Get current configuration"""
    user_id = get_current_user_id()
    config = load_config(user_id)
    # Don't expose full API keys
    config['GOOGLE_API_KEY'] = '***' + config['GOOGLE_API_KEY'][-8:] if config['GOOGLE_API_KEY'] else ''
    config['OPENAI_API_KEY'] = '***' + config['OPENAI_API_KEY'][-8:] if config.get('OPENAI_API_KEY') else ''
    config['ANTHROPIC_API_KEY'] = '***' + config['ANTHROPIC_API_KEY'][-8:] if config['ANTHROPIC_API_KEY'] else ''
    config['LINKEDIN_ACCESS_TOKEN'] = '***' + config['LINKEDIN_ACCESS_TOKEN'][-8:] if config['LINKEDIN_ACCESS_TOKEN'] else ''
    config['LINKEDIN_PERSON_ID'] = '***' + config['LINKEDIN_PERSON_ID'][-8:] if config['LINKEDIN_PERSON_ID'] else ''
    return jsonify(config)

@app.route('/api/config', methods=['POST'])
@require_auth
def update_config():
    """Update configuration"""
    try:
        data = request.get_json() or {}
        user_id = get_current_user_id()
        config = load_config(user_id)
        
        # Update all provided configuration values
        for key in data:
            value = data[key]
            if key in PLATFORM_MANAGED_AI_KEYS:
                continue
            # Skip masked values (don't overwrite with ***) but allow False, 0, empty strings
            if isinstance(value, str) and value.startswith('***'):
                continue
            config[key] = value
        
        save_config(config, user_id=user_id)
        logger.info(f"Configuration saved. TEST_MODE={config.get('TEST_MODE')}")
        return jsonify({'success': True, 'message': 'Configuration saved!'})
    except Exception as e:
        logger.exception("Failed to save config")
        return _safe_api_error('Request failed', e, 400)

@app.route('/api/test-linkedin', methods=['POST'])
@require_auth
def test_linkedin():
    """Test LinkedIn authentication"""
    try:
        from linkedin_poster import LinkedInPoster
        user_id = get_current_user_id()
        config_obj = load_config(user_id)
        poster = LinkedInPoster(
            test_mode=True,
            access_token=config_obj.get('LINKEDIN_ACCESS_TOKEN', ''),
            person_id=config_obj.get('LINKEDIN_PERSON_ID', '')
        )
        return jsonify({'success': True, 'message': 'LinkedIn authentication test passed!'})
    except Exception as e:
        return _safe_api_error('LinkedIn Error', e)
WORD_RE = re.compile(r"\b[\w'-]+\b")
HASHTAG_RE = re.compile(r"#([A-Za-z][A-Za-z0-9_]{1,49})")
EMOJI_RE = re.compile(
    "["
    "\U0001F300-\U0001F5FF"
    "\U0001F600-\U0001F64F"
    "\U0001F680-\U0001F6FF"
    "\U0001F700-\U0001F77F"
    "\U0001F780-\U0001F7FF"
    "\U0001F800-\U0001F8FF"
    "\U0001F900-\U0001F9FF"
    "\U0001FA00-\U0001FA6F"
    "\U0001FA70-\U0001FAFF"
    "\u2600-\u26FF"
    "\u2700-\u27BF"
    "]+",
    flags=re.UNICODE,
)


def clamp_int(value, minimum, maximum, default):
    try:
        value = int(value)
    except Exception:
        value = default
    return max(minimum, min(maximum, value))


def parse_content_topics(req_data: dict, config_obj: dict) -> list:
    raw_topics = req_data.get('topics')
    if isinstance(raw_topics, list):
        values = raw_topics
    elif isinstance(raw_topics, str):
        values = [part.strip() for part in raw_topics.split(',')]
    else:
        fallback = config_obj.get('CONTENT_TOPICS', '') or ''
        values = [part.strip() for part in str(fallback).split(',')]

    cleaned = []
    for topic in values:
        if not topic:
            continue
        normalized = str(topic).strip().replace('_', ' ')
        if normalized and normalized not in cleaned:
            cleaned.append(normalized)
    return cleaned


def words_count(text: str) -> int:
    return len(WORD_RE.findall(text or ''))


def enforce_word_ceiling(text: str, max_words: int) -> str:
    """Trim text to max_words, preserving paragraph structure and completing sentences."""
    text = (text or '').strip()
    if words_count(text) <= max_words:
        return text
    # Split into paragraphs, accumulate until budget is exceeded
    paragraphs = text.split('\n\n')
    kept = []
    running = 0
    for para in paragraphs:
        para_wc = words_count(para)
        if running + para_wc <= max_words:
            kept.append(para)
            running += para_wc
        else:
            # Trim this paragraph at a sentence boundary within budget
            sentences = re.split(r'(?<=[.!?])\s+', para)
            for sent in sentences:
                sent_wc = words_count(sent)
                if running + sent_wc <= max_words:
                    kept.append(sent)
                    running += sent_wc
                else:
                    break
            break
    result = '\n\n'.join(kept).strip() if len(kept) > 0 else text[:max_words * 6]
    if result and result[-1] not in '.!?':
        result += '.'
    return result


def normalize_hashtags(tags: list) -> list:
    normalized = []
    seen = set()
    for tag in tags:
        if not tag:
            continue
        clean = re.sub(r'[^A-Za-z0-9_]', '', str(tag))
        if len(clean) < 2:
            continue
        key = clean.lower()
        if key in seen:
            continue
        seen.add(key)
        normalized.append(f"#{clean}")
    return normalized


# Curated professional hashtag banks — real hashtags practitioners follow, not topic slugs.
_INDUSTRY_HASHTAG_BANK: dict = {
    'fintech':           ['FinTech', 'Payments', 'DigitalBanking', 'BankingTech', 'OpenBanking', 'PaymentInnovation', 'FinancialServices'],
    'finance':           ['Finance', 'FinancialServices', 'BankingTech', 'WealthManagement', 'FinTech'],
    'crypto':            ['Crypto', 'Web3', 'DeFi', 'Blockchain', 'CryptoFinance', 'OnChain'],
    'web3':              ['Web3', 'Blockchain', 'SmartContracts', 'DAOs', 'DecentralizedFinance', 'Web3Dev'],
    'saas':              ['SaaS', 'B2BSaaS', 'ProductLedGrowth', 'SaaSGrowth', 'TechStartup', 'ProductManagement'],
    'healthcare':        ['HealthTech', 'DigitalHealth', 'MedTech', 'HealthcareIT', 'PatientExperience', 'HealthcareInnovation'],
    'ecommerce':         ['Ecommerce', 'RetailTech', 'D2C', 'ConversionOptimization', 'CustomerExperience', 'EcommerceStrategy'],
    'genai':             ['GenerativeAI', 'AITools', 'LLM', 'AIStrategy', 'MachineLearning', 'ArtificialIntelligence'],
    'virtual_assistant': ['ConversationalAI', 'Automation', 'CustomerExperience', 'AIAssistant', 'ChatbotDevelopment'],
    'supply_chain':      ['SupplyChain', 'Logistics', 'SupplyChainTech', 'Operations', 'ProcureTech', 'SupplyChainManagement'],
    'tech':              ['Technology', 'SoftwareEngineering', 'TechLeadership', 'DevOps', 'Engineering'],
    'marketing':         ['DigitalMarketing', 'ContentMarketing', 'GrowthMarketing', 'B2BMarketing', 'MarTech'],
    'hr':                ['HRTech', 'PeopleOps', 'TalentManagement', 'FutureOfWork', 'HumanResources'],
    'legal':             ['LegalTech', 'Compliance', 'RegTech', 'LegalInnovation', 'CorporateLaw'],
}


def derive_hashtag_candidates(theme: str, industry: str, role: str, topics: list) -> list:
    """Return professional industry hashtags as candidates.

    Uses a curated per-industry bank so hashtags are real practitioners' tags
    (e.g. #FinTech #Payments) rather than topic-summarising slugs
    (e.g. #HowNovaPayReducedCheckoutFailure).
    """
    candidates = []

    # Priority 1 — curated industry bank (real, followable hashtags)
    industry_key = re.sub(r'[^a-z0-9_]', '_', (industry or '').lower().strip())
    bank_tags: list = _INDUSTRY_HASHTAG_BANK.get(industry_key, [])
    if not bank_tags:
        # Partial match fallback (e.g. "Fintech & Payments" → 'fintech')
        for key in _INDUSTRY_HASHTAG_BANK:
            if key in industry_key or industry_key.startswith(key[:4]):
                bank_tags = _INDUSTRY_HASHTAG_BANK[key]
                break
    candidates.extend(bank_tags[:5])

    # Priority 2 — clean industry label as a standalone tag
    if industry and len(industry) < 30:
        clean = re.sub(r'[^A-Za-z0-9]', '', industry)
        if len(clean) >= 3:
            candidates.append(clean)

    # Priority 3 — role as a standalone tag (CTO, Founder, ProductManager, etc.)
    if role and len(role) < 25:
        clean_role = re.sub(r'[^A-Za-z0-9]', '', role)
        if len(clean_role) >= 2:
            candidates.append(clean_role)

    # Priority 4 — single meaningful words from topics (not from theme — that produces slugs)
    for t in (topics or []):
        if not t:
            continue
        words = re.findall(r'[A-Za-z]{4,}', str(t))
        for w in words[:2]:
            candidates.append(w.capitalize())

    # Fallback
    candidates.extend(['Innovation', 'Leadership'])
    return normalize_hashtags(candidates)


def remove_hashtags_from_body(text: str) -> str:
    body = re.sub(r'(^|\s)#[A-Za-z][A-Za-z0-9_]{1,49}', ' ', text or '')
    body = body.replace('\r\n', '\n').replace('\r', '\n')
    body = re.sub(r'\n{3,}', '\n\n', body)

    cleaned_lines = []
    for line in body.split('\n'):
        compact = re.sub(r'[ \t]{2,}', ' ', line).strip()
        if compact:
            cleaned_lines.append(compact)
        elif cleaned_lines and cleaned_lines[-1] != '':
            cleaned_lines.append('')

    return '\n'.join(cleaned_lines).strip()


def apply_emoji_policy(text: str, emoji_level: str) -> str:
    if emoji_level == 'none':
        return EMOJI_RE.sub('', text or '').strip()
    return (text or '').strip()


def clean_linkedin_body(text: str) -> str:
    body = (text or '').replace('\r\n', '\n').replace('\r', '\n').strip()
    if not body:
        return ''

    # Remove markdown formatting artefacts
    body = re.sub(r'\*{1,3}', '', body)
    body = re.sub(r'`+', '', body)
    body = re.sub(r'^\s*[-•]\s+', '', body, flags=re.MULTILINE)
    body = re.sub(r'\n{3,}', '\n\n', body)

    # Preserve paragraph structure from the AI output
    raw_paragraphs = [p.strip() for p in body.split('\n\n') if p.strip()]
    if not raw_paragraphs:
        # Fallback: treat single lines as paragraphs
        raw_paragraphs = [ln.strip() for ln in body.split('\n') if ln.strip()]
    if not raw_paragraphs:
        return ''

    cleaned_paragraphs = []
    for para in raw_paragraphs:
        # Collapse multi-line within a paragraph to single line
        para = re.sub(r'\s*\n\s*', ' ', para)
        para = re.sub(r'\s{2,}', ' ', para).strip()
        if para:
            cleaned_paragraphs.append(para)

    # If result is a single giant paragraph (>350 chars), break it on sentence boundaries
    if len(cleaned_paragraphs) == 1 and len(cleaned_paragraphs[0]) > 350:
        text_blob = cleaned_paragraphs[0]
        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text_blob) if s.strip()]
        if len(sentences) >= 3:
            paragraphs_out = []
            current = []
            for sentence in sentences:
                candidate = (' '.join(current + [sentence])).strip()
                if current and (len(candidate) > 280 or len(current) >= 2):
                    paragraphs_out.append(' '.join(current).strip())
                    current = [sentence]
                else:
                    current.append(sentence)
            if current:
                paragraphs_out.append(' '.join(current).strip())
            cleaned_paragraphs = paragraphs_out

    return '\n\n'.join(cleaned_paragraphs).strip()


def ensure_engagement_hook(body: str, industry: str, role: str, topic: str) -> str:
    # The AI prompt (Rule 12 — TOPIC ANCHOR) now owns the opening sentence.
    # Post-processing hooks caused generic off-topic openers; disabled.
    return (body or '').strip()


def ensure_engagement_cta(body: str, role: str) -> str:
    """Only append a CTA if the post has no engagement element at all.
    The AI prompt already instructs a CTA — this is a last-resort safety net."""
    text = (body or '').strip()
    if not text:
        return text

    # Check the LAST paragraph only (not the whole body) for CTA signals
    paragraphs = text.split('\n\n')
    last_para = (paragraphs[-1] if paragraphs else text).lower()
    cta_markers = [
        'what do you think', 'what has worked', 'share your', 'drop a comment', 'comment below',
        'dm me', 'let me know', 'how are you', 'your take', 'agree or disagree',
        'curious', 'have you', 'thoughts?', 'thoughts on', 'would love to hear',
        'how do you', 'what would you', 'what are your', 'interested in hearing',
    ]
    has_cta = any(marker in last_para for marker in cta_markers) or last_para.rstrip().endswith('?')
    if has_cta:
        return text

    # Only append if the post is long enough to warrant a separate CTA
    if words_count(text) < 40:
        return text

    cta_line = "What's your experience with this?"
    return f"{text}\n\n{cta_line}".strip()


def wrap_linkedin_lines(body: str, width: int = 170) -> str:
    text = (body or '').strip()
    if not text:
        return text

    wrapped_paragraphs = []
    for paragraph in [p.strip() for p in text.split('\n\n') if p.strip()]:
        wrapped_paragraphs.append(
            textwrap.fill(paragraph, width=width, break_long_words=False, break_on_hyphens=False)
        )
    return '\n\n'.join(wrapped_paragraphs).strip()


def enforce_linkedin_quality(body: str, industry: str, role: str, topic: str, target_audience: str = '', emoji_level: str = 'moderate') -> str:
    content = clean_linkedin_body(body)
    content = apply_emoji_policy(content, emoji_level)
    content = ensure_engagement_hook(content, industry, role, topic)
    content = ensure_engagement_cta(content, role)
    content = wrap_linkedin_lines(content, width=170)
    return content.strip()


def _post_contract_heuristics(body: str, theme: str, goal_key: str) -> dict:
    text = str(body or '').strip()
    if not text:
        return {
            'score': 0,
            'clarity': 0,
            'novelty': 0,
            'specificity': 0,
            'hook': 0,
            'cta': 0,
            'issues': ['Empty output'],
            'first_line': ''
        }

    paragraphs = [p.strip() for p in re.split(r'\n\s*\n', text) if p.strip()]
    first_line = paragraphs[0].split('\n')[0].strip() if paragraphs else text[:120]
    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if s.strip()]
    avg_sentence_len = (sum(words_count(s) for s in sentences) / len(sentences)) if sentences else words_count(text)

    lower_text = text.lower()
    lower_first_line = first_line.lower()
    theme_tokens = [
        token for token in re.findall(r'[a-zA-Z0-9]+', str(theme or '').lower())
        if len(token) >= 4
    ]
    hook_topic_match = any(token in lower_first_line for token in theme_tokens[:6]) if theme_tokens else True
    hook_length_ok = len(first_line) <= 120

    cta_markers = [
        'what\'s your take', 'what do you think', 'curious', 'share your', 'drop a comment',
        'let me know', 'agree or disagree', 'thoughts?', 'have you seen', 'would you'
    ]
    has_cta = any(marker in lower_text for marker in cta_markers) or text.strip().endswith('?')

    numbers_count = len(re.findall(r'\b\d+(?:\.\d+)?%?\b', text))
    specificity_terms = len(re.findall(r'\b[A-Z]{2,}\b', text)) + numbers_count

    banned_generic = [
        'in today\'s fast-paced world', 'game changer', 'paradigm shift', 'cutting-edge', 'synergy',
        'move the needle', 'best practices', 'robust', 'transformative'
    ]
    banned_hits = sum(1 for phrase in banned_generic if phrase in lower_text)

    clarity = max(0, min(100, int(round(100 - max(0, avg_sentence_len - 18) * 3.4))))
    novelty = max(0, min(100, 76 - (banned_hits * 12) + (8 if 'but' in lower_text or 'however' in lower_text else 0)))
    specificity = max(0, min(100, 44 + min(40, specificity_terms * 7)))
    hook = max(0, min(100, (55 if hook_length_ok else 25) + (35 if hook_topic_match else 0)))
    cta = 88 if has_cta else 32

    if goal_key in {'spark_comments', 'grow_network'} and not text.strip().endswith('?'):
        cta = min(cta, 55)

    issues = []
    if not hook_length_ok:
        issues.append('Hook line exceeds 120 characters')
    if not hook_topic_match:
        issues.append('Opening line is not clearly anchored to the requested topic')
    if len(paragraphs) < 2:
        issues.append('Needs clearer paragraph structure (2+ short paragraphs)')
    if not has_cta:
        issues.append('Missing clear engagement CTA/question at the end')
    if banned_hits > 0:
        issues.append('Contains generic corporate phrasing')

    score = int(round((clarity * 0.24) + (novelty * 0.2) + (specificity * 0.2) + (hook * 0.2) + (cta * 0.16)))
    score = max(0, min(100, score))

    return {
        'score': score,
        'clarity': clarity,
        'novelty': novelty,
        'specificity': specificity,
        'hook': hook,
        'cta': cta,
        'issues': issues,
        'first_line': first_line,
    }


def _evaluate_post_quality(ai, body: str, theme: str, goal_key: str) -> dict:
    heuristic = _post_contract_heuristics(body, theme, goal_key)
    short_body = str(body or '').strip()[:1800]
    if not short_body:
        return heuristic

    eval_prompt = _PromptBuilder.build_evaluation_prompt(body, theme, goal_key)

    try:
        eval_result = ai.generate(eval_prompt, max_tokens=140, temperature=0.0, task='evaluate')
        raw = (eval_result.get('text') or '').strip()
        if raw.startswith('```'):
            raw = raw.split('```', 2)[1]
            if raw.strip().lower().startswith('json'):
                raw = raw.strip()[4:]
        match = re.search(r'\{.*\}', raw, flags=re.DOTALL)
        payload = json.loads(match.group(0) if match else raw)

        def _score(name: str, fallback: int) -> int:
            try:
                return max(0, min(100, int(payload.get(name, fallback))))
            except Exception:
                return fallback

        llm = {
            'clarity': _score('clarity', heuristic['clarity']),
            'novelty': _score('novelty', heuristic['novelty']),
            'specificity': _score('specificity', heuristic['specificity']),
            'hook': _score('hook', heuristic['hook']),
            'cta': _score('cta', heuristic['cta']),
            'overall': _score('overall', heuristic['score']),
            'issues': payload.get('issues') if isinstance(payload.get('issues'), list) else [],
        }

        merged = {
            'clarity': int(round((llm['clarity'] * 0.6) + (heuristic['clarity'] * 0.4))),
            'novelty': int(round((llm['novelty'] * 0.55) + (heuristic['novelty'] * 0.45))),
            'specificity': int(round((llm['specificity'] * 0.6) + (heuristic['specificity'] * 0.4))),
            'hook': int(round((llm['hook'] * 0.55) + (heuristic['hook'] * 0.45))),
            'cta': int(round((llm['cta'] * 0.55) + (heuristic['cta'] * 0.45))),
        }
        merged['score'] = int(round(
            (merged['clarity'] * 0.24)
            + (merged['novelty'] * 0.2)
            + (merged['specificity'] * 0.2)
            + (merged['hook'] * 0.2)
            + (merged['cta'] * 0.16)
        ))
        merged['issues'] = list(dict.fromkeys((heuristic.get('issues') or []) + llm.get('issues', [])))[:5]
        merged['first_line'] = heuristic.get('first_line', '')
        return merged
    except Exception as eval_error:
        logger.debug('Post evaluator fallback to heuristics: %s', eval_error)
        return heuristic


def _is_crypto_requested(industry: str, role: str, topic: str, topics: list, post_goal: str) -> bool:
    combined = ' '.join([
        str(industry or ''),
        str(role or ''),
        str(topic or ''),
        str(post_goal or ''),
        ' '.join([str(item or '') for item in (topics or [])])
    ]).lower()
    crypto_terms = ['crypto', 'cryptocurrency', 'web3', 'blockchain', 'defi', 'token', 'nft', 'bitcoin', 'ethereum', 'exchange']
    return any(term in combined for term in crypto_terms)


def _forbidden_terms_for_context(
    industry: str,
    role: str,
    topic: str,
    topics: list,
    post_goal: str = '',
    *_legacy_unused_args,
) -> list:
    if _is_crypto_requested(industry, role, topic, topics, post_goal):
        return []
    return [
        'crypto', 'cryptocurrency', 'web3', 'blockchain', 'defi', 'token', 'tokens', 'nft', 'nfts',
        'bitcoin', 'ethereum', 'solana', 'wallet', 'exchange', 'dex', 'cex'
    ]


def _find_forbidden_terms(text: str, forbidden_terms: list) -> list:
    body = str(text or '').lower()
    hits = []
    for term in forbidden_terms:
        if re.search(rf'\b{re.escape(term.lower())}\b', body):
            hits.append(term)
    return sorted(list(set(hits)))


# ── Production Grounding System ───────────────────────────────────────────────

def _expand_retrieval_queries(topic: str, industry: str, role: str, goal_key: str) -> list:
    """Generate 4-6 diverse search queries from user inputs to improve KB recall.

    Instead of searching with just the topic string, we create semantically
    varied queries so that relevant KB chunks are found even when the user's
    topic wording doesn't exactly match the stored text.
    
    IMPROVED: Added more query variations to catch content that uses different terminology.
    """
    queries = []
    topic = (topic or '').strip()
    industry = (industry or '').strip()
    role = (role or '').strip()

    # Q1 — the user's exact topic (highest priority)
    if topic:
        queries.append(topic)

    # Q2 — topic contextualised with industry
    if topic and industry:
        queries.append(f"{topic} in {industry}")

    # Q3 — topic contextualised with role perspective
    if topic and role:
        queries.append(f"{topic} from {role} perspective")
    
    # Q4 — just the main industry/role keywords (broader catch-all for any content in that domain)
    if industry or role:
        broad_parts = [p for p in [industry, role] if p]
        if broad_parts:
            queries.append(' '.join(broad_parts))
    
    # Q5 — goal + topic combination (often KB is organized by use case)
    goal_label = _GOAL_KEY_TO_LABEL.get(goal_key, goal_key or '')
    if topic and goal_label:
        queries.append(f"{topic} for {goal_label}")
    
    # Q6 — broader industry + role + goal combo (catch-all)
    goal_label = _GOAL_KEY_TO_LABEL.get(goal_key, goal_key or '')
    broad_parts = [p for p in [industry, role, goal_label, topic] if p]
    if broad_parts and ' '.join(broad_parts) not in [q for q in queries]:
        queries.append(' '.join(broad_parts))

    # Deduplicate while preserving order
    seen = set()
    unique = []
    for q in queries:
        q_lower = q.lower().strip()
        if q_lower and q_lower not in seen:
            seen.add(q_lower)
            unique.append(q)
    return unique or [topic or industry or 'general knowledge']


def _multi_query_kb_search(rag, queries: list, file_id_arg, k_per_query: int = 4,
                           strict_threshold: float = 0.75,
                           relaxed_threshold: float = 0.68) -> list:
    """Run multi-query retrieval against KB, deduplicate and rerank results.

    1. Each query is searched at strict threshold first.
    2. Any query that returns 0 hits is retried at relaxed threshold.
    3. Results are deduplicated by chunk id and sorted by descending similarity.
    """
    all_hits = {}  # keyed by chunk id to deduplicate

    for query in queries:
        hits = rag.similarity_search(
            query, k=k_per_query,
            match_threshold=strict_threshold,
            file_ids=file_id_arg,
        )
        if not hits:
            hits = rag.similarity_search(
                query, k=k_per_query,
                match_threshold=relaxed_threshold,
                file_ids=file_id_arg,
            )
        for hit in hits:
            chunk_id = hit.get('id') or hit.get('document', '')[:80]
            existing = all_hits.get(chunk_id)
            if existing is None or float(hit.get('similarity', 0)) > float(existing.get('similarity', 0)):
                all_hits[chunk_id] = hit

    # Sort by similarity descending and return top results
    ranked = sorted(all_hits.values(), key=lambda h: float(h.get('similarity', 0)), reverse=True)
    return ranked


_GROUNDING_FULL = 'grounded'       # ≥2 high-confidence KB hits
_GROUNDING_PARTIAL = 'partial'     # 1 hit or low avg similarity
_GROUNDING_NONE = 'ungrounded'     # no KB hits at all


def _classify_grounding_level(kb_hits: list, kb_used: bool, kb_mode: str) -> str:
    """Classify how well the generation is grounded in KB evidence.

    Returns one of: 'grounded', 'partial', 'ungrounded'.
    
    IMPROVED & ADAPTIVE: Lowered thresholds to be more permissive. Also uses adaptive
    thresholds if vector similarities are consistently weak (< 0.30), suggesting
    embedding model or vector DB issues on production.
    - FULL: avg_sim >= 0.70 AND 2+ high-confidence hits (or 0.20/0.15 if weak vectors)
    - PARTIAL: avg_sim >= 0.55 (or 0.10 if weak vectors)
    - NONE: default fallback
    """
    if kb_mode == 'no_kb' or not kb_used or not kb_hits:
        return _GROUNDING_NONE

    similarities = [float(h.get('similarity', 0)) for h in kb_hits if h]
    if not similarities:
        return _GROUNDING_NONE

    avg_sim = sum(similarities) / len(similarities)
    max_sim = max(similarities)
    
    # ADAPTIVE: Detect if vector similarities are weak (< 0.30) and adjust thresholds
    weak_vector_scores = max_sim < 0.30
    
    if weak_vector_scores:
        # LOW THRESHOLDS for weak vector systems (production embedding issues)
        logger.debug('Using adaptive (low) thresholds due to weak vector scores (max=%.3f)', max_sim)
        high_conf_count = sum(1 for s in similarities if s >= 0.20)  # Lowered from 0.70
        
        if high_conf_count >= 2 and avg_sim >= 0.15:
            return _GROUNDING_FULL
        elif len(similarities) >= 1 and avg_sim >= 0.10:
            return _GROUNDING_PARTIAL
        else:
            return _GROUNDING_NONE
    else:
        # NORMAL THRESHOLDS — calibrated for match_threshold=0.30 retrieval.
        # High-confidence bar is 0.60 (not 0.70) because with broader retrieval
        # scores cluster lower; 0.60 still signals a strong semantic match.
        high_conf_count = sum(1 for s in similarities if s >= 0.60)

        if high_conf_count >= 2 and avg_sim >= 0.55:
            return _GROUNDING_FULL
        elif len(similarities) >= 1 and avg_sim >= 0.40:
            return _GROUNDING_PARTIAL
        else:
            return _GROUNDING_NONE


def _build_grounding_prompt_rules(grounding_level: str, user_industry: str, kb_context: str) -> str:
    """Return prompt section text calibrated to the grounding level.

    GROUNDED  → allow specific claims, must cite KB excerpts.
    PARTIAL   → mix KB + general insight, soften any unsupported claims.
    UNGROUNDED→ insight-only mode, zero specific facts.
    """
    if grounding_level == _GROUNDING_FULL:
        return f"""KNOWLEDGE BASE EXCERPTS — YOUR ONLY SOURCE OF TRUTH:
{kb_context}

GROUNDING RULES (STRICT — GROUNDED MODE):
- Every factual claim, statistic, company name, product name, or specific example MUST come from the excerpts above.
- If you want to make a point that is NOT covered in the excerpts, phrase it as a general observation or opinion — never as a fact.
- Use phrases like "based on [topic from excerpt]" to root your points in real evidence.
- If an excerpt is off-domain (not about {user_industry}), IGNORE it completely.
- NEVER invent statistics, percentages, research studies, company names, or quotes."""

    elif grounding_level == _GROUNDING_PARTIAL:
        return f"""KNOWLEDGE BASE EXCERPTS (partial match — use these as your primary source):
{kb_context}

GROUNDING RULES (PARTIAL-CONFIDENCE MODE — IMPROVED):
- The KB excerpts above are your primary source for this topic. USE THEM ACTIVELY — reference specific points, mechanisms, patterns from the excerpts.
- For points covered by excerpts: make specific, concrete claims grounded in the excerpt content.
- For points NOT covered by excerpts: use INSIGHT-ONLY framing — patterns, trade-offs, principles, rhetorical questions. Do NOT present them as facts.
- Actively weave KB concepts into the post. Example: if an excerpt mentions "AMMs use constant product formula", use that specific mechanism in your post.
- Use phrases like: "As shown in [excerpt topic]", "The pattern here is", "This mechanism works because..." — ground where you can.
- Use hedging language for unsupported claims: "in my experience", "a common pattern", "many teams find that".
- NEVER invent statistics, percentages, research studies, company names, product names, or quotes.
- If an excerpt is off-domain (not about {user_industry}), IGNORE it completely."""

    else:  # UNGROUNDED
        return f"""(No relevant knowledge base content matched this topic.)

GROUNDING RULES (INSIGHT-ONLY MODE — NO KB AVAILABLE):
- You have NO factual evidence from the user's knowledge base for this topic.
- Write ONLY from general principles, widely-known industry patterns, and professional opinion.
- Frame every point as a perspective, observation, or question — NOT as a factual claim.
- Use language like: "I've seen teams struggle with…", "One pattern that keeps showing up…", "The question worth asking is…"
- Absolutely ZERO invented statistics, percentages, company names, product names, research studies, or quotes.
- Do NOT name specific companies, tools, or products unless they are universally known household names in {user_industry}.
- Keep every statement defensible as opinion or widely-accepted wisdom."""


def _verify_claims_against_kb(ai, post_text: str, kb_context: str, user_industry: str) -> dict:
    """Post-generation claim verifier. Checks each factual claim against KB excerpts.

    Returns dict with:
      - 'has_issues': bool
      - 'ungrounded_claims': list of strings (the problematic sentences)
      - 'rewrite_instructions': str (guidance for auto-rewrite)
    """
    if not kb_context or not post_text:
        return {'has_issues': False, 'ungrounded_claims': [], 'rewrite_instructions': ''}

    verify_prompt = _PromptBuilder.build_verification_prompt(post_text, kb_context)

    try:
        result = ai.generate(verify_prompt, max_tokens=300, temperature=0.0, task='evaluate')
        raw = (result.get('text') or '').strip()
        if raw.startswith('```'):
            raw = re.sub(r'^```[a-zA-Z]*\n?', '', raw)
            raw = re.sub(r'\n?```$', '', raw)
        match = re.search(r'\{.*\}', raw, flags=re.DOTALL)
        payload = json.loads(match.group(0) if match else raw)
        return {
            'has_issues': bool(payload.get('has_issues', False)),
            'ungrounded_claims': list(payload.get('ungrounded_claims', [])),
            'rewrite_instructions': str(payload.get('rewrite_instructions', '')),
        }
    except Exception as e:
        logger.warning('Claim verification failed: %s — skipping', e)
        return {'has_issues': False, 'ungrounded_claims': [], 'rewrite_instructions': ''}


def _rewrite_ungrounded_claims(ai, post_text: str, verification: dict,
                                user_industry: str, user_role: str, kb_context: str) -> str:
    """Auto-rewrite a post to soften or remove ungrounded claims.

    Takes the verification result and rewrites only the problematic parts,
    converting hard factual claims into defensible insight/opinion framing.
    """
    if not verification.get('has_issues') or not verification.get('ungrounded_claims'):
        return post_text

    rewrite_prompt = _PromptBuilder.build_rewrite_prompt(
        post_text=post_text,
        ungrounded_claims=verification['ungrounded_claims'],
        rewrite_instructions=verification.get('rewrite_instructions', ''),
        user_industry=user_industry,
        user_role=user_role,
        kb_context=kb_context,
    )

    try:
        result = ai.generate(rewrite_prompt, max_tokens=500, task='rewrite')
        rewritten = (result.get('text') or '').strip()
        if rewritten and len(rewritten) > 50:
            return rewritten
    except Exception as e:
        logger.warning('Claim rewrite failed: %s — keeping original', e)

    return post_text


# ── Chunk Quality Filter ──────────────────────────────────────────────────────

def _filter_low_quality_chunks(kb_hits: list, min_quality: float = 0.35) -> list:
    """Remove low-quality chunks (headers, footers, TOC, short fragments).

    Uses RAGStore.score_chunk_quality for scoring.  Chunks below min_quality
    are dropped.  Returns the filtered list (may be shorter than input).
    """
    from rag_system_pgvector import RAGStore
    if not kb_hits:
        return kb_hits
    filtered = []
    for hit in kb_hits:
        doc = hit.get('document') or ''
        quality = RAGStore.score_chunk_quality(doc)
        hit['_chunk_quality'] = quality
        if quality >= min_quality:
            filtered.append(hit)
        else:
            logger.debug('Dropped low-quality chunk (q=%.2f): %s…', quality, doc[:60])
    logger.info('Chunk quality filter: %d → %d chunks (min_quality=%.2f)',
                len(kb_hits), len(filtered), min_quality)
    return filtered


# ── Cross-encoder proxy: keyword-overlap reranking ────────────────────────────

def _rerank_with_keyword_boost(kb_hits: list, query_text: str,
                                 vector_weight: float = 0.75,
                                 keyword_weight: float = 0.25) -> list:
    """Lightweight cross-encoder proxy using keyword-overlap scoring.

    Reranks chunks by: vector_weight * original_similarity + keyword_weight * keyword_density.
    No external model needed — uses token overlap as a cheap relevance signal.
    """
    if not kb_hits or not query_text:
        return kb_hits

    from rag_system_pgvector import RAGStore
    query_keywords = RAGStore._extract_keywords(query_text)
    if not query_keywords:
        return kb_hits

    for hit in kb_hits:
        doc_lower = (hit.get('document') or '').lower()
        kw_hits = sum(1 for kw in query_keywords if kw in doc_lower)
        kw_density = kw_hits / len(query_keywords) if query_keywords else 0.0
        original_sim = float(hit.get('similarity', 0))
        boosted = vector_weight * original_sim + keyword_weight * kw_density
        hit['_rerank_score'] = round(boosted, 4)
        hit['similarity'] = round(boosted, 4)

    kb_hits.sort(key=lambda h: h.get('_rerank_score', 0), reverse=True)
    return kb_hits


# ── KB Gap Analysis ───────────────────────────────────────────────────────────

def _analyze_kb_coverage_gaps(topic: str, user_industry: str, user_role: str,
                               kb_hits: list, grounding_level: str) -> dict:
    """Analyse how well the KB covers the user's topic. Returns actionable suggestions.

    Return dict: {
      'coverage_pct': 0-100,
      'gaps': [...list of missing sub-topics...],
      'upload_suggestions': [...actionable file suggestions...],
    }
    """
    result = {'coverage_pct': 0, 'gaps': [], 'upload_suggestions': []}

    if not topic:
        return result

    # Simple heuristic: score coverage based on grounding level + hit quality
    if grounding_level == _GROUNDING_FULL:
        result['coverage_pct'] = 90
        return result
    elif grounding_level == _GROUNDING_PARTIAL:
        result['coverage_pct'] = 50
    else:
        result['coverage_pct'] = 10

    # Identify what the KB covers vs what the topic needs
    topic_lower = topic.lower()
    topic_keywords = set(re.findall(r'[a-zA-Z]{3,}', topic_lower))
    topic_keywords -= {'the', 'and', 'for', 'how', 'why', 'what', 'with', 'from'}

    covered_keywords = set()
    if kb_hits:
        for hit in kb_hits:
            doc_lower = (hit.get('document') or '').lower()
            for kw in topic_keywords:
                if kw in doc_lower:
                    covered_keywords.add(kw)

    missing_keywords = topic_keywords - covered_keywords
    if missing_keywords:
        result['gaps'] = sorted(missing_keywords)[:5]

    # Generate upload suggestions based on gaps
    suggestions = []
    if grounding_level == _GROUNDING_NONE:
        suggestions.append(f"Upload a document about \"{topic}\" to get factual, grounded posts.")
        if user_industry:
            suggestions.append(f"Add {user_industry} research reports, whitepapers, or case studies.")
    elif grounding_level == _GROUNDING_PARTIAL:
        if missing_keywords:
            suggestions.append(f"Your KB partially covers this topic. Add content about: {', '.join(sorted(missing_keywords)[:3])}.")
        suggestions.append("Upload more detailed documents to improve grounding confidence.")

    if user_role and grounding_level != _GROUNDING_FULL:
        suggestions.append(f"Consider adding {user_role}-perspective analyses or frameworks for better role-specific grounding.")

    result['upload_suggestions'] = suggestions[:3]
    return result


# ── Dynamic Instruction Packs from KB ─────────────────────────────────────────

def _extract_dynamic_kb_context(kb_hits: list, user_industry: str, user_role: str) -> str:
    """Extract vocabulary, themes, and domain-specific language from KB chunks.

    Returns a short instruction supplement that adapts the prompt to the user's
    own language/terminology, making the output feel more on-brand.
    """
    if not kb_hits:
        return ''

    # Collect unique terms that appear frequently across KB chunks
    from collections import Counter
    from rag_system_pgvector import RAGStore

    all_text = ' '.join((h.get('document') or '') for h in kb_hits[:5])
    keywords = RAGStore._extract_keywords(all_text, max_keywords=40)

    # Count high-value domain terms (3+ chars, not generic)
    industry_lower = (user_industry or '').lower()
    role_lower = (user_role or '').lower()
    generic_words = {
        'the', 'and', 'for', 'that', 'this', 'with', 'from', 'have', 'been',
        'will', 'are', 'was', 'can', 'but', 'not', 'our', 'your', 'their',
        'more', 'than', 'also', 'about', 'into', 'most', 'other', 'some',
        'just', 'like', 'make', 'made', 'when', 'what', 'how', 'which',
        'each', 'such', 'very', 'use', 'used', 'using', 'new', 'way',
    }

    word_counts = Counter()
    tokens = re.findall(r'[a-zA-Z]{3,}', all_text.lower())
    for t in tokens:
        if t not in generic_words and len(t) >= 4:
            word_counts[t] += 1

    # Extract domain-specific terms (appear 2+ times in KB but aren't stopwords)
    domain_terms = [term for term, count in word_counts.most_common(20) if count >= 2]

    if not domain_terms:
        return ''

    # Extract any named entities or proper nouns from the chunks (capitalised words)
    proper_nouns = set()
    for hit in kb_hits[:5]:
        doc = hit.get('document') or ''
        # Find capitalised multi-word phrases
        for match in re.findall(r'[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+', doc):
            if len(match) > 5:
                proper_nouns.add(match.strip())
    # Limit
    proper_nouns = sorted(proper_nouns)[:8]

    parts = []
    parts.append("KB VOCABULARY SUPPLEMENT (use these terms naturally when relevant):")
    parts.append(f"  Domain terms: {', '.join(domain_terms[:12])}")
    if proper_nouns:
        parts.append(f"  Named entities from your KB: {', '.join(proper_nouns[:6])}")
    parts.append(f"  These come from your uploaded documents — use them to make the post feel on-brand.")

    return '\n'.join(parts)


# ── Sentence-Level Grounding Scoring ──────────────────────────────────────────

def _score_sentences_grounding(post_text: str, kb_hits: list, rag_store=None) -> list:
    """Score each sentence in the post for KB grounding.

    Uses embedding similarity between each sentence and the KB chunks.
    Returns list of dicts: [{'sentence': str, 'score': float, 'level': str}, ...]

    Levels: 'grounded' (≥0.75), 'partial' (≥0.60), 'ungrounded' (<0.60)
    """
    if not post_text or not kb_hits:
        return []

    # Split post into sentences
    sentences = re.split(r'(?<=[.!?])\s+', post_text.strip())
    sentences = [s.strip() for s in sentences if len(s.strip()) > 15]

    if not sentences:
        return []

    # Get KB chunk texts
    kb_texts = [(h.get('document') or '') for h in kb_hits if h.get('document')]
    if not kb_texts:
        return []

    # If we have a rag_store with embedding capability, use semantic scoring
    if rag_store:
        try:
            import numpy as np
            sentence_embeddings = rag_store._encode_texts(sentences)
            kb_embeddings = rag_store._encode_texts(kb_texts[:5])  # Top 5 chunks

            results = []
            for i, sent in enumerate(sentences):
                sent_emb = sentence_embeddings[i]
                # Compute max similarity against all KB chunks
                max_sim = 0.0
                for kb_emb in kb_embeddings:
                    sim = float(np.dot(sent_emb, kb_emb) /
                                (np.linalg.norm(sent_emb) * np.linalg.norm(kb_emb) + 1e-8))
                    max_sim = max(max_sim, sim)

                level = 'grounded' if max_sim >= 0.75 else ('partial' if max_sim >= 0.60 else 'ungrounded')
                results.append({
                    'sentence': sent[:200],
                    'score': round(max_sim, 3),
                    'level': level,
                })
            return results
        except Exception as e:
            logger.warning('Sentence-level grounding scoring failed: %s', e)

    # Fallback: keyword overlap scoring
    kb_combined = ' '.join(kb_texts).lower()
    results = []
    for sent in sentences:
        words = set(re.findall(r'[a-zA-Z]{4,}', sent.lower()))
        if not words:
            results.append({'sentence': sent[:200], 'score': 0.0, 'level': 'ungrounded'})
            continue
        overlap = sum(1 for w in words if w in kb_combined) / len(words)
        level = 'grounded' if overlap >= 0.6 else ('partial' if overlap >= 0.35 else 'ungrounded')
        results.append({'sentence': sent[:200], 'score': round(overlap, 3), 'level': level})

    return results


# ── Author-Side Source Traceability ───────────────────────────────────────────

def _build_source_traceability(kb_hits: list, post_text: str = '') -> list:
    """Build source traceability map for the author's dashboard.

    Returns a list of source objects that the author can inspect to verify
    where content came from.  NOT shown to LinkedIn readers — author-only.

    Returns: [{
        'file': str,
        'chunk_preview': str,
        'similarity': float,
        'chunk_quality': float,
        'file_id': str,
    }, ...]
    """
    if not kb_hits:
        return []

    sources = []
    seen_files = set()
    for hit in kb_hits[:6]:
        meta = hit.get('metadata') or {}
        file_name = os.path.basename(meta.get('source', 'Unknown'))
        file_id = hit.get('file_id', '')
        chunk_text = (hit.get('document') or '').strip()
        sim = round(float(hit.get('similarity', 0)), 3)
        quality = round(float(hit.get('_chunk_quality', 0.5)), 3)

        source_key = f"{file_id}:{chunk_text[:50]}"
        if source_key in seen_files:
            continue
        seen_files.add(source_key)

        sources.append({
            'file': file_name,
            'chunk_preview': chunk_text[:300] + ('…' if len(chunk_text) > 300 else ''),
            'similarity': sim,
            'chunk_quality': quality,
            'file_id': file_id,
        })

    return sources


# ── Grounding Telemetry Logging ───────────────────────────────────────────────

def _log_grounding_telemetry(user_id: str, generation_data: dict) -> None:
    """Log grounding metrics for this generation to system_logs.

    Tracks: grounding level, avg similarity, hit count, gap analysis,
    rewrite status, and strict mode usage.  Used for analytics.
    """
    try:
        from database.db_helper import get_db
        db = get_db()
        db.log('info', 'grounding_telemetry', user_id=user_id, metadata={
            'grounding_level': generation_data.get('grounding_level', 'unknown'),
            'avg_similarity': generation_data.get('avg_similarity', 0),
            'kb_hits_count': generation_data.get('kb_hits_count', 0),
            'coverage_pct': generation_data.get('coverage_pct', 0),
            'strict_mode': generation_data.get('strict_mode', False),
            'rewrite_applied': generation_data.get('rewrite_applied', False),
            'kb_mode': generation_data.get('kb_mode', ''),
            'topic': (generation_data.get('topic', '') or '')[:100],
            'industry': generation_data.get('industry', ''),
            'role': generation_data.get('role', ''),
        })
    except Exception as e:
        logger.debug('Grounding telemetry log failed (non-critical): %s', e)


@app.route('/api/generate-preview', methods=['POST'])
@limiter.limit("8 per minute")        # per user (not per IP)
@limiter.limit("30 per hour")          # hourly guard against bots
@require_auth
def generate_preview():
    """Generate a preview post"""
    try:
        from ai_provider import AIProvider
        import random
        import config as cfg
        from rag_system_pgvector import RAGStore
        
        logger.info("Generate preview request received")
        
        req_data = request.get_json(silent=True) or {}

        user_id = g.user_id  # already validated by @require_auth

        can_generate, quota_meta = _check_generation_guardrail(user_id)
        if not can_generate:
            return jsonify({
                'success': False,
                'quota_exceeded': True,
                'quota_info': quota_meta,
                **quota_meta
            }), 403
        effective_plan = quota_meta.get('plan') or _get_effective_plan(user_id)
        is_free_plan = effective_plan == 'free'

        if is_free_plan:
            req_data['kb_mode'] = 'use_kb'
            req_data['workspace_id'] = ''
            req_data['specific_file_ids'] = []
            req_data['word_count_mode'] = 'custom_range'
            req_data['min_words'] = 120
            req_data['max_words'] = 220
            req_data.pop('topic', None)
            req_data.pop('topics', None)

        config_obj = load_config(user_id)
        ai = _build_platform_ai_provider()
        user_topic = (req_data.get('topic') or '').strip()
        user_industry = _normalize_taxonomy_label(req_data.get('industry') or config_obj.get('CONTENT_INDUSTRY', ''), _INDUSTRY_LABELS)
        user_role = _normalize_taxonomy_label(req_data.get('role') or config_obj.get('USER_ROLE', ''), _ROLE_LABELS)
        post_tone = _normalize_tone_value(req_data.get('tone') or config_obj.get('TONE', 'professional') or 'professional')

        raw_goal_value = str(
            req_data.get('goal_preset')
            or req_data.get('post_goal')
            or req_data.get('business_goal')
            or ''
        ).strip()
        if not raw_goal_value:
            return jsonify({
                'success': False,
                'message': 'Post Goal is required. Please select a goal before generating.'
            }), 400

        goal_key, business_goal = _normalize_goal(raw_goal_value)
        if goal_key == 'general_engagement':
            return jsonify({
                'success': False,
                'message': 'Invalid Post Goal. Please choose one of the available goal presets.'
            }), 400

        post_goal = business_goal
        audience_type = str(
            req_data.get('audience_type')
            or req_data.get('audienceType')
            or 'individual'
        ).strip().lower() or 'individual'
        target_audience = str(
            req_data.get('target_audience')
            or req_data.get('targetAudience')
            or config_obj.get('AUDIENCE_KEYWORDS', '')
            or ''
        ).strip()
        hashtag_count = clamp_int(req_data.get('hashtags', config_obj.get('HASHTAG_COUNT', 3)), 0, 10, 3)
        emoji_level = (req_data.get('emojis') or config_obj.get('EMOJI_USAGE', 'moderate') or 'moderate').strip().lower()
        topics = parse_content_topics(req_data, config_obj)
        style_clone_mode = _normalize_style_clone_mode(req_data.get('style_clone_mode') or 'hybrid')

        kb_mode_raw = (req_data.get('kb_mode') or 'use_kb').strip().lower()
        if kb_mode_raw in {'no_kb', 'dont_use_kb', 'off'}:
            kb_mode = 'no_kb'
        elif kb_mode_raw in {'specific_files', 'specific', 'use_specific_files'}:
            kb_mode = 'specific_files'
        else:
            kb_mode = 'use_kb'

        # ── Strict grounding toggle ───────────────────────────────────────────
        strict_grounding = bool(req_data.get('strict_grounding', False))

        workspace_id = (req_data.get('workspace_id') or '').strip()
        raw_specific_file_ids = req_data.get('specific_file_ids') or []
        if not isinstance(raw_specific_file_ids, list):
            raw_specific_file_ids = []
        specific_file_ids = [str(file_id).strip() for file_id in raw_specific_file_ids if str(file_id).strip()]

        min_words = clamp_int(req_data.get('min_words', config_obj.get('MIN_POST_WORDS', 120)), 40, 600, 120)
        max_words = clamp_int(req_data.get('max_words', config_obj.get('MAX_POST_WORDS', 220)), 40, 600, 220)
        if max_words < min_words:
            max_words = min_words

        word_count_mode = (req_data.get('word_count_mode') or config_obj.get('POST_LENGTH_MODE', 'custom_range') or 'custom_range').strip().lower()
        if word_count_mode not in {'custom_range', 'ai_random'}:
            word_count_mode = 'custom_range'
        
        neutral_themes = [
            f"{user_industry or 'technology'} trends and practical insights",
            f"{user_role or 'leadership'} execution strategies",
            "team productivity and process improvement",
            "product, engineering, and business alignment",
            "scaling systems and operational excellence"
        ]
        if user_topic:
            theme = user_topic
        elif topics:
            theme = random.choice(topics)
        elif user_industry and user_role:
            theme = f"{user_industry} insights for {user_role} professionals"
        elif user_industry:
            theme = f"Practical {user_industry} insights"
        elif user_role:
            theme = f"{user_role} leadership and execution playbook"
        elif kb_mode == 'no_kb':
            theme = random.choice(neutral_themes)
        else:
            theme = random.choice(neutral_themes)
        
        fmt = random.choice(POST_FORMATS) if POST_FORMATS else 'article'

        if user_industry or user_role or topics:
            services = f"Professional insights for {user_industry or 'business and technology'} audiences, with focus on {user_role or 'strategy and execution'}."
        else:
            services = f"Professional insights for {user_industry or 'business and technology'} audiences, with focus on {user_role or 'leadership and execution'}."

        forbidden_terms = _forbidden_terms_for_context(
            user_industry, user_role, user_topic, topics, post_goal
        )
        selected_domain = user_industry or 'the selected industry'
        domain_guardrail = (
            f"HARD DOMAIN BOUNDARY: Write strictly for {selected_domain}. "
            "Do not mention unrelated industries unless explicitly requested."
        )
        if forbidden_terms:
            domain_guardrail += (
                " Specifically do not mention: " + ', '.join(forbidden_terms[:10]) + "."
            )

        # ── Style Clone injection ─────────────────────────────────────────────
        use_style_clone = bool(req_data.get('use_style_clone', False))
        style_instruction = ""
        style_clone_active = False
        if use_style_clone and style_clone_mode != 'off':
            try:
                sc_blob = (_ensure_user_feature_blob(user_id) or {}).get('style_clone') or {}
                if sc_blob.get('enabled') and sc_blob.get('samples'):
                    traits = sc_blob.get('traits') or {}
                    samples_preview = sc_blob['samples'][:3]

                    # Derive concrete format directives from traits
                    _emoji_from_trait = {
                        'none': 'ZERO emojis — absolutely none, not even at the end.',
                        'rare': 'At most 1 emoji, only where it genuinely adds meaning.',
                        'minimal': 'At most 1 emoji, only where it genuinely adds meaning.',
                        'moderate': '2–3 emojis maximum.',
                        'frequent': 'Emojis can appear throughout, but never more than 1 per sentence.',
                    }
                    trait_emoji_rule = _emoji_from_trait.get(
                        (traits.get('emoji_usage') or '').lower().split('/')[0].strip(),
                        None
                    )

                    # Paragraph/list format directive
                    para_style = (traits.get('paragraph_style') or '').lower()
                    if 'list' in para_style or 'bullet' in para_style:
                        list_rule = (
                            "FORMAT: Use single-line breaks between short statements or list-style lines. "
                            "Dashes or line breaks as separators are ALLOWED — this person writes in lists."
                        )
                    elif 'single' in para_style or 'one-liner' in para_style:
                        list_rule = (
                            "FORMAT: Write in punchy single-line statements separated by line breaks. "
                            "Short paragraphs, maximum 1–2 sentences each."
                        )
                    else:
                        list_rule = "FORMAT: Short paragraphs. Maximum 2–3 sentences each. No long blocks of text."

                    # Opening / closing directives
                    opener = traits.get('opening_style') or 'direct statement'
                    closer = traits.get('closing_style') or 'reflective thought'
                    vocab = traits.get('vocabulary_level') or 'mixed'
                    structure_desc = traits.get('post_structure') or ''
                    sig_phrases = traits.get('signature_phrases') or []

                    sig_block = ""
                    if sig_phrases:
                        sig_block = (
                            f"\n- SIGNATURE STYLE MARKERS (do NOT copy these, but capture the same energy): "
                            + ", ".join(f'"{p}"' for p in sig_phrases[:4])
                        )

                    style_mode_heading = "STRICT MODE — STYLE CLONE DOMINATES VOICE/FORMAT" if style_clone_mode == 'strict' else "HYBRID MODE — BLEND STYLE CLONE WITH ROLE/GOAL"
                    style_instruction = f"""
╔══════════════════════════════════════════════════════════════════╗
║  STYLE CLONE — {style_mode_heading}       ║
╚══════════════════════════════════════════════════════════════════╝
Use the fingerprint below to shape writing style while honoring role, audience,
domain, and post-goal constraints.

VOICE FINGERPRINT:
- Overall voice: {traits.get('style_summary', 'direct and analytical')}
- Sentence length: {traits.get('avg_sentence_length', 'short')} — enforce this strictly
- Tone: {traits.get('tone', 'direct and confident')}
- Vocabulary level: {vocab}
- Opening style: {opener} — the first line MUST open this way
- Closing style: {closer} — the last line MUST close this way
- Paragraph/structure: {traits.get('paragraph_style', 'short blocks')}
- Structural pattern: {structure_desc}{sig_block}

{list_rule}

EMOJI RULE (HARD): {trait_emoji_rule or 'Match the emoji level shown in the fingerprint.'}

REFERENCE POSTS — study the rhythm, word choice, sentence weight (DO NOT copy content):
{chr(10).join(f'--- REF {i+1} ---{chr(10)}{s[:500]}' for i, s in enumerate(samples_preview))}
╔══════════════════════════════════════════════════════════════════╗
║  END STYLE CLONE — the post must sound like these reference posts ║
╚══════════════════════════════════════════════════════════════════╝"""

                    style_clone_active = True
                    if trait_emoji_rule:
                        emoji_level = (traits.get('emoji_usage') or 'moderate').lower().split('/')[0].strip()

            except Exception as sc_err:
                logger.warning('Style clone fetch failed: %s', sc_err)

        kb_used = False
        emoji_rule_map = {
            'none':     'Do not use emojis — zero, not even at the end.',
            'rare':     'At most 1 emoji, only where it genuinely adds meaning.',
            'minimal':  'Use at most 1–2 relevant emojis.',
            'moderate': 'Use 2–4 relevant emojis for readability.',
            'frequent': 'Use up to 5–7 relevant emojis, naturally placed.',
            'high':     'Use up to 5–7 relevant emojis without overstuffing.',
        }
        emoji_rule = emoji_rule_map.get((emoji_level or '').lower(), emoji_rule_map['moderate'])

        topic_hint = ', '.join(topics) if topics else 'industry trends and practical insights'
        target_audience_hint = f"Professionals in {user_industry or 'this industry'}, specifically those in or working with {user_role or 'leadership roles'}."

        if word_count_mode == 'ai_random':
            random_target = random.randint(110, 230)
            word_rule = f"Choose an optimal LinkedIn length naturally, around {random_target} words."
        else:
            word_rule = f"Keep the post between {min_words} and {max_words} words."

        kb_used = False
        kb_no_match = False
        kb_state = 'disabled'   # disabled | no_files | not_built | no_match | error | ok
        kb_sources = []
        kb_context = ""
        kb_selected_file_count = 0
        kb_selected_file_ids = []
        kb_hits = []
        rag = None  # Initialise so it's available for sentence grounding
        try:
            # Get current user's ID (authenticated or test user)
            user_id = get_current_user_id()
            rag = RAGStore(user_id=user_id)
            if is_free_plan:
                free_user_files = rag.db.list_kb_files(user_id)
                if not free_user_files:
                    return jsonify({
                        'success': False,
                        'message': 'Free plan requires 1 KB file upload before generation. Upload a file and try again.'
                    }), 403
                if not rag.is_built():
                    return jsonify({
                        'success': False,
                        'message': 'Knowledge base is still training. Please wait a moment and try again.'
                    }), 403

            if kb_mode == 'no_kb':
                kb_state = 'disabled'
            elif not rag.is_built():
                kb_state = 'not_built'
                kb_no_match = True
            else:
                user_files = rag.db.list_kb_files(user_id)
                user_file_ids = [str(row.get('id')) for row in user_files if row.get('id')]

                if not user_file_ids:
                    kb_state = 'no_files'
                    kb_no_match = True
                else:
                    selected_file_ids = list(user_file_ids)

                    if kb_mode == 'specific_files':
                        selected_file_ids = [fid for fid in specific_file_ids if fid in user_file_ids]
                    elif workspace_id:
                        blob = _ensure_user_feature_blob(user_id)
                        ws = _get_workspace(blob, workspace_id)
                        if ws:
                            if ws.get('use_all_files'):
                                selected_file_ids = list(user_file_ids)
                            else:
                                ws_file_ids = [str(fid) for fid in (ws.get('file_ids') or [])]
                                selected_file_ids = [fid for fid in ws_file_ids if fid in user_file_ids]

                    kb_selected_file_ids = selected_file_ids
                    kb_selected_file_count = len(selected_file_ids)

                    if not selected_file_ids:
                        kb_state = 'no_files'
                        kb_no_match = True
                    else:
                        filtered = len(selected_file_ids) < len(user_file_ids)
                        file_id_arg = selected_file_ids if filtered else None

                        # ── Multi-query hybrid retrieval (production grounding) ──
                        retrieval_queries = _expand_retrieval_queries(
                            theme or topic_hint, user_industry, user_role, goal_key
                        )

                        # Phase 1: hybrid search (vector + keyword) per query
                        # threshold=0.30: low enough to retrieve semantically related chunks even when
                        # topic phrasing differs from the stored KB text (e.g. "NovaPay checkout"
                        # vs "payment failure reduction"). Reranking + quality filter clean up noise.
                        all_hybrid_hits = {}
                        for rq in retrieval_queries:
                            hits = rag.hybrid_search(
                                rq, k=6,
                                match_threshold=0.30,
                                file_ids=file_id_arg,
                                vector_weight=0.75,
                                keyword_weight=0.25,
                            )
                            for hit in hits:
                                cid = hit.get('id') or hit.get('document', '')[:80]
                                existing = all_hybrid_hits.get(cid)
                                if existing is None or float(hit.get('similarity', 0)) > float(existing.get('similarity', 0)):
                                    all_hybrid_hits[cid] = hit
                        kb_hits = sorted(all_hybrid_hits.values(),
                                         key=lambda h: float(h.get('similarity', 0)), reverse=True)
                        
                        # LOG: Show KB retrieval details for debugging
                        logger.info('KB retrieval: searched %d queries, found %d hybrid hits before filtering',
                                    len(retrieval_queries), len(kb_hits))
                        if kb_hits:
                            sims = [float(h.get('similarity', 0)) for h in kb_hits[:5]]
                            logger.info('KB hit similarities (top 5): %s', 
                                       [f'{s:.4f}' for s in sims])

                        # Phase 2: chunk quality filter
                        kb_hits = _filter_low_quality_chunks(kb_hits, min_quality=0.35)

                        # Phase 3: keyword-overlap reranking
                        kb_hits = _rerank_with_keyword_boost(
                            kb_hits, theme or topic_hint,
                            vector_weight=0.75, keyword_weight=0.25
                        )
                        
                        # DIAGNOSTIC: Check if vector similarity is suspiciously low
                        # If all scores are < 0.30, it suggests embedding/vector issues
                        if kb_hits:
                            final_sims = [float(h.get('similarity', 0)) for h in kb_hits]
                            max_sim = max(final_sims) if final_sims else 0
                            if max_sim < 0.30 and kb_mode != 'no_kb':
                                logger.warning(
                                    'KB similarity scores suspiciously low: max=%.4f (should be 0.50+). '
                                    'This may indicate: (1) vector embeddings not stored correctly, '
                                    '(2) embedding model not initialized on production, or (3) KB not indexed. '
                                    'Falling back to keyword-only matching. User: %s',
                                    max_sim, user_id
                                )
                                # Fallback: Retry with keyword search only, higher k value
                                logger.info('Attempting keyword-only fallback search (keyword_weight=1.0)')
                                fallback_hits = {}
                                for rq in retrieval_queries:
                                    kw_hits = rag.keyword_search(rq, k=10, file_ids=file_id_arg)
                                    for hit in kw_hits:
                                        cid = hit.get('id') or hit.get('document', '')[:80]
                                        existing = fallback_hits.get(cid)
                                        if existing is None or float(hit.get('similarity', 0)) > float(existing.get('similarity', 0)):
                                            fallback_hits[cid] = hit
                                kb_hits_fallback = sorted(fallback_hits.values(),
                                                         key=lambda h: float(h.get('similarity', 0)), reverse=True)
                                if kb_hits_fallback and max([float(h.get('similarity', 0)) for h in kb_hits_fallback]) > 0.40:
                                    logger.info('Keyword-only fallback successful: %d hits with better scores', len(kb_hits_fallback))
                                    kb_hits = kb_hits_fallback[:5]  # Use top 5 from fallback
                        
                        # LOG: Show final KB state
                        if kb_hits:
                            final_sims = [float(h.get('similarity', 0)) for h in kb_hits[:5]]
                            logger.info('KB final state: %d chunks after filtering, final similarities: %s',
                                       len(kb_hits), [f'{s:.4f}' for s in final_sims])

                        if kb_hits:
                            kb_used = True
                            kb_state = 'ok'
                            snippets = []
                            # IMPROVED: Include up to 5 KB hits (was 3) with more context (1200 chars instead of 900)
                            # This ensures richer context for complex topics like crypto/AMM mechanics
                            for idx, hit in enumerate(kb_hits[:5], start=1):
                                src = os.path.basename((hit.get('metadata') or {}).get('source', 'knowledge_base'))
                                kb_sources.append(src)
                                doc_text = (hit.get('document') or '').strip()
                                sim = hit.get('similarity', 0.0)
                                if doc_text:
                                    snippets.append(f"[{idx}] Source: {src} (relevance: {sim:.2f})\n{doc_text[:1200]}")
                            kb_context = "\n\n".join(snippets)
                        else:
                            kb_state = 'no_match'
                            kb_no_match = True

        except Exception as kb_error:
            logger.warning("KB retrieval unavailable, falling back to LLM context: %s", kb_error)
            kb_state = 'error'
            kb_no_match = True  # KB was requested but failed — tell the user

        kb_avg_similarity = 0.0
        if kb_hits:
            similarities = [float(hit.get('similarity') or 0.0) for hit in kb_hits if hit is not None]
            if similarities:
                kb_avg_similarity = sum(similarities) / len(similarities)
        kb_low_confidence = bool(kb_used and kb_avg_similarity < 0.76)

        # ── Grounding level classification ────────────────────────────────────
        grounding_level = _classify_grounding_level(kb_hits, kb_used, kb_mode)
        logger.info('Grounding level: %s (avg_sim=%.3f, hits=%d, kb_mode=%s, kb_used=%s)',
                     grounding_level, kb_avg_similarity, len(kb_hits), kb_mode, kb_used)
        
        # LOG: Show grounding decision details
        if kb_hits:
            sims = [float(h.get('similarity', 0)) for h in kb_hits]
            logger.debug('KB hits details for grounding: %s hits with avg_sim=%.4f, min=%.4f, max=%.4f',
                        len(sims), kb_avg_similarity, min(sims) if sims else 0, max(sims) if sims else 0)

        # ── Strict grounding gate ─────────────────────────────────────────────
        # When strict mode is ON but no KB match is found, fall through to Insight
        # Mode instead of blocking.  The response flags the downgrade so the UI can
        # inform the user why the post was generated without KB grounding.
        _strict_grounding_downgraded = False
        if strict_grounding and kb_mode != 'no_kb' and grounding_level == _GROUNDING_NONE:
            _strict_grounding_downgraded = True
            kb_no_match = True
            kb_state = 'no_match'
            logger.info(
                'Strict grounding downgraded to Insight Mode — no KB match for topic "%s"',
                theme or topic_hint,
            )

        # ── Dynamic instruction pack supplement from KB ───────────────────────
        dynamic_kb_supplement = ''
        if kb_used and kb_hits:
            dynamic_kb_supplement = _extract_dynamic_kb_context(kb_hits, user_industry, user_role)

        # ── Tone / Goal / Style rules (via PromptBuilder) ────────────────────
        tone_voice, tone_template = _PromptBuilder.resolve_tone(post_tone)
        goal_structure = _PromptBuilder.resolve_goal_structure(goal_key)

        # ── Instruction Pack (auto-loaded for industry × role × goal) ─────────────
        instruction_pack_text = _build_instruction_pack_text(user_industry, user_role, goal_key, config_obj=config_obj)

        # ── Merge dynamic KB vocabulary supplement ────────────────────────────────
        if dynamic_kb_supplement:
            instruction_pack_text = (instruction_pack_text or '') + '\n\n' + dynamic_kb_supplement

        # ── Style Clone trait overrides (must run AFTER tone_voice is set) ────────
        sc_trait_overrides = {}
        if use_style_clone:
            try:
                sc_blob = (_ensure_user_feature_blob(user_id) or {}).get('style_clone') or {}
                if sc_blob.get('enabled') and sc_blob.get('traits'):
                    sc_trait_overrides = sc_blob['traits']
            except Exception:
                pass

        style_clone_strict = style_clone_active and style_clone_mode == 'strict'
        if style_clone_active and sc_trait_overrides:
            clone_tone = str(sc_trait_overrides.get('tone') or '').strip()
            if clone_tone:
                if style_clone_strict:
                    tone_voice = clone_tone
                else:
                    tone_voice = f"{tone_voice} Blend in this personal writing cadence: {clone_tone}."

        # ── Style clone rules (via PromptBuilder) ─────────────────────────────
        _sc_rules = _PromptBuilder.resolve_style_clone_rules(style_clone_active, style_clone_strict)
        voice_rule_text = _sc_rules['voice']
        structure_rule_text = _sc_rules['structure']
        format_rule_text = _sc_rules['format']
        style_clone_compliance_rule = _sc_rules['compliance']

        # ── Build KB section (grounding-level-aware) ─────────────────────────────
        kb_section = _build_grounding_prompt_rules(grounding_level, user_industry, kb_context)

        prompt = _PromptBuilder.build_generation_prompt(
            user_industry=user_industry,
            user_role=user_role,
            theme=theme,
            services=services,
            target_audience_hint=target_audience_hint,
            topic_hint=topic_hint,
            business_goal=business_goal,
            tone_voice=tone_voice,
            tone_template=tone_template,
            goal_structure=goal_structure,
            instruction_pack_text=instruction_pack_text,
            style_instruction=style_instruction,
            kb_section=kb_section,
            domain_guardrail=domain_guardrail,
            word_rule=word_rule,
            emoji_rule=emoji_rule,
            hashtag_count=hashtag_count,
            fmt=fmt,
            grounding_level=grounding_level,
            voice_rule_text=voice_rule_text,
            structure_rule_text=structure_rule_text,
            format_rule_text=format_rule_text,
            style_clone_compliance_rule=style_clone_compliance_rule,
        )

        logger.info(f"Generating preview with prompt: {prompt[:100]}...")
        
        import time

        # ── Request timeout budget (max wall-clock time for entire pipeline) ──
        _REQUEST_BUDGET_SEC = float(os.getenv('GENERATION_TIMEOUT_SEC', '90'))
        _request_start = time.time()

        def _budget_remaining() -> float:
            return max(0.0, _REQUEST_BUDGET_SEC - (time.time() - _request_start))

        def _has_budget(min_sec: float = 10.0) -> bool:
            """Return True if at least min_sec seconds remain in the request budget."""
            return _budget_remaining() > min_sec

        # ── Token usage accumulator for this request ─────────────────────────
        _token_totals = {'prompt': 0, 'completion': 0, 'total': 0, 'calls': 0}

        def _track_usage(result: dict) -> None:
            """Accumulate token usage from an AI API result dict."""
            usage = result.get('usage') if isinstance(result, dict) else None
            if usage:
                _token_totals['prompt'] += int(usage.get('prompt_tokens') or 0)
                _token_totals['completion'] += int(usage.get('completion_tokens') or 0)
                _token_totals['total'] += int(usage.get('total_tokens') or 0)
                _token_totals['calls'] += 1

        def _generate_once(generation_prompt: str) -> str:
            start_time = time.time()
            try:
                result = ai.generate(generation_prompt, max_tokens=800, task='generate')
                _track_usage(result)
            except Exception as e:
                logger.error(f"AI generation failed after {time.time() - start_time:.2f}s: {e}")
                raise

            if not result or 'text' not in result:
                logger.error(f"Invalid AI response: {result}")
                raise ValueError('AI returned invalid response')

            text = (result.get('text') or '').strip()
            if not text:
                raise ValueError('Generated content is empty')

            # Validate minimum output quality — reject truncated/stub outputs
            wc = words_count(text)
            if wc < 40:
                logger.warning('AI output too short (%d words), retrying once with explicit length instruction', wc)
                length_nudge = generation_prompt + '\n\nIMPORTANT: Your previous output was too short. Write a COMPLETE post of at least 120 words.'
                try:
                    retry_result = ai.generate(length_nudge, max_tokens=800, task='generate')
                    _track_usage(retry_result)
                    retry_text = (retry_result.get('text') or '').strip()
                    if retry_text and words_count(retry_text) > wc:
                        return retry_text
                except Exception:
                    logger.debug('Length-nudge retry failed, using original short output')
            return text

        def _strip_llm_preamble(text: str) -> str:
            """Remove common LLM preambles that shouldn't be in the final post.
            
            Examples:
            - "Here is the LinkedIn post..."
            - "Here is the rewritten LinkedIn post..."
            - "Here's a post about..."
            """
            lines = text.split('\n')
            result_lines = []
            skip_mode = False
            
            for line in lines:
                lower_line = line.lower().strip()
                
                # Skip lines that look like preamble
                if any(phrase in lower_line for phrase in [
                    'here is the',
                    "here's the",
                    'here\'s the',
                    'here is a',
                    "here's a",
                    'here\'s a',
                    'rewritten',
                    'optimized for',
                    'linkedin post',
                    'revised post',
                    'draft'
                ]):
                    skip_mode = True
                    continue
                
                # Skip separator lines like --- or ===
                if lower_line and all(c in '-=*' for c in lower_line):
                    if skip_mode:
                        skip_mode = False
                    continue
                
                # If we're in skip mode but hit a blank line followed by content, switch modes
                if skip_mode and not lower_line:
                    skip_mode = False
                    continue
                
                if not skip_mode or lower_line:  # Add line if not skipping or if it has content
                    result_lines.append(line)
            
            # Clean up result
            result = '\n'.join(result_lines).strip()
            
            # Remove any remaining leading/trailing dashes or equals
            while result and result[0] in '-=*':
                result = result[1:].lstrip()
            while result and result[-1] in '-=*':
                result = result[:-1].rstrip()
            
            return result

        def _post_process_generated(raw_text: str):
            # IMPROVED: Strip LLM preambles before processing
            raw_text = _strip_llm_preamble(raw_text)
            
            generated_tags_local = normalize_hashtags(HASHTAG_RE.findall(raw_text))
            body_local = enforce_linkedin_quality(
                remove_hashtags_from_body(raw_text),
                user_industry,
                user_role,
                theme,
                target_audience_hint,
                emoji_level,
            )

            if word_count_mode == 'custom_range':
                word_total = words_count(body_local)
                if word_total < min_words or word_total > max_words:
                    rewrite_prompt = f"""Rewrite the following LinkedIn post to be between {min_words} and {max_words} words.
Preserve meaning, tone, and practical value.
Do not include hashtags in the body.
\nPost:\n{body_local}\n"""
                    try:
                        rewrite = ai.generate(rewrite_prompt, max_tokens=800, task='rewrite')
                        rewritten_text = (rewrite.get('text') or '').strip()
                        if rewritten_text:
                            body_local = enforce_linkedin_quality(
                                remove_hashtags_from_body(rewritten_text),
                                user_industry,
                                user_role,
                                theme,
                                target_audience_hint,
                                emoji_level,
                            )
                    except Exception as rewrite_error:
                        logger.warning("Word-range rewrite fallback failed: %s", rewrite_error)

                body_local = enforce_word_ceiling(body_local, max_words)

            forbidden_hits_local = _find_forbidden_terms(body_local, forbidden_terms)
            if forbidden_hits_local:
                rewrite_prompt = f"""Rewrite the LinkedIn post below while keeping the same intent, tone, and structure.
Hard rule: remove any references to these forbidden terms: {', '.join(forbidden_hits_local)}.
Keep the post focused strictly on: {selected_domain} and role: {user_role or 'professional'}.
Do not add markdown symbols (no ** or bullets) and keep readable short paragraphs.

Post:
{body_local}
"""
                try:
                    rewrite = ai.generate(rewrite_prompt, max_tokens=800, task='rewrite')
                    rewritten_text = (rewrite.get('text') or '').strip()
                    if rewritten_text:
                        body_local = enforce_linkedin_quality(
                            remove_hashtags_from_body(rewritten_text),
                            user_industry,
                            user_role,
                            theme,
                            target_audience_hint,
                            emoji_level,
                        )
                except Exception as rewrite_error:
                    logger.warning("Domain guardrail rewrite failed: %s", rewrite_error)

            return body_local, generated_tags_local

        try:
            first_draft_raw = _generate_once(prompt)
        except Exception as first_error:
            return _safe_api_error('AI generation failed. Please try again.', first_error)

        body, generated_tags = _post_process_generated(first_draft_raw)

        # ── Speculative parallelism: evaluate quality + verify claims concurrently ──
        # Determine verification parameters upfront so we can fire both tasks together.
        _run_verify = False
        _verify_kb_ctx = ''
        if grounding_level in (_GROUNDING_FULL, _GROUNDING_PARTIAL) and kb_context and _has_budget(15):
            _run_verify = True
            _verify_kb_ctx = kb_context
        elif grounding_level == _GROUNDING_NONE and kb_mode != 'no_kb' and _has_budget(15):
            _run_verify = True
            _verify_kb_ctx = ''

        _first_body = body  # remember first-draft body for later comparison

        with ThreadPoolExecutor(max_workers=2, thread_name_prefix='gen-parallel') as _pool:
            _eval_future = _pool.submit(_evaluate_post_quality, ai, body, theme, goal_key)
            _verify_future = (
                _pool.submit(_verify_claims_against_kb, ai, body, _verify_kb_ctx, user_industry)
                if _run_verify else None
            )
            evaluation = _eval_future.result()

        quality_threshold = clamp_int(req_data.get('quality_threshold', 75), 60, 95, 75)
        retry_cap_rate = 0.80
        try:
            retry_cap_rate = float(req_data.get('retry_cap_rate', os.getenv('GENERATION_RETRY_CAP_RATE', '0.80')))
        except Exception:
            retry_cap_rate = 0.35
        retry_cap_rate = max(0.0, min(1.0, retry_cap_rate))

        retry_attempted = False
        retry_allowed = random.random() < retry_cap_rate
        selected_draft = 'draft_1'
        second_evaluation = None

        if evaluation.get('score', 0) < quality_threshold and retry_allowed and _has_budget(20):
            retry_attempted = True
            feedback_issues = evaluation.get('issues') or [
                'Improve hook specificity and topic anchoring',
                'Increase clarity and concrete detail',
                'Strengthen CTA quality'
            ]
            retry_prompt = _PromptBuilder.build_retry_prompt(
                prompt, evaluation.get('score', 0), feedback_issues
            )
            try:
                second_draft_raw = _generate_once(retry_prompt)
                second_body, second_generated_tags = _post_process_generated(second_draft_raw)
                second_evaluation = _evaluate_post_quality(ai, second_body, theme, goal_key)

                if second_evaluation.get('score', 0) > evaluation.get('score', 0):
                    body = second_body
                    generated_tags = second_generated_tags
                    evaluation = second_evaluation
                    selected_draft = 'draft_2'
            except Exception as retry_error:
                logger.warning('Second draft retry failed, keeping first draft: %s', retry_error)

        # ── Post-generation claim verification & auto-rewrite ─────────────────
        # If body is unchanged from first draft, reuse the speculative verification
        # result that was computed in parallel.  If body changed (retry picked draft 2),
        # re-run verification on the new body.
        claim_verification = {'has_issues': False, 'ungrounded_claims': [], 'rewrite_instructions': ''}
        grounding_rewrite_applied = False

        if _run_verify:
            if body is _first_body and _verify_future is not None:
                # Body unchanged — harvest the speculative parallel result
                try:
                    claim_verification = _verify_future.result()
                except Exception as e:
                    logger.warning('Speculative claim verification failed: %s', e)
            elif _has_budget(15):
                # Body changed after retry — re-verify on new body
                claim_verification = _verify_claims_against_kb(ai, body, _verify_kb_ctx, user_industry)

            if claim_verification.get('has_issues') and _has_budget(10):
                logger.info('Claim verification found %d ungrounded claims — auto-rewriting',
                            len(claim_verification.get('ungrounded_claims', [])))
                rewritten_body = _rewrite_ungrounded_claims(
                    ai, body, claim_verification, user_industry, user_role, _verify_kb_ctx
                )
                if rewritten_body != body:
                    body = enforce_linkedin_quality(
                        remove_hashtags_from_body(rewritten_body),
                        user_industry, user_role, theme, target_audience_hint, emoji_level,
                    )
                    body = enforce_word_ceiling(body, max_words)
                    grounding_rewrite_applied = True
                    if _verify_kb_ctx:
                        logger.info('Grounding rewrite applied successfully')

        candidate_tags = derive_hashtag_candidates(theme, user_industry, user_role, topics)
        merged_tags = normalize_hashtags(generated_tags + candidate_tags)
        final_hashtags = merged_tags[:hashtag_count] if hashtag_count > 0 else []

        if final_hashtags:
            content = f"{body}\n\n{' '.join(final_hashtags)}".strip()
        else:
            content = body
        
        _elapsed = time.time() - _request_start
        logger.info(f"Successfully generated preview ({_elapsed:.1f}s / {_REQUEST_BUDGET_SEC}s budget): {content[:100]}...")

        # ── Sentence-level grounding analysis (author-side only) ──────────────
        sentence_grounding = []
        try:
            if kb_used and kb_hits:
                sentence_grounding = _score_sentences_grounding(body, kb_hits, rag_store=rag)
        except Exception as sg_err:
            logger.debug('Sentence grounding scoring failed (non-critical): %s', sg_err)

        # ── Source traceability (author-side) ─────────────────────────────────
        source_traceability = _build_source_traceability(kb_hits, body)

        # ── KB gap analysis ───────────────────────────────────────────────────
        gap_analysis = _analyze_kb_coverage_gaps(
            theme or topic_hint, user_industry, user_role, kb_hits, grounding_level
        )

        # ── Grounding telemetry ───────────────────────────────────────────────
        _log_grounding_telemetry(user_id, {
            'grounding_level': grounding_level,
            'avg_similarity': kb_avg_similarity,
            'kb_hits_count': len(kb_hits),
            'coverage_pct': gap_analysis.get('coverage_pct', 0),
            'strict_mode': strict_grounding,
            'rewrite_applied': grounding_rewrite_applied,
            'kb_mode': kb_mode,
            'topic': theme or topic_hint,
            'industry': user_industry,
            'role': user_role,
        })

        _increment_monthly_usage(
            user_id,
            posts_generated=1,
            api_calls=_token_totals['calls'] or 1,
            ai_prompt_tokens=_token_totals['prompt'],
            ai_completion_tokens=_token_totals['completion'],
            ai_total_tokens=_token_totals['total'],
        )

        return jsonify({
            'success': True,
            'strict_grounding_downgraded': _strict_grounding_downgraded,
            'content': content,
            'text': content,
            'post': content,
            'hashtags': final_hashtags,
            'theme': theme,
            'kb_used': kb_used,
            'kb_no_match': kb_no_match,
            'kb_state': kb_state,
            'kb_sources': sorted(list(set(kb_sources))),
            'grounding': {
                'level': grounding_level,
                'label': {
                    _GROUNDING_FULL: 'KB-Grounded',
                    _GROUNDING_PARTIAL: 'Partially Grounded',
                    _GROUNDING_NONE: 'Insight Mode',
                }.get(grounding_level, 'Unknown'),
                'description': {
                    _GROUNDING_FULL: 'All claims are backed by your knowledge base.',
                    _GROUNDING_PARTIAL: 'Some claims are KB-backed; others are framed as insights.',
                    _GROUNDING_NONE: 'No KB match found. Content is opinion and insight-based only.',
                }.get(grounding_level, ''),
                'kb_hits_count': len(kb_hits),
                'avg_similarity': round(kb_avg_similarity, 3),
                'claim_verification': {
                    'ran': bool(claim_verification.get('has_issues') is not None and kb_context),
                    'issues_found': claim_verification.get('has_issues', False),
                    'ungrounded_claims_count': len(claim_verification.get('ungrounded_claims', [])),
                    'auto_rewrite_applied': grounding_rewrite_applied,
                },
                'sentence_scores': sentence_grounding,
                'source_traceability': source_traceability,
            },
            'gap_analysis': gap_analysis,
            'settings_applied': {
                'industry': user_industry,
                'role': user_role,
                'topics': topics,
                'hashtag_count': hashtag_count,
                'emoji_level': emoji_level,
                'word_count_mode': word_count_mode,
                'min_words': min_words,
                'max_words': max_words,
                'output_words': words_count(content),
                'kb_mode': kb_mode,
                'workspace_id': workspace_id,
                'kb_selected_file_count': kb_selected_file_count,
                'kb_selected_file_ids': kb_selected_file_ids,
                'audience_type': audience_type,
                'target_audience': target_audience,
                'business_goal': business_goal,
                'goal_key': goal_key,
                'post_goal': post_goal,
                'tone': post_tone,
                'style_clone_mode': style_clone_mode,
                'strict_grounding': strict_grounding,
                'kb_avg_similarity': round(kb_avg_similarity, 3),
                'kb_low_confidence': kb_low_confidence,
                'grounding_level': grounding_level,
                'grounding_rewrite_applied': grounding_rewrite_applied,
                'quality_score': evaluation.get('score', 0),
                'quality_threshold': quality_threshold,
                'quality_retry_allowed': retry_allowed,
                'quality_retry_attempted': retry_attempted,
                'selected_draft': selected_draft,
                'retry_cap_rate': retry_cap_rate,
                'quality_metrics': {
                    'clarity': evaluation.get('clarity', 0),
                    'novelty': evaluation.get('novelty', 0),
                    'specificity': evaluation.get('specificity', 0),
                    'hook': evaluation.get('hook', 0),
                    'cta': evaluation.get('cta', 0),
                },
                'quality_issues': evaluation.get('issues', []),
                'draft_2_quality_score': second_evaluation.get('score', 0) if isinstance(second_evaluation, dict) else None
            }
        })
    except Exception as e:
        logger.exception("Generate preview failed")
        return _safe_api_error('Generation Error', e)

@app.route('/api/dashboard-init', methods=['GET'])
@require_auth
def dashboard_init():
    """Batch endpoint that returns config + posts + scheduled posts + analytics + billing + KB status.

    Eliminates 8-10 sequential fetch calls on the frontend cold load.
    """
    try:
        user_id = get_current_user_id()
        config_obj = load_config(user_id)

        # Posts
        posts = _db_list_posts(user_id, limit=10)
        if not posts:
            posts = [
                row for row in _read_json_list(POSTS_PATH)
                if str(row.get('user_id') or '').strip() == str(user_id)
            ][-10:][::-1]

        # Scheduled posts
        scheduled = _db_list_scheduled_posts(user_id)
        if not scheduled:
            scheduled = [
                row for row in _read_json_list(SCHEDULED_POSTS_PATH)
                if str(row.get('user_id') or '').strip() == str(user_id)
            ]

        # Analytics
        all_posts_for_analytics = _db_list_posts(user_id, limit=200)
        if not all_posts_for_analytics:
            all_posts_for_analytics = [
                row for row in _read_json_list(POSTS_PATH)
                if str(row.get('user_id') or '').strip() == str(user_id)
            ]
        analytics = _calculate_real_analytics(all_posts_for_analytics, scheduled)

        # Billing
        effective_plan = _get_effective_plan(user_id)
        plan_limits = _get_plan_limits(effective_plan)
        usage = _get_monthly_usage_row(user_id)

        # KB status
        kb_status = {}
        try:
            from rag_system_pgvector import RAGStore
            rag = RAGStore(user_id=user_id)
            files = rag.db.list_kb_files(user_id)
            total_chunks = sum(int(f.get('chunk_count') or 0) for f in files)
            kb_status = {
                'files_count': len(files),
                'total_chunks': total_chunks,
                'is_training': is_kb_training(user_id),
            }
        except Exception:
            kb_status = {'files_count': 0, 'total_chunks': 0, 'is_training': False}

        # Config (safe subset)
        safe_config = {k: v for k, v in config_obj.items() if k not in (
            'LINKEDIN_CLIENT_SECRET', 'GOOGLE_API_KEY', 'OPENAI_API_KEY',
            'ANTHROPIC_API_KEY', 'DEEPSEEK_API_KEY', 'XAI_API_KEY',
        )}

        return jsonify({
            'success': True,
            'config': safe_config,
            'posts': posts,
            'scheduled_posts': scheduled,
            'analytics': analytics,
            'billing': {
                'plan': effective_plan,
                'limits': plan_limits,
                'usage': usage,
            },
            'kb_status': kb_status,
        })
    except Exception as e:
        logger.exception('dashboard-init failed')
        return _safe_api_error('Failed to load dashboard data', e)


@app.route('/api/posts', methods=['GET'])
@require_auth
def get_posts():
    """Get recently generated posts"""
    try:
        user_id = get_current_user_id()
        # Primary: read from Supabase
        db_posts = _db_list_posts(user_id, limit=10)
        if db_posts:
            return jsonify({'success': True, 'posts': db_posts})
        # Fallback: read from JSON file (legacy data)
        posts = [
            row for row in _read_json_list(POSTS_PATH)
            if str(row.get('user_id') or '').strip() == str(user_id)
        ]
        return jsonify({'success': True, 'posts': posts[-10:][::-1]})
    except Exception as e:
        return _safe_api_error('An unexpected error occurred', e)
@app.route('/api/clear-post-history', methods=['POST'])
@require_auth
def clear_post_history():
    """Clear post history for current user (or all legacy entries without user_id)."""
    try:
        user_id = get_current_user_id()
        # Primary: delete from DB
        db_cleared = _db_delete_user_posts(user_id)
        # Also clean JSON backup
        posts = _read_json_list(POSTS_PATH)
        has_user_scoped_rows = any(str(row.get('user_id') or '').strip() for row in posts)
        if has_user_scoped_rows:
            remaining = [
                row for row in posts
                if str(row.get('user_id') or '').strip() != str(user_id)
            ]
        else:
            remaining = []
        json_cleared = len(posts) - len(remaining)
        _write_json_list(POSTS_PATH, remaining)
        cleared_count = max(db_cleared, json_cleared)

        return jsonify({
            'success': True,
            'cleared': cleared_count,
            'message': f'Cleared {cleared_count} post(s) from history.'
        })
    except Exception as e:
        logger.exception("Failed to clear post history")
        return _safe_api_error('An unexpected error occurred', e)


@app.route('/api/posts/<post_id>/edit', methods=['POST'])
@require_auth
def edit_post(post_id):
    """Edit a post's content and/or hashtags before publishing."""
    try:
        user_id = get_current_user_id()
        data = request.get_json() or {}
        new_content = data.get('content')
        new_hashtags = data.get('hashtags')

        if new_content is not None and not str(new_content).strip():
            return jsonify({'success': False, 'message': 'Content cannot be empty'}), 400

        # Try DB first
        db_posts = _db_list_posts(user_id, limit=500)
        found_in_db = False
        for db_post in db_posts:
            if str(db_post.get('id')) == str(post_id):
                updates = {}
                if new_content is not None:
                    updates['content'] = str(new_content).strip()
                if new_hashtags is not None:
                    updates['hashtags'] = new_hashtags if isinstance(new_hashtags, list) else []
                if updates:
                    _db_update_post(post_id, updates)
                found_in_db = True
                break

        if not found_in_db:
            return jsonify({'success': False, 'message': 'Post not found'}), 404

        return jsonify({'success': True, 'message': 'Post updated successfully'})
    except Exception as e:
        logger.exception("Failed to edit post %s", post_id)
        return _safe_api_error('An unexpected error occurred', e)


@app.route('/api/analytics', methods=['GET'])
@require_auth
def get_analytics():
    """Return real analytics calculated from persisted post data (no simulated metrics)."""
    try:
        user_id = get_current_user_id()
        # Primary: DB
        posts = _db_list_posts(user_id, limit=200)
        if not posts:
            posts = [
                row for row in _read_json_list(POSTS_PATH)
                if str(row.get('user_id') or '').strip() == str(user_id)
            ]
        scheduled_posts = _db_list_scheduled_posts(user_id)
        if not scheduled_posts:
            scheduled_posts = [
                row for row in _read_json_list(SCHEDULED_POSTS_PATH)
                if str(row.get('user_id') or '').strip() == str(user_id)
            ]
        analytics = _calculate_real_analytics(posts, scheduled_posts)
        return jsonify({'success': True, 'analytics': analytics})
    except Exception as e:
        logger.exception("Failed to compute analytics")
        return _safe_api_error('An unexpected error occurred', e)


@app.route('/api/sync-linkedin-analytics', methods=['POST'])
@require_auth
def sync_linkedin_analytics():
    """Fetch latest LinkedIn social metrics for posted items with known URNs."""
    try:
        payload = request.get_json(silent=True) or {}
        max_posts = payload.get('max_posts', 25)
        try:
            max_posts = int(max_posts)
        except Exception:
            max_posts = 25
        max_posts = min(max(max_posts, 1), 100)

        user_id = get_current_user_id()
        result = _sync_linkedin_analytics(max_posts=max_posts, user_id=user_id)
        status_code = 200 if result.get('success') else 400
        return jsonify(result), status_code
    except Exception as e:
        logger.exception("Failed to sync LinkedIn analytics")
        return _safe_api_error('An unexpected error occurred', e)

@app.route('/api/schedule-post', methods=['POST'])
@require_auth
def schedule_post():
    """Schedule a post for later"""
    try:
        data = request.get_json() or {}
        user_id = get_current_user_id()
        content = data.get('content', '')
        hashtags = data.get('hashtags', [])
        schedule_time = data.get('schedule_time', '')
        
        if not content or not schedule_time:
            return jsonify({'success': False, 'message': 'Content and schedule time required'})

        try:
            scheduled_dt = _parse_schedule_datetime(schedule_time)
            if scheduled_dt == datetime.min:
                raise ValueError('Invalid schedule time')
        except Exception:
            return jsonify({'success': False, 'message': 'Invalid schedule time format'}), 400

        min_dt = datetime.now() + timedelta(minutes=2)
        if scheduled_dt < min_dt:
            return jsonify({'success': False, 'message': 'Schedule time must be at least 2 minutes from now'}), 400
        
        effective_plan = _get_effective_plan(user_id)
        plan_limits = _get_plan_limits(effective_plan)
        scheduled_limit = _plan_limit_int(plan_limits, 'scheduled_posts', 10)

        if scheduled_limit <= 0:
            return jsonify({
                'success': False,
                'message': 'Scheduling automation is available on paid plans. Please upgrade to schedule posts on LinkedIn.'
            }), 403

        # Server-side protection: cap scheduled posts based on plan limits.
        user_scheduled_count = _get_user_scheduled_count(user_id)
        if user_scheduled_count >= scheduled_limit:
            return jsonify({
                'success': False,
                'message': f'You can schedule up to {scheduled_limit} posts on your {effective_plan.replace("_", " ")} plan. Please publish/cancel some scheduled posts first.'
            }), 403
        
        # Add new scheduled post
        scheduled_post = {
            'content': content,
            'hashtags': hashtags,
            'schedule_time': schedule_time,
            'created_at': datetime.now().isoformat(),
            'id': f"sp_{uuid4().hex[:12]}",
            'user_id': user_id,
            **_extract_post_metadata(data)
        }
        
        # Save to DB (primary) + JSON (backup)
        _db_save_scheduled_post(user_id, scheduled_post)
        scheduled_posts = _read_json_list(SCHEDULED_POSTS_PATH)
        scheduled_posts.append(scheduled_post)
        _write_json_list(SCHEDULED_POSTS_PATH, scheduled_posts)
        
        return jsonify({'success': True, 'message': f'Post scheduled for {schedule_time}'})
    except Exception as e:
        logger.exception("Failed to schedule post")
        return _safe_api_error('Scheduling failed', e)
@app.route('/api/scheduled-posts', methods=['GET'])
@require_auth
def get_scheduled_posts():
    """Return scheduled posts ordered by schedule time"""
    try:
        user_id = get_current_user_id()
        # Primary: DB
        scheduled_posts = _db_list_scheduled_posts(user_id)
        if not scheduled_posts:
            scheduled_posts = [
                row for row in _read_json_list(SCHEDULED_POSTS_PATH)
                if str(row.get('user_id') or '').strip() == str(user_id)
            ]

        def parse_dt(value):
            try:
                parsed = _parse_schedule_datetime(value)
                return parsed if parsed != datetime.min else datetime.max
            except Exception:
                return datetime.max

        scheduled_posts.sort(key=lambda item: parse_dt(item.get('schedule_time', '')))

        return jsonify({'success': True, 'posts': scheduled_posts})
    except Exception as e:
        logger.exception("Failed to load scheduled posts")
        return _safe_api_error('An unexpected error occurred', e)

@app.route('/api/reschedule-post', methods=['POST'])
@require_auth
def reschedule_post():
    """Reschedule an existing post by id"""
    try:
        data = request.get_json() or {}
        user_id = get_current_user_id()
        post_id = data.get('id')
        schedule_time = data.get('schedule_time', '')

        if not post_id or not schedule_time:
            return jsonify({'success': False, 'message': 'Post id and schedule time required'}), 400

        try:
            scheduled_dt = _parse_schedule_datetime(schedule_time)
            if scheduled_dt == datetime.min:
                raise ValueError('Invalid schedule time')
        except Exception:
            return jsonify({'success': False, 'message': 'Invalid schedule time format'}), 400

        min_dt = datetime.now() + timedelta(minutes=2)
        if scheduled_dt < min_dt:
            return jsonify({'success': False, 'message': 'Schedule time must be at least 2 minutes from now'}), 400

        scheduled_posts = _read_json_list(SCHEDULED_POSTS_PATH)

        updated = False
        for post in scheduled_posts:
            owner_id = str(post.get('user_id') or '').strip()
            is_owner = (owner_id == str(user_id)) or (not owner_id)
            if str(post.get('id')) == str(post_id) and is_owner:
                post['schedule_time'] = schedule_time
                if not owner_id:
                    post['user_id'] = user_id
                updated = True
                break

        if not updated:
            return jsonify({'success': False, 'message': 'Scheduled post not found'}), 404

        _write_json_list(SCHEDULED_POSTS_PATH, scheduled_posts)
        # Update DB
        try:
            if auth_supabase:
                auth_supabase.table('scheduled_posts_v2').update(
                    {'schedule_time': schedule_time}
                ).eq('id', post_id).execute()
        except Exception:
            pass

        return jsonify({'success': True, 'message': 'Post rescheduled successfully'})
    except Exception as e:
        logger.exception("Failed to reschedule post")
        return _safe_api_error('An unexpected error occurred', e)

@app.route('/api/cancel-scheduled-post', methods=['POST'])
@require_auth
def cancel_scheduled_post():
    """Cancel a scheduled post by id"""
    try:
        data = request.get_json() or {}
        user_id = get_current_user_id()
        post_id = data.get('id')
        if not post_id:
            return jsonify({'success': False, 'message': 'Post id required'}), 400

        scheduled_posts = _read_json_list(SCHEDULED_POSTS_PATH)

        new_posts = [
            post for post in scheduled_posts
            if not (
                str(post.get('id')) == str(post_id)
                and (
                    str(post.get('user_id') or '') == str(user_id)
                    or not str(post.get('user_id') or '').strip()
                )
            )
        ]
        if len(new_posts) == len(scheduled_posts):
            return jsonify({'success': False, 'message': 'Scheduled post not found'}), 404

        _write_json_list(SCHEDULED_POSTS_PATH, new_posts)
        # Also remove from DB
        _db_delete_scheduled_post(post_id)

        return jsonify({'success': True, 'message': 'Scheduled post canceled'})
    except Exception as e:
        logger.exception("Failed to cancel scheduled post")
        return _safe_api_error('An unexpected error occurred', e)

@app.route('/api/post-now', methods=['POST'])
@require_auth
def post_now():
    """Post content immediately (either from preview or generate new)"""
    try:
        from ai_provider import AIProvider
        from linkedin_poster import LinkedInPoster
        import random
        import config as cfg
        
        user_id = get_current_user_id()
        
        # Check quota before posting
        can_generate, quota_meta = _check_generation_guardrail(user_id)
        if not can_generate:
            return jsonify({
                'success': False,
                'quota_exceeded': True,
                'quota_info': quota_meta,
                **quota_meta
            }), 403
        
        config_obj = load_config(user_id)
        data = request.get_json() or {}
        use_preview = data.get('usePreview', False)
        preview_content = data.get('content', '')
        preview_hashtags = data.get('hashtags', [])
        
        # If preview content provided, use it; otherwise generate new
        if use_preview and preview_content:
            content = preview_content
            hashtags = preview_hashtags
            theme = 'User Preview'  # Mark as user-provided preview
            logger.info(f"Posting preview content ({len(content)} chars)")
        else:
            # Generate new content
            ai = _build_platform_ai_provider()
            user_industry = (data.get('industry') or config_obj.get('CONTENT_INDUSTRY') or '').strip()
            user_role = (data.get('role') or config_obj.get('USER_ROLE') or '').strip()
            neutral_themes = [
                f"{user_industry or 'technology'} trends and practical execution",
                f"{user_role or 'leadership'} playbooks and lessons",
                "team productivity and workflow optimization",
                "product and engineering collaboration",
                "scaling operations with better systems"
            ]
            theme = random.choice(neutral_themes)
            fmt = random.choice(POST_FORMATS)
            services = f"Professional context for {user_industry or 'business and technology'} audiences, with {user_role or 'leadership'} perspective."
            
            # Improved prompt for better human-like content
            prompt = f"""Generate a professional LinkedIn post about: {theme}

Context: {services}

Requirements:
- Write in a natural, human-like tone (not generic AI)
- Avoid placeholder text like [Company Name], [Exchange Name], or [Exchange]
- Be specific and authentic
- Include 1-2 actionable insights or takeaways
- Keep it between {config_obj['MIN_POST_LENGTH']} and {config_obj['MAX_POST_LENGTH']} characters
- Do NOT include hashtags in the post body

Format: {fmt}

Write ONLY the post content, nothing else."""
            
            result = ai.generate(prompt, max_tokens=500, task='generate')
            content = result['text'].strip()
            
            # Generate relevant hashtags based on theme
            hashtags = ['#LinkedIn', '#Leadership', '#Growth']
            
            logger.info(f"Generated new content ({len(content)} chars) for theme: {theme}")
        
        # Post to LinkedIn
        poster = LinkedInPoster(
            test_mode=config_obj['TEST_MODE'],
            access_token=config_obj.get('LINKEDIN_ACCESS_TOKEN', ''),
            person_id=config_obj.get('LINKEDIN_PERSON_ID', '')
        )
        post_result = poster.post(content)
        
        # Save to posts history
        post_data = {
            'content': content,
            'hashtags': hashtags,
            'theme': theme,
            'created_at': datetime.now().isoformat(),
            'user_id': user_id,
            'posted': post_result.get('status') == 'posted',
            'test_mode': config_obj['TEST_MODE'],
            'provider': post_result.get('provider') or 'linkedin',
            'linkedin_urn': post_result.get('linkedin_urn'),
            'publish_result': post_result.get('status'),
            'publish_response': post_result.get('response') if isinstance(post_result.get('response'), dict) else None,
            **_extract_post_metadata(data)
        }
        
        # Load existing posts
        posts = _read_json_list(POSTS_PATH)
        
        posts.append(post_data)
        
        # Save to DB (primary) + JSON (backup)
        _db_save_post(user_id, post_data)
        _write_json_list(POSTS_PATH, posts)
        
        if post_result.get('status') == 'posted':
            status_message = "Post published successfully!"
        elif config_obj['TEST_MODE']:
            status_message = "Post preview generated (test mode)"
        else:
            status_message = f"Failed to post: {post_result.get('error', 'Unknown error')}"
        
        return jsonify({
            'success': True,
            'message': status_message,
            'post': {
                'content': content,
                'hashtags': hashtags,
                'theme': theme
            }
        })
    except Exception as e:
        logger.exception("Failed to post now")
        return _safe_api_error('Posting failed', e)
# ============= KNOWLEDGE BASE & MODEL TRAINING ENDPOINTS =============

@app.route('/api/upload-knowledge-base', methods=['POST'])
@limiter.limit("20 per minute")
@require_auth
def upload_knowledge_base():
    """Upload PDF or DOCX files to the knowledge base"""
    try:
        from werkzeug.utils import secure_filename
        
        files = []
        if 'files' in request.files:
            files = request.files.getlist('files')
        elif 'file' in request.files:
            files = request.files.getlist('file')
        else:
            logger.warning("Upload request missing 'files' or 'file' field")
            return jsonify({'success': False, 'message': 'No files provided'}), 400

        if not files or all(not f.filename for f in files):
            logger.warning("No files selected in upload")
            return jsonify({'success': False, 'message': 'No files selected'}), 400

        user_id = ensure_kb_user_id()
        if not user_id:
            return jsonify({
                'success': False,
                'message': 'Authentication required for knowledge base actions. Please sign in again and retry.'
            }), 401

        from rag_system_pgvector import RAGStore
        rag = RAGStore(user_id=user_id)

        user_pdf_dir = get_user_pdf_dir(user_id)
        os.makedirs(user_pdf_dir, exist_ok=True)
        
        effective_plan = _get_effective_plan(user_id)
        plan_limits = _get_plan_limits(effective_plan)
        max_documents = _plan_limit_int(plan_limits, 'kb_documents', MAX_DOCUMENTS_PER_USER)
        max_storage_mb = _plan_limit_int(plan_limits, 'kb_storage_mb', (MAX_TOTAL_FILE_SIZE // (1024 * 1024)))
        max_total_size = max_storage_mb * 1024 * 1024

        if max_documents <= 0 or max_total_size <= 0:
            return jsonify({
                'success': False,
                'message': 'Knowledge base upload is available on paid plans. Please upgrade to continue.'
            }), 403

        # Check document count limit
        existing_records = rag.db.list_kb_files(user_id)
        if len(existing_records) >= max_documents:
            logger.warning(f"Document limit reached for user {user_id}: {len(existing_records)}/{max_documents}")
            return jsonify({
                'success': False, 
                'message': f'Maximum {max_documents} documents allowed for your plan. Delete some files first or upgrade your plan.'
            }), 403

        existing_total_size = 0
        for row in existing_records:
            try:
                existing_total_size += int(row.get('size_bytes') or row.get('file_size') or 0)
            except Exception:
                continue

        # Save uploaded files with validation
        uploaded_count = 0
        skipped_count = 0
        allowed_extensions = ('.pdf', '.docx', '.txt', '.md', '.csv', '.pptx')
        skipped_reasons = []
        saved_filepaths = []
        uploaded_size_bytes = 0
        
        for file in files:
            if not file or not file.filename:
                continue
            
            filename = secure_filename(file.filename)
            file_ext = filename.lower()
            
            # Check if file has allowed extension
            if not any(file_ext.endswith(ext) for ext in allowed_extensions):
                logger.warning("Skipping unsupported file type: %s", filename)
                skipped_reasons.append(f"{filename}: Unsupported file type (allowed: PDF, DOCX, TXT, MD, CSV, PPTX)")
                skipped_count += 1
                continue
            
            file_size_bytes = len(file.read())
            # Check file size
            if file_size_bytes > MAX_PDF_SIZE:
                file.seek(0)
                logger.warning(f"File too large: {filename} (max {MAX_PDF_SIZE/1024/1024}MB)")
                skipped_reasons.append(f"{filename}: File too large (max 50MB)")
                skipped_count += 1
                continue
            
            file.seek(0)
            
            # Check if we've hit the document limit
            current_count = len(existing_records) + uploaded_count
            if current_count >= max_documents:
                logger.warning(f"Hit document limit during batch upload")
                skipped_reasons.append(f"{filename}: Document limit reached")
                skipped_count += 1
                continue

            current_total_size = existing_total_size + uploaded_size_bytes
            if current_total_size + file_size_bytes > max_total_size:
                limit_mb = max_total_size / (1024 * 1024)
                logger.warning("KB storage limit reached for user %s", user_id)
                skipped_reasons.append(f"{filename}: Storage limit exceeded ({limit_mb:.0f} MB max)")
                skipped_count += 1
                continue
            
            try:
                filepath = os.path.join(user_pdf_dir, filename)
                file.save(filepath)
                logger.info("Saved file: %s", filepath)
                saved_filepaths.append(filepath)
                uploaded_count += 1
                uploaded_size_bytes += file_size_bytes
            except Exception as e:
                logger.exception("Failed to save file %s: %s", filename, e)
                skipped_reasons.append(f"{filename}: Error saving file")
                skipped_count += 1
                continue
        
        if uploaded_count == 0:
            logger.warning("No PDF/DOCX files uploaded successfully")
            reason_text = " | ".join(skipped_reasons) if skipped_reasons else "Unknown error"
            return jsonify({
                'success': False, 
                'message': f'No files uploaded. {reason_text}'
            }), 400

        _increment_monthly_usage(
            user_id,
            kb_files_uploaded=uploaded_count,
            kb_storage_bytes=uploaded_size_bytes,
            api_calls=1
        )
        
        training_result = _enqueue_or_start_kb_training(user_id, mode='incremental', filepaths=saved_filepaths)
        rag_error = None
        training_job_id = training_result.get('training_job_id')
        if not training_result.get('success'):
            rag_error = training_result.get('message', 'Failed to start training')
        
        # Build response message
        response_msg = f'Successfully uploaded {uploaded_count} file(s)'
        if skipped_count > 0:
            response_msg += f' ({skipped_count} skipped)'
        if rag_error:
            response_msg += f' (RAG training note: {rag_error})'
        else:
            response_msg += f" ({training_result.get('message') or 'Training started'})"
        
        return jsonify({
            'success': True,
            'message': response_msg,
            'uploaded': uploaded_count,
            'skipped': skipped_count,
            'skipped_reasons': skipped_reasons,
            'training_job_id': training_job_id,
            'training_queued': bool(training_result.get('success')),
            'training_mode': 'queue' if training_result.get('via_queue') else 'local_background'
        })
    except Exception as e:
        logger.exception("Knowledge base upload failed")
        return _safe_api_error('Upload failed', e)

@app.route('/api/train-model', methods=['POST'])
@require_auth
def train_model():
    """Train/rebuild the RAG model with current knowledge base"""
    try:
        if not os.getenv('SUPABASE_URL') or not (os.getenv('SUPABASE_KEY') or os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_ANON_KEY')):
            return jsonify({
                'success': False,
                'message': 'Supabase is not configured. Set SUPABASE_URL and SUPABASE_KEY (or SUPABASE_SERVICE_ROLE_KEY) in .env, then restart the app.'
            }), 400

        user_id = ensure_kb_user_id()
        if not user_id:
            return jsonify({
                'success': False,
                'message': 'Authentication required for training. Please sign in again and retry.'
            }), 401

        from rag_system_pgvector import RAGStore
        rag = RAGStore(user_id=user_id)
        user_files = rag.db.list_kb_files(user_id)

        if not user_files:
            return jsonify({
                'success': False,
                'message': 'No user-specific documents found. Upload files first.'
            }), 400

        training_result = _enqueue_or_start_kb_training(user_id, mode='full')
        if not training_result.get('success'):
            if training_result.get('already_running'):
                return jsonify({
                    'success': False,
                    'message': training_result.get('message', 'Training is already in progress. Please wait and refresh status.')
                }), 409
            return jsonify({
                'success': False,
                'message': training_result.get('message', 'Failed to start training job')
            }), 500

        return jsonify({
            'success': True,
            'message': f"✅ {training_result.get('message')}. Refresh status in a few moments.",
            'training_job_id': training_result.get('training_job_id'),
            'training_mode': 'queue' if training_result.get('via_queue') else 'local_background'
        })
    except Exception as e:
        logger.exception("Model training failed")
        return _safe_api_error('Training failed', e)


@app.route('/api/train-last-kb-file', methods=['POST'])
@require_auth
def train_last_kb_file():
    """Queue incremental indexing for the most recently uploaded KB file."""
    try:
        if not os.getenv('SUPABASE_URL') or not (os.getenv('SUPABASE_KEY') or os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_ANON_KEY')):
            return jsonify({
                'success': False,
                'message': 'Supabase is not configured. Set SUPABASE_URL and SUPABASE_KEY (or SUPABASE_SERVICE_ROLE_KEY) in .env, then restart the app.'
            }), 400

        user_id = ensure_kb_user_id()
        if not user_id:
            return jsonify({
                'success': False,
                'message': 'Authentication required for training. Please sign in again and retry.'
            }), 401

        from rag_system_pgvector import RAGStore
        rag = RAGStore(user_id=user_id)
        user_files = rag.db.list_kb_files(user_id)

        if not user_files:
            return jsonify({'success': False, 'message': 'No uploaded files found. Upload a file first.'}), 400

        def _parse_created(value):
            text = str(value or '').strip()
            if not text:
                return datetime.min
            try:
                return datetime.fromisoformat(text.replace('Z', '+00:00')).replace(tzinfo=None)
            except Exception:
                return datetime.min

        latest_record = max(user_files, key=lambda row: _parse_created(row.get('created_at')))
        latest_filename = str(latest_record.get('filename') or '').strip()
        if not latest_filename:
            return jsonify({'success': False, 'message': 'Latest uploaded file could not be resolved.'}), 400

        local_path = resolve_local_kb_path(
            latest_record.get('storage_path') or '',
            latest_filename,
            user_id
        )

        if not local_path or not os.path.isfile(local_path):
            return jsonify({
                'success': False,
                'message': 'Latest uploaded file is not available locally. Use Rebuild All Files instead.'
            }), 400

        training_result = _enqueue_or_start_kb_training(user_id, mode='incremental', filepaths=[local_path])
        if not training_result.get('success'):
            if training_result.get('already_running'):
                return jsonify({
                    'success': False,
                    'message': training_result.get('message', 'Training is already in progress. Please wait and retry.')
                }), 409
            return jsonify({
                'success': False,
                'message': training_result.get('message', 'Failed to start training job')
            }), 500

        return jsonify({
            'success': True,
            'message': f"{training_result.get('message')} for latest file: {latest_filename}",
            'filename': latest_filename,
            'training_job_id': training_result.get('training_job_id'),
            'training_mode': 'queue' if training_result.get('via_queue') else 'local_background'
        })
    except Exception as e:
        logger.exception('Latest-file training failed')
        return _safe_api_error('Failed to index latest file', e)

@app.route('/api/knowledge-base-status', methods=['GET'])
@require_auth
def knowledge_base_status():
    """Get knowledge base statistics"""
    try:
        from rag_system_pgvector import RAGStore

        user_id = ensure_kb_user_id()
        if not user_id:
            return jsonify({
                'success': False,
                'message': 'Authentication required to load knowledge base status. Please sign in again.'
            }), 401

        # Count only this user's uploaded documents
        file_count = 0
        pdf_count = 0
        docx_count = 0

        # Try pgvector status; if it fails, still return upload counters
        is_trained = False
        doc_count_in_rag = 0
        indexed_file_count = 0
        rag_error = None
        try:
            rag = RAGStore(user_id=user_id)
            is_trained = rag.is_built()
            doc_count_in_rag = rag.get_document_count()
            kb_files = rag.db.list_kb_files(user_id)
            file_count = len(kb_files)
            pdf_count = len([f for f in kb_files if (f.get('file_type') or '').lower() == 'pdf'])
            docx_count = len([f for f in kb_files if (f.get('file_type') or '').lower() == 'docx'])
            indexed_file_count = len([f for f in kb_files if (f.get('upload_status') or '').lower() == 'indexed'])
        except Exception as e:
            rag_error = str(e)
            logger.warning("KB status fallback mode (pgvector unavailable): %s", e)

        training_state = get_kb_training_status(user_id)
        local_training_state = get_kb_training_state(user_id)

        queue_in_progress = bool(training_state.get('in_progress', False))
        local_in_progress = bool(local_training_state.get('in_progress', False))
        merged_training_in_progress = queue_in_progress or local_in_progress

        merged_training_status = training_state.get('status', 'idle')
        if local_in_progress:
            merged_training_status = local_training_state.get('status') or 'running'
        elif str(merged_training_status).strip().lower() in {'idle', 'queue_unavailable'}:
            local_status = str(local_training_state.get('status') or '').strip().lower()
            if local_status and local_status not in {'idle'}:
                merged_training_status = local_status

        merged_training_error = training_state.get('error')
        if local_training_state.get('error'):
            merged_training_error = local_training_state.get('error')

        response = {
            'success': True,
            'trained': is_trained,
            'rag_ready': is_trained,
            'knowledge_base_trained': is_trained,
            'training_in_progress': merged_training_in_progress,
            'training_status': merged_training_status,
            'training_error': merged_training_error,
            'training_job_id': training_state.get('job_id'),
            'total_uploaded_files': file_count,
            'pdf_count': pdf_count,
            'pdf_count_detail': pdf_count,
            'docx_count': docx_count,
            'trained_file_count': indexed_file_count,
            'indexed_file_count': indexed_file_count,
            'rag_document_count': doc_count_in_rag,
            'status': 'Ready for use' if is_trained else ('Needs training' if file_count > 0 else 'No documents'),
            'max_documents': MAX_DOCUMENTS_PER_USER
        }
        if is_trained and file_count > 0 and indexed_file_count == 0:
            response['trained_file_count'] = file_count
            response['indexed_file_count'] = file_count
        if not training_state.get('queue_available', True) and not local_in_progress:
            response['queue_warning'] = f"KB queue unavailable: {training_state.get('error')}"
        if rag_error:
            response['rag_warning'] = f'Vector status unavailable: {rag_error}'
        return jsonify(response)
    except Exception as e:
        logger.exception("Knowledge base status check failed")
        return _safe_api_error('Status check failed', e)

@app.route('/api/list-knowledge-base-files', methods=['GET'])
@require_auth
def list_knowledge_base_files():
    """List all uploaded knowledge base files"""
    try:
        from rag_system_pgvector import RAGStore

        user_id = ensure_kb_user_id()
        if not user_id:
            return jsonify({
                'success': False,
                'message': 'Authentication required to list knowledge base files. Please sign in again.'
            }), 401

        rag = RAGStore(user_id=user_id)
        kb_files = rag.db.list_kb_files(user_id)
        rag_is_trained = False
        rag_doc_count = 0
        try:
            rag_is_trained = bool(rag.is_built())
            rag_doc_count = int(rag.get_document_count() or 0)
        except Exception:
            rag_is_trained = False
            rag_doc_count = 0

        files_list = []
        for record in kb_files:
            filename = record.get('filename') or ''
            if not filename:
                continue
            file_size = int(record.get('file_size_bytes') or 0)
            file_type = (record.get('file_type') or '').upper() or ('PDF' if filename.lower().endswith('.pdf') else 'DOCX')
            raw_chunk_count = (
                record.get('chunk_count')
                or record.get('chunks')
                or record.get('chunk_total')
                or record.get('document_count')
                or 0
            )
            try:
                chunk_count = int(raw_chunk_count or 0)
            except Exception:
                chunk_count = 0

            upload_status = str(record.get('upload_status') or 'uploaded').lower()
            indexed = bool(record.get('indexed')) or upload_status == 'indexed' or chunk_count > 0
            if indexed and upload_status in {'uploaded', 'pending', 'processing', 'queued', ''}:
                upload_status = 'indexed'
            files_list.append({
                'id': record.get('id'),
                'name': filename,
                'type': file_type,
                'size': round(file_size / 1024 / 1024, 2),
                'size_bytes': file_size,
                'chunks': chunk_count,
                'indexed': indexed,
                'upload_status': upload_status,
                'created_at': record.get('created_at')
            })

        if files_list and rag_is_trained and rag_doc_count > 0:
            if all(not bool(row.get('indexed')) for row in files_list):
                for row in files_list:
                    row['indexed'] = True
                    row['upload_status'] = 'indexed'

            if all(int(row.get('chunks') or 0) == 0 for row in files_list):
                base = rag_doc_count // len(files_list)
                remainder = rag_doc_count % len(files_list)
                for idx, row in enumerate(files_list):
                    row['chunks'] = base + (1 if idx < remainder else 0)
                    if row['chunks'] > 0:
                        row['indexed'] = True
                        row['upload_status'] = 'indexed'

        # Sort latest first for clearer recency actions
        files_list.sort(key=lambda x: str(x.get('created_at') or ''), reverse=True)
        
        return jsonify({
            'success': True,
            'files': files_list,
            'count': len(files_list)
        })
    except Exception as e:
        logger.exception("Failed to list files")
        return _safe_api_error('Failed to list knowledge base files', e)


@app.route('/api/kb-file-options', methods=['GET'])
@require_auth
def kb_file_options():
    try:
        from rag_system_pgvector import RAGStore

        user_id = ensure_kb_user_id()
        if not user_id:
            return jsonify({'success': False, 'message': 'Authentication required'}), 401

        rag = RAGStore(user_id=user_id)
        rows = rag.db.list_kb_files(user_id)
        options = []
        for row in rows:
            file_id = row.get('id')
            filename = row.get('filename')
            if not file_id or not filename:
                continue
            options.append({
                'id': file_id,
                'name': filename,
                'indexed': (row.get('upload_status') == 'indexed')
            })

        return jsonify({'success': True, 'files': options, 'count': len(options)})
    except Exception as e:
        logger.exception('Failed to list KB file options')
        return _safe_api_error('An unexpected error occurred', e)


@app.route('/api/kb-workspaces', methods=['GET'])
@require_auth
def list_kb_workspaces():
    try:
        user_id = ensure_kb_user_id()
        if not user_id:
            return jsonify({'success': False, 'message': 'Authentication required'}), 401

        blob = _ensure_user_feature_blob(user_id)
        return jsonify({'success': True, 'workspaces': blob.get('kb_workspaces', [])})
    except Exception as e:
        logger.exception('Failed to list KB workspaces')
        return _safe_api_error('An unexpected error occurred', e)


@app.route('/api/kb-workspaces', methods=['POST'])
@require_auth
def save_kb_workspace():
    try:
        user_id = ensure_kb_user_id()
        if not user_id:
            return jsonify({'success': False, 'message': 'Authentication required'}), 401

        data = request.get_json(silent=True) or {}
        workspace_id = str(data.get('id') or '').strip() or None

        blob = _ensure_user_feature_blob(user_id)
        workspaces = blob.get('kb_workspaces', [])

        existing_idx = -1
        existing = {}
        if workspace_id:
            for idx, ws in enumerate(workspaces):
                if str(ws.get('id')) == workspace_id:
                    existing_idx = idx
                    existing = ws
                    break

        normalized = _normalize_workspace_payload(data, existing_id=existing.get('id') if existing else workspace_id)
        if existing_idx >= 0:
            workspaces[existing_idx] = normalized
        else:
            workspaces.append(normalized)

        blob['kb_workspaces'] = workspaces
        _save_user_feature_blob(user_id, blob)

        return jsonify({'success': True, 'workspace': normalized, 'workspaces': workspaces})
    except Exception as e:
        logger.exception('Failed to save KB workspace')
        return _safe_api_error('An unexpected error occurred', e)


@app.route('/api/kb-workspaces/<workspace_id>', methods=['DELETE'])
@require_auth
def delete_kb_workspace(workspace_id):
    try:
        user_id = ensure_kb_user_id()
        if not user_id:
            return jsonify({'success': False, 'message': 'Authentication required'}), 401

        blob = _ensure_user_feature_blob(user_id)
        workspaces = blob.get('kb_workspaces', [])
        if str(workspace_id) == 'ws_all_files':
            return jsonify({'success': False, 'message': 'All Files workspace cannot be deleted'}), 400

        next_workspaces = [ws for ws in workspaces if str(ws.get('id')) != str(workspace_id)]
        blob['kb_workspaces'] = next_workspaces
        _save_user_feature_blob(user_id, blob)

        return jsonify({'success': True, 'workspaces': next_workspaces})
    except Exception as e:
        logger.exception('Failed to delete KB workspace')
        return _safe_api_error('An unexpected error occurred', e)


@app.route('/api/generation-presets', methods=['GET'])
@require_auth
def list_generation_presets():
    try:
        user_id = ensure_kb_user_id()
        if not user_id:
            return jsonify({'success': False, 'message': 'Authentication required'}), 401

        blob = _ensure_user_feature_blob(user_id)
        return jsonify({'success': True, 'presets': blob.get('generation_presets', [])})
    except Exception as e:
        logger.exception('Failed to list generation presets')
        return _safe_api_error('An unexpected error occurred', e)


@app.route('/api/generation-presets/save', methods=['POST'])
@require_auth
def save_generation_preset():
    try:
        user_id = ensure_kb_user_id()
        if not user_id:
            return jsonify({'success': False, 'message': 'Authentication required'}), 401

        if _get_effective_plan(user_id) == 'free':
            return jsonify({
                'success': False,
                'message': 'Custom templates are available on paid plans. Please upgrade to save templates.'
            }), 403

        data = request.get_json(silent=True) or {}
        name = (data.get('name') or '').strip()[:60]
        settings = data.get('settings') if isinstance(data.get('settings'), dict) else {}
        preset_id = str(data.get('id') or '').strip()

        if not name:
            return jsonify({'success': False, 'message': 'Preset name is required'}), 400

        blob = _ensure_user_feature_blob(user_id)
        presets = blob.get('generation_presets', [])

        if preset_id:
            updated = False
            for preset in presets:
                if str(preset.get('id')) == preset_id:
                    preset['name'] = name
                    preset['settings'] = settings
                    preset['updated_at'] = int(time.time())
                    updated = True
                    break
            if not updated:
                presets.append({'id': preset_id, 'name': name, 'settings': settings, 'updated_at': int(time.time())})
        else:
            presets.append({'id': f"preset_{uuid4().hex[:12]}", 'name': name, 'settings': settings, 'updated_at': int(time.time())})

        blob['generation_presets'] = presets
        _save_user_feature_blob(user_id, blob)
        return jsonify({'success': True, 'presets': presets})
    except Exception as e:
        logger.exception('Failed to save generation preset')
        return _safe_api_error('An unexpected error occurred', e)


@app.route('/api/generation-presets/<preset_id>', methods=['DELETE'])
@require_auth
def delete_generation_preset(preset_id):
    try:
        user_id = ensure_kb_user_id()
        if not user_id:
            return jsonify({'success': False, 'message': 'Authentication required'}), 401

        blob = _ensure_user_feature_blob(user_id)
        presets = blob.get('generation_presets', [])
        next_presets = [preset for preset in presets if str(preset.get('id')) != str(preset_id)]
        blob['generation_presets'] = next_presets
        _save_user_feature_blob(user_id, blob)
        return jsonify({'success': True, 'presets': next_presets})
    except Exception as e:
        logger.exception('Failed to delete generation preset')
        return _safe_api_error('An unexpected error occurred', e)


@app.route('/api/delete-knowledge-base-file', methods=['POST'])
@require_auth
def delete_knowledge_base_file():
    """Delete a knowledge base file"""
    try:
        from rag_system_pgvector import RAGStore
        
        data = request.get_json()
        if not data or 'filename' not in data:
            return jsonify({
                'success': False,
                'message': 'Filename required'
            }), 400
        
        filename = (data['filename'] or '').strip()
        # Sanitize filename
        if '/' in filename or '\\' in filename or '..' in filename:
            return jsonify({
                'success': False,
                'message': 'Invalid filename'
            }), 400

        user_id = ensure_kb_user_id()
        if not user_id:
            return jsonify({
                'success': False,
                'message': 'Authentication required to delete knowledge base files. Please sign in again.'
            }), 401

        rag = RAGStore(user_id=user_id)
        user_records = rag.db.list_kb_files(user_id)
        matching_records = [
            row for row in user_records
            if (row.get('filename') or '').lower() == filename.lower()
        ]

        if not matching_records:
            return jsonify({
                'success': False,
                'message': f'File not found for this account: {filename}'
            }), 404

        db_error = None
        deleted_count = 0
        for record in matching_records:
            try:
                local_path = resolve_local_kb_path(record.get('storage_path') or '', record.get('filename') or '', user_id)
                if os.path.isfile(local_path) and f"{os.sep}{user_id}{os.sep}" in local_path:
                    os.remove(local_path)
                rag.db.delete_kb_file(record['id'])
                deleted_count += 1
            except Exception as e:
                db_error = str(e)
                logger.exception("Failed deleting KB record/file for %s: %s", filename, e)

        response_msg = f'Successfully deleted {filename}'
        if db_error:
            response_msg += f' (DB cleanup warning: {db_error})'

        return jsonify({
            'success': True,
            'message': response_msg,
            'deleted_records': deleted_count
        })
    except Exception as e:
        logger.exception("Delete knowledge base file failed")
        return _safe_api_error('Delete failed', e)

# ============= ENTERPRISE PREMIUM FEATURES =============

@app.route('/api/industries', methods=['GET'])
def get_industries():
    """Get list of supported industries for multi-tenant feature"""
    industries = {
        'tech': {
            'name': 'Technology & Software',
            'roles': ['dev', 'cto', 'pm', 'ceo'],
            'topics': ['AI/ML', 'Cloud', 'DevOps', 'Security', 'Architecture', 'Best Practices']
        },
        'finance': {
            'name': 'Finance & Banking',
            'roles': ['ceo', 'finance', 'ops', 'cto'],
            'topics': ['Fintech', 'Compliance', 'Risk Management', 'Trading', 'Blockchain', 'Market Trends']
        },
        'healthcare': {
            'name': 'Healthcare & Pharma',
            'roles': ['ceo', 'cto', 'ops', 'marketing'],
            'topics': ['Telemedicine', 'Regulations', 'Patient Care', 'Innovation', 'Research', 'Digital Health']
        },
        'crypto': {
            'name': 'Cryptocurrency & Web3',
            'roles': ['dev', 'cto', 'ceo', 'marketing'],
            'topics': ['Smart Contracts', 'DeFi', 'Tokenomics', 'Security', 'Regulations', 'Market Analysis']
        },
        'saas': {
            'name': 'SaaS & Startups',
            'roles': ['ceo', 'pm', 'marketing', 'cto'],
            'topics': ['Product Launch', 'Growth Hacking', 'Fundraising', 'MVP', 'Customer Success', 'Scaling']
        },
        'ecommerce': {
            'name': 'E-Commerce & Retail',
            'roles': ['ceo', 'marketing', 'ops', 'pm'],
            'topics': ['Supply Chain', 'Customer Experience', 'Conversion Rate', 'Trends', 'Personalization', 'Analytics']
        }
    }
    return jsonify(industries)

@app.route('/api/roles', methods=['GET'])
def get_roles():
    """Get list of professional roles for premium content personalization"""
    roles = {
        'ceo': {'title': 'CEO / Founder', 'focus': 'Strategy, Growth, Vision'},
        'cto': {'title': 'CTO / VP Engineering', 'focus': 'Technical, Architecture, Innovation'},
        'dev': {'title': 'Software Developer', 'focus': 'Code, Best Practices, Tools'},
        'pm': {'title': 'Product Manager', 'focus': 'User Experience, Roadmap, Metrics'},
        'hr': {'title': 'HR / People Ops', 'focus': 'Culture, Hiring, Engagement'},
        'finance': {'title': 'Finance / CFO', 'focus': 'Budget, Analytics, Growth'},
        'ops': {'title': 'Operations', 'focus': 'Efficiency, Processes, Scaling'},
        'marketing': {'title': 'Marketing / Growth', 'focus': 'Campaigns, Analytics, Engagement'},
        'sales': {'title': 'Sales / BD', 'focus': 'Deals, Relationships, Growth'}
    }
    return jsonify(roles)

@app.route('/api/generate-preview-premium', methods=['POST'])
@require_auth
def generate_preview_premium():
    """DEPRECATED — use /api/generate-preview instead (includes grounding system).

    This endpoint previously ran a separate, ungrounded generation pipeline.
    It is kept as a stub so any stale client requests get a clear error instead
    of a 404.
    """
    return jsonify({
        'success': False,
        'message': 'This endpoint is deprecated. Use /api/generate-preview instead.',
        'deprecated': True,
    }), 410

@app.route('/api/enterprise-stats', methods=['GET'])
@require_auth
def get_enterprise_stats():
    """Get enhanced analytics for premium users"""
    try:
        user_id = get_current_user_id()
        posts = _db_list_posts(user_id, limit=200)
        if not posts:
            posts = [
                row for row in _read_json_list(POSTS_PATH)
                if str(row.get('user_id') or '').strip() == str(user_id)
            ]

        scheduled_posts = _db_list_scheduled_posts(user_id)
        if not scheduled_posts:
            scheduled_posts = [
                row for row in _read_json_list(SCHEDULED_POSTS_PATH)
                if str(row.get('user_id') or '').strip() == str(user_id)
            ]
        analytics = _calculate_real_analytics(posts, scheduled_posts)
        total_posts = analytics['total_posts']
        posted = analytics['posted_count']
        scheduled = analytics['scheduled_count']
        
        return jsonify({
            'total_posts': total_posts,
            'posted_count': posted,
            'scheduled_count': scheduled,
            'draft_count': total_posts - posted - scheduled,
            'engagement_rate': analytics.get('avg_engagement_rate'),
            'impressions': analytics.get('total_tracked_impressions', 0),
            'tracked_posts_count': analytics.get('tracked_posts_count', 0),
            'followers_gained': None
        })
    except Exception as e:
        logger.exception(f"Failed to get stats: {e}")
        return _safe_api_error('Request failed', e, 400)

# ─────────────────────────────────────────────────────────────────────────────
# STYLE CLONE
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/api/style', methods=['GET'])
@require_auth
def get_style():
    """Return saved style samples and analysed traits for the current user."""
    try:
        user_id = get_current_user_id()
        blob = _ensure_user_feature_blob(user_id)
        return jsonify({'success': True, 'style': blob.get('style_clone') or {}})
    except Exception as e:
        logger.exception('get_style failed: %s', e)
        return _safe_api_error('Request failed', e, 400)


@app.route('/api/style/save', methods=['POST'])
@require_auth
def save_style_samples():
    """Save 2-15 LinkedIn writing samples and auto-analyse the writing fingerprint."""
    try:
        user_id = get_current_user_id()
        data = request.get_json() or {}
        samples = data.get('samples') or []
        if not isinstance(samples, list):
            samples = [samples]
        samples = [s.strip() for s in samples if isinstance(s, str) and s.strip()]
        if len(samples) < 2:
            return jsonify({'success': False, 'message': 'Provide at least 2 writing samples.'}), 400
        samples = samples[:15]

        config_obj = load_config(user_id)
        ai = _build_platform_ai_provider()

        samples_text = "\n\n---\n\n".join(f"Sample {i+1}:\n{s}" for i, s in enumerate(samples))
        analysis_prompt = f"""Study these {len(samples)} LinkedIn posts written by the same person. Extract their unique writing fingerprint.

{samples_text}

Return a JSON object with EXACTLY these keys:
{{
  "avg_sentence_length": "short / medium / long",
  "paragraph_style": "e.g. single-line breaks / 2-3 sentence blocks",
  "opening_style": "e.g. Bold statement / Question / Personal story / Statistic",
  "closing_style": "e.g. Open question / Direct CTA / Reflection",
  "tone": "e.g. Direct and confident / Warm and personal / Analytical",
  "emoji_usage": "none / rare / moderate / frequent",
  "signature_phrases": ["phrase1", "phrase2", "phrase3"],
  "vocabulary_level": "simple / mixed / sophisticated",
  "post_structure": "one clear structural pattern observed",
  "style_summary": "One sentence describing this person's unique LinkedIn voice"
}}

Output ONLY valid JSON. No prose, no markdown fences."""

        result = ai.generate(analysis_prompt, max_tokens=600, task='analysis')
        raw = (result.get('text') or '').strip()
        if raw.startswith('```'):
            raw = raw.split('```')[1]
            if raw.startswith('json'):
                raw = raw[4:]
            raw = raw.strip()
        try:
            traits = json.loads(raw)
        except Exception:
            traits = {'style_summary': 'Style saved. Analysis unavailable — your voice will still be applied during generation.'}

        style_data = {
            'samples': samples,
            'traits': traits,
            'updated_at': datetime.now().isoformat(),
            'enabled': True,
        }
        blob = _ensure_user_feature_blob(user_id)
        blob['style_clone'] = style_data
        _save_user_feature_blob(user_id, blob)
        return jsonify({'success': True, 'style': style_data})
    except Exception as e:
        logger.exception('save_style_samples failed: %s', e)
        return _safe_api_error('Request failed', e, 400)


@app.route('/api/style/toggle', methods=['POST'])
@require_auth
def toggle_style_clone():
    """Enable or disable style clone for generation."""
    try:
        user_id = get_current_user_id()
        data = request.get_json() or {}
        enabled = bool(data.get('enabled', True))
        blob = _ensure_user_feature_blob(user_id)
        style_data = blob.get('style_clone') or {}
        style_data['enabled'] = enabled
        blob['style_clone'] = style_data
        _save_user_feature_blob(user_id, blob)
        return jsonify({'success': True, 'enabled': enabled})
    except Exception as e:
        return _safe_api_error('Request failed', e, 400)


# ─────────────────────────────────────────────────────────────────────────────
# CONTENT REPURPOSE PIPELINE
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/api/repurpose', methods=['POST'])
@require_auth
def repurpose_content():
    """Extract key insights from a URL or pasted text and produce 3 distinct LinkedIn post variants."""
    try:
        user_id = get_current_user_id()
        _rp_plan = _get_effective_plan(user_id)
        if not _get_plan_limits(_rp_plan).get('repurpose', False):
            return jsonify({
                'success': False,
                'upgrade_required': True,
                'message': 'Content repurposing is available on the Starter plan and above. Upgrade to unlock this feature.'
            }), 403
        data = request.get_json() or {}
        source_type = data.get('source_type', 'text')
        source = (data.get('source') or '').strip()
        industry = (data.get('industry') or 'technology').strip()
        role = (data.get('role') or 'professional').strip()
        tone = (data.get('tone') or 'professional').strip()

        if not source:
            return jsonify({'success': False, 'message': 'No source content provided.'}), 400

        raw_text = source
        page_title = ''

        if source_type == 'url':
            try:
                import urllib.request as _ur
                req = _ur.Request(source, headers={'User-Agent': 'Mozilla/5.0 (compatible; VelankBot/1.0)'})
                with _ur.urlopen(req, timeout=12) as resp:
                    html_bytes = resp.read(120_000)
                html_str = html_bytes.decode('utf-8', errors='replace')
                title_m = re.search(r'<title[^>]*>(.*?)</title>', html_str, re.I | re.S)
                if title_m:
                    page_title = re.sub(r'<[^>]+>', '', title_m.group(1)).strip()
                html_str = re.sub(r'<(script|style|nav|header|footer|aside)[^>]*>.*?</\1>', ' ', html_str, flags=re.I | re.S)
                raw_text = re.sub(r'<[^>]+>', ' ', html_str)
                raw_text = re.sub(r'\s+', ' ', raw_text).strip()[:8000]
            except Exception as fetch_err:
                logger.warning('URL fetch failed: %s', fetch_err)
                return jsonify({'success': False, 'message': f'Could not fetch URL: {fetch_err}'}), 400

        config_obj = load_config(user_id)
        ai = _build_platform_ai_provider()

        extract_prompt = f"""Extract exactly 5 specific, valuable insights from this content. Return ONLY a JSON array of 5 strings (each under 20 words). No prose.

CONTENT:
{raw_text[:5000]}

Output: ["insight 1", "insight 2", "insight 3", "insight 4", "insight 5"]"""

        extract_result = ai.generate(extract_prompt, max_tokens=300, task='analysis')
        raw_points = (extract_result.get('text') or '').strip()
        if raw_points.startswith('```'):
            raw_points = raw_points.split('```')[1]
            if raw_points.startswith('json'):
                raw_points = raw_points[4:]
        try:
            key_points = json.loads(raw_points.strip())
            if not isinstance(key_points, list):
                key_points = []
        except Exception:
            key_points = []

        _BANNED_R = (
            "In today's fast-paced world, game-changer, paradigm shift, leverage, synergy, "
            "cutting-edge, best practices, move the needle, seamlessly, robust, transformative, "
            "empower, innovative solution, value-add, at the end of the day"
        )

        variant_specs = [
            ("Data & Insight", "Lead with the most surprising or specific insight. Be concrete, cite what you found. End with a punchy standalone statement."),
            ("Personal Takeaway", f"Write in first person as a {role}. Share what YOU personally took from this. Make it a genuine reflection, not generic. Start mid-thought."),
            ("Contrarian Take", f"Challenge the obvious reading of this. What are most {role}s getting wrong? Make one bold, well-reasoned claim. Invite debate."),
        ]

        variants = []
        for angle_name, angle_instruction in variant_specs:
            points_text = '\n'.join(f'- {p}' for p in key_points) if key_points else raw_text[:1500]
            gen_prompt = f"""[DOMAIN LOCK] You are a {role} in the {industry} industry writing a LinkedIn post.

SOURCE KEY POINTS:
{points_text}

ANGLE: {angle_name}
INSTRUCTION: {angle_instruction}

STRICT RULES:
- 130-200 words, flowing prose, short paragraphs
- No markdown (no **, no ***)
- Do NOT open with "I" as the literal first character
- No banned phrases: {_BANNED_R}
- End with 3-4 relevant hashtags on the final line
- Output ONLY the post text"""

            gen_result = ai.generate(gen_prompt, max_tokens=400, task='repurpose')
            full_text = gen_result.get('text') or ''
            post_body = clean_linkedin_body(remove_hashtags_from_body(full_text))
            hashtags = normalize_hashtags(HASHTAG_RE.findall(full_text))
            variants.append({'angle': angle_name, 'text': post_body, 'hashtags': hashtags[:4]})

        return jsonify({
            'success': True,
            'title': page_title or 'Repurposed Content',
            'key_points': key_points,
            'variants': variants,
            'industry': industry,
            'role': role,
        })
    except Exception as e:
        logger.exception('repurpose_content failed: %s', e)
        return _safe_api_error('Request failed', e, 400)


# ─────────────────────────────────────────────────────────────────────────────
# BEST TIME TO POST
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/api/best-time', methods=['GET'])
@require_auth
def get_best_time():
    """Analyse published post history + global LinkedIn benchmarks to surface optimal slots."""
    try:
        user_id = get_current_user_id()
        _bt_plan = _get_effective_plan(user_id)
        if not _get_plan_limits(_bt_plan).get('best_time', False):
            return jsonify({
                'success': False,
                'upgrade_required': True,
                'message': 'Best time to post is available on the Creator plan and above. Upgrade to unlock this feature.'
            }), 403
        posts = _db_list_posts(user_id, limit=200)
        if not posts:
            posts = [
                row for row in _read_json_list(POSTS_PATH)
                if str(row.get('user_id') or '').strip() == str(user_id)
                and row.get('posted')
            ]

        # LinkedIn global engagement benchmarks (0–100 score per day/hour)
        GLOBAL_DAY = [72, 88, 92, 90, 80, 35, 28]  # Mon-Sun
        GLOBAL_HOUR = {7: 60, 8: 82, 9: 90, 10: 88, 11: 75, 12: 78, 13: 65,
                       14: 58, 15: 55, 16: 60, 17: 72, 18: 68, 19: 55, 20: 42}
        DAY_NAMES = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

        user_day = [0] * 7
        user_hour: dict[int, int] = {}
        for post in posts:
            ts = post.get('created_at') or post.get('scheduled_for') or ''
            try:
                dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                user_day[dt.weekday()] += 1
                h = dt.hour
                user_hour[h] = user_hour.get(h, 0) + 1
            except Exception:
                pass

        total = sum(user_day)
        has_data = total >= 3

        if has_data:
            mx_d = max(user_day) or 1
            mx_h = max(user_hour.values()) if user_hour else 1
            blended_day = [round(0.65 * GLOBAL_DAY[i] + 0.35 * round(user_day[i] / mx_d * 100)) for i in range(7)]
            blended_hour = {h: round(0.65 * base + 0.35 * round(user_hour.get(h, 0) / mx_h * 100))
                            for h, base in GLOBAL_HOUR.items()}
        else:
            blended_day = list(GLOBAL_DAY)
            blended_hour = dict(GLOBAL_HOUR)

        def fmt_h(h: int) -> str:
            s = 'AM' if h < 12 else 'PM'
            return f"{h % 12 or 12}:00 {s}"

        sorted_days = sorted(range(7), key=lambda i: blended_day[i], reverse=True)
        sorted_hours = sorted(blended_hour, key=lambda h: blended_hour[h], reverse=True)

        top_slots = [
            {
                'day': DAY_NAMES[sorted_days[0]],
                'time': f'{fmt_h(sorted_hours[0])}–{fmt_h(sorted_hours[0]+1)}',
                'score': blended_day[sorted_days[0]],
                'reason': 'Your top publishing day at peak engagement hour' if has_data else 'Globally highest LinkedIn traffic window',
            },
            {
                'day': DAY_NAMES[sorted_days[1]],
                'time': f'{fmt_h(sorted_hours[1])}–{fmt_h(sorted_hours[1]+1)}',
                'score': blended_day[sorted_days[1]],
                'reason': 'Second strongest window for your audience' if has_data else 'Top-2 global LinkedIn day',
            },
            {
                'day': 'Thursday',
                'time': '12:00 PM–1:00 PM',
                'score': blended_day[3],
                'reason': 'Lunch-hour scroll spike — consistent across all industries',
            },
        ]

        return jsonify({
            'success': True,
            'has_user_data': has_data,
            'total_analyzed_posts': total,
            'day_scores': [{'day': DAY_NAMES[i], 'score': blended_day[i]} for i in range(7)],
            'hour_scores': [{'hour': h, 'label': fmt_h(h), 'score': blended_hour[h]} for h in sorted(blended_hour)],
            'top_slots': top_slots,
            'note': f'Based on your {total} published posts + global LinkedIn engagement data.' if has_data else 'Based on global LinkedIn research. Publish more posts to personalise.',
        })
    except Exception as e:
        logger.exception('get_best_time failed: %s', e)
        return _safe_api_error('Request failed', e, 400)


if __name__ == '__main__':
    missing_auth = []
    if not (os.getenv('SUPABASE_URL') or '').strip():
        missing_auth.append('SUPABASE_URL')
    if not ((os.getenv('SUPABASE_ANON_KEY') or '').strip() or (os.getenv('SUPABASE_KEY') or '').strip() or (os.getenv('SUPABASE_SERVICE_ROLE_KEY') or '').strip()):
        missing_auth.append('SUPABASE_ANON_KEY|SUPABASE_KEY|SUPABASE_SERVICE_ROLE_KEY')
    if missing_auth:
        logger.error("Auth misconfigured. Missing: %s", ', '.join(missing_auth))

    # Start background services once for local/direct runs.
    ensure_background_services_started()
    
    # Disable debug mode in production
    debug_mode = os.getenv('FLASK_ENV') != 'production'
    app.run(
        debug=debug_mode,
        use_reloader=False,
        port=int(os.getenv('PORT', 5050)),
        host='0.0.0.0'
    )
