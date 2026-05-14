"""Admin panel Blueprint — extracted from app.py monolith (P1-6).

All /admin/* and /api/admin/* routes live here.  The factory function
``create_admin_blueprint`` receives external dependencies (limiter, logger,
data_dir) so the module never imports from app.py, avoiding circular deps.
"""

from __future__ import annotations

import calendar
import csv
import hmac
import io
import json
import logging
import os
import threading
import time
from datetime import datetime, timedelta
from functools import wraps
from pathlib import Path
from uuid import UUID

from dotenv import dotenv_values
from flask import (
    Blueprint,
    Response,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

# ── Auth module (no circular dependency) ──────────────────────────────────────
from auth import (
    request_password_reset,
    supabase as auth_supabase,
)

# ---------------------------------------------------------------------------
# Shared tiny utilities (duplicated locally to avoid importing from app.py)
# ---------------------------------------------------------------------------

_logger = logging.getLogger('velank')


def _safe_api_error(user_message: str, exc: Exception = None, status: int = 500) -> tuple:
    if exc is not None:
        _logger.exception('%s: %s', user_message, exc)
    return jsonify({'success': False, 'message': user_message}), status


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
        '1m': ('1_month', 1), '1_month': ('1_month', 1),
        'monthly': ('1_month', 1), 'pro': ('1_month', 1),
        '3m': ('3_month', 3), '3_month': ('3_month', 3), 'quarterly': ('3_month', 3),
        '12m': ('12_month', 12), '12_month': ('12_month', 12),
        'yearly': ('12_month', 12), 'annual': ('12_month', 12), 'agency': ('12_month', 12),
    }
    return plan_map.get(value)


def _parse_iso_utc(value: str):
    text = str(value or '').strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace('Z', '+00:00'))
        return parsed
    except Exception:
        return None


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
        _logger.warning("Failed to read list JSON file: %s", file_path)
        return []


def _write_json_list(file_path: str, items: list) -> None:
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    payload = items if isinstance(items, list) else []
    tmp_path = file_path + '.tmp'
    with open(tmp_path, 'w') as fh:
        json.dump(payload, fh, indent=2)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp_path, file_path)


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def create_admin_blueprint(*, limiter, logger, data_dir: str):
    """Return the admin Blueprint with all routes and helpers.

    Parameters
    ----------
    limiter : flask_limiter.Limiter
        The shared rate-limiter instance (already init_app'd on the Flask app).
    logger : logging.Logger
        Application logger.
    data_dir : str
        Absolute path to the ``data/`` directory (for legacy JSON migration).
    """
    admin_bp = Blueprint('admin', __name__)

    POSTS_PATH = os.path.join(data_dir, 'posts.json')
    SCHEDULED_POSTS_PATH = os.path.join(data_dir, 'scheduled_posts.json')

    # ── Admin brute-force tracking ────────────────────────────────────────
    _ADMIN_LOGIN_ATTEMPTS: dict[str, list] = {}
    _ADMIN_LOCKOUT_WINDOW = 300
    _ADMIN_LOCKOUT_MAX = 5

    # ── Admin session ─────────────────────────────────────────────────────
    _ADMIN_SESSION_MAX_AGE = 3600

    def _admin_session_valid() -> bool:
        if not session.get('is_admin'):
            return False
        login_at = session.get('admin_login_at', 0)
        if login_at and (time.time() - login_at) > _ADMIN_SESSION_MAX_AGE:
            session.pop('is_admin', None)
            session.pop('admin_email', None)
            session.pop('admin_login_at', None)
            return False
        return True

    def require_admin_session(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if not _admin_session_valid():
                return redirect(url_for('admin.admin_login_page'))
            return f(*args, **kwargs)
        return wrapper

    def require_admin_api(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if not _admin_session_valid():
                return jsonify({'success': False, 'message': 'Admin authentication required'}), 401
            return f(*args, **kwargs)
        return wrapper

    # ── Admin users cache ─────────────────────────────────────────────────
    _CACHE_TTL = max(30, int(os.getenv('ADMIN_USERS_CACHE_TTL_SEC', '300') or 300))
    _CACHE_LOCK = threading.Lock()
    _CACHE: dict = {'users': [], 'updated_at': 0.0, 'stale': False, 'warning': ''}

    def _set_cache(users: list, stale: bool = False, warning: str = '') -> None:
        with _CACHE_LOCK:
            _CACHE['users'] = users if isinstance(users, list) else []
            _CACHE['updated_at'] = time.time()
            _CACHE['stale'] = bool(stale)
            _CACHE['warning'] = str(warning or '').strip()

    def _get_cache_meta() -> dict:
        with _CACHE_LOCK:
            return {
                'users': list(_CACHE.get('users') or []),
                'updated_at': float(_CACHE.get('updated_at') or 0.0),
                'stale': bool(_CACHE.get('stale')),
                'warning': str(_CACHE.get('warning') or ''),
            }

    def _list_auth_users(page: int = 1, per_page: int = 1000):
        if not auth_supabase:
            meta = _get_cache_meta()
            if meta['users']:
                _set_cache(meta['users'], stale=True, warning='Supabase auth unavailable. Showing cached user list.')
                return meta['users']
            _set_cache([], stale=True, warning='Supabase authentication is not configured.')
            return []
        try:
            response = auth_supabase.auth.admin.list_users(page=page, per_page=per_page)
            if isinstance(response, list):
                _set_cache(response, stale=False, warning='')
                return response
            users = getattr(response, 'users', None)
            if users is None and isinstance(response, dict):
                users = response.get('users', [])
            users = users or []
            _set_cache(users, stale=False, warning='')
            return users
        except Exception as e:
            logger.error("Admin list users failed: %s", e)
            meta = _get_cache_meta()
            if meta['users']:
                age_sec = int(max(0, time.time() - meta['updated_at']))
                warning = f'Live user list fetch failed. Showing cached results ({age_sec}s old).'
                _set_cache(meta['users'], stale=True, warning=warning)
                return meta['users']
            _set_cache([], stale=True, warning='Unable to load users from authentication provider.')
            return []

    def _user_to_admin_row(user_obj, subscription_map=None):
        subscription_map = subscription_map or {}
        metadata = getattr(user_obj, 'user_metadata', {}) or {}
        user_id = str(getattr(user_obj, 'id', ''))
        email = getattr(user_obj, 'email', '')
        created_at = getattr(user_obj, 'created_at', None)
        confirmed_at = getattr(user_obj, 'email_confirmed_at', None)
        last_sign_in_at = getattr(user_obj, 'last_sign_in_at', None)
        banned_until = getattr(user_obj, 'banned_until', None)
        is_active = not bool(banned_until)
        is_verified = bool(confirmed_at)
        sub = subscription_map.get(user_id, {})
        plan = (sub.get('plan') or 'free').title()
        subscription_status = str(sub.get('status') or 'inactive').lower()
        period_start = sub.get('current_period_start')
        period_end = sub.get('current_period_end')
        cancel_at_period_end = bool(sub.get('cancel_at_period_end'))
        return {
            'id': user_id, 'email': email,
            'first_name': metadata.get('first_name', ''),
            'last_name': metadata.get('last_name', ''),
            'country': metadata.get('country', ''),
            'signup_date': created_at, 'verified': is_verified,
            'active': is_active, 'status': 'Active' if is_active else 'Inactive',
            'last_sign_in_at': last_sign_in_at,
            'plan': plan, 'subscription_status': subscription_status,
            'subscription_period_start': period_start,
            'subscription_period_end': period_end,
            'cancel_at_period_end': cancel_at_period_end,
        }

    def _extract_list_users_response(response):
        if isinstance(response, list):
            return response, None
        users = getattr(response, 'users', None)
        if users is None and isinstance(response, dict):
            users = response.get('users', [])
        if users is None:
            users = []
        total = getattr(response, 'total', None)
        if total is None and isinstance(response, dict):
            total = response.get('total')
        return users or [], total

    def _list_all_auth_users(max_users: int = 5000, per_page: int = 1000):
        if not auth_supabase:
            meta = _get_cache_meta()
            return meta['users']
        try:
            all_users = []
            page = 1
            while len(all_users) < max_users:
                response = auth_supabase.auth.admin.list_users(page=page, per_page=per_page)
                users, _ = _extract_list_users_response(response)
                if not users:
                    break
                all_users.extend(users)
                if len(users) < per_page:
                    break
                page += 1
            _set_cache(all_users, stale=False, warning='')
            return all_users
        except Exception as e:
            logger.error('Admin list all users failed: %s', e)
            meta = _get_cache_meta()
            if meta['users']:
                _set_cache(meta['users'], stale=True, warning='Live user list fetch failed. Showing cached results.')
                return meta['users']
            _set_cache([], stale=True, warning='Unable to load users from authentication provider.')
            return []

    def _log_action(action: str, target_user_id: str = '', details: dict = None):
        details = details or {}
        try:
            logger.info("ADMIN_ACTION action=%s admin=%s target=%s details=%s",
                        action, session.get('admin_email', ''), target_user_id, details)
        except Exception:
            pass
        if not auth_supabase:
            return
        try:
            auth_supabase.table('system_logs').insert({
                'level': 'info',
                'message': f'admin:{action}',
                'request_path': request.path,
                'request_method': request.method,
                'metadata': {
                    'admin_email': session.get('admin_email', ''),
                    'target_user_id': target_user_id,
                    'details': details,
                },
            }).execute()
        except Exception as e:
            logger.debug("Admin system log insert skipped/failed: %s", e)

    def _find_auth_user_by_id(user_id: str):
        users = _list_auth_users()
        for user in users:
            if str(getattr(user, 'id', '')) == str(user_id):
                return user
        if auth_supabase:
            try:
                response = auth_supabase.auth.admin.get_user_by_id(user_id)
                user_obj = getattr(response, 'user', None)
                if user_obj is None and isinstance(response, dict):
                    user_obj = response.get('user')
                if user_obj:
                    return user_obj
            except Exception as e:
                logger.error("Admin get_user_by_id failed: %s", e)
        return None

    def _is_valid_uuid(value: str) -> bool:
        try:
            UUID(str(value))
            return True
        except Exception:
            return False

    def _dict_diff(before: dict, after: dict) -> dict:
        before = before or {}
        after = after or {}
        keys = set(before.keys()) | set(after.keys())
        changes = {}
        for key in sorted(keys):
            if before.get(key) != after.get(key):
                changes[key] = {'before': before.get(key), 'after': after.get(key)}
        return changes

    def _get_feature_flag_row(flag_key: str):
        if not auth_supabase:
            return None
        try:
            rows = auth_supabase.table('feature_flags').select('*').eq('key', flag_key).limit(1).execute().data or []
            return rows[0] if rows else None
        except Exception as e:
            logger.error('Feature flag read failed for %s: %s', flag_key, e)
            return None

    def _set_feature_flag(flag_key: str, enabled: bool, config: dict | None = None, name: str = ''):
        if not auth_supabase:
            return False
        now = datetime.utcnow().isoformat() + 'Z'
        row = {
            'key': flag_key,
            'name': name or flag_key.replace('_', ' ').title(),
            'description': 'Admin incident control',
            'is_enabled_globally': bool(enabled),
            'rollout_percentage': 100 if enabled else 0,
            'config': config or {},
            'updated_at': now,
        }
        try:
            auth_supabase.table('feature_flags').upsert(row, on_conflict='key').execute()
            return True
        except Exception as e:
            logger.error('Feature flag upsert failed for %s: %s', flag_key, e)
            return False

    def _extract_user_email(user_obj) -> str:
        if isinstance(user_obj, dict):
            return str(user_obj.get('email') or '').strip().lower()
        return str(getattr(user_obj, 'email', '') or '').strip().lower()

    def _extract_user_metadata(user_obj) -> dict:
        if isinstance(user_obj, dict):
            return user_obj.get('user_metadata', {}) or {}
        return getattr(user_obj, 'user_metadata', {}) or {}

    def _collect_target_emails(scope: str = 'all') -> list[str]:
        emails = []
        for user in _list_all_auth_users(max_users=20000, per_page=1000):
            user_obj = user if isinstance(user, dict) else (getattr(user, 'user', None) or user)
            email = _extract_user_email(user_obj)
            if not email:
                continue
            md = _extract_user_metadata(user_obj)
            if scope == 'active' and md.get('is_active') is False:
                continue
            if scope == 'verified':
                if isinstance(user_obj, dict):
                    verified = bool(user_obj.get('email_confirmed_at') or user_obj.get('confirmed_at'))
                else:
                    verified = bool(getattr(user_obj, 'email_confirmed_at', None) or getattr(user_obj, 'confirmed_at', None))
                if not verified:
                    continue
            emails.append(email)
        return sorted(set(emails))

    def _get_admin_credentials():
        env_email = os.getenv('ADMIN_EMAIL', '').strip().lower()
        env_password = os.getenv('ADMIN_PASSWORD', '').strip()
        if env_email and env_password:
            return {'email': env_email, 'password': env_password}
        try:
            file_values = dotenv_values(Path(data_dir).parent / '.env')
        except Exception:
            file_values = {}
        file_email = str(file_values.get('ADMIN_EMAIL') or '').strip().lower()
        file_password = str(file_values.get('ADMIN_PASSWORD') or '').strip()
        return {'email': env_email or file_email, 'password': env_password or file_password}

    # =====================================================================
    # ADMIN ROUTES
    # =====================================================================

    @admin_bp.route('/admin/login', methods=['GET', 'POST'])
    @limiter.limit("5 per minute", methods=["POST"])
    def admin_login_page():
        """Admin login page with brute-force lockout."""
        if request.method == 'GET':
            return render_template('admin_login.html')

        data = request.get_json(silent=True) or request.form or {}
        email = (data.get('email') or '').strip().lower()
        password = (data.get('password') or '').strip()
        client_ip = request.headers.get('X-Forwarded-For', request.remote_addr or '0.0.0.0').split(',')[0].strip()

        now_ts = time.time()
        attempts = _ADMIN_LOGIN_ATTEMPTS.get(client_ip, [])
        attempts = [t for t in attempts if now_ts - t < _ADMIN_LOCKOUT_WINDOW]
        _ADMIN_LOGIN_ATTEMPTS[client_ip] = attempts

        if len(attempts) >= _ADMIN_LOCKOUT_MAX:
            remaining = int(_ADMIN_LOCKOUT_WINDOW - (now_ts - attempts[0]))
            logger.warning('Admin login locked out for IP %s (%d attempts)', client_ip, len(attempts))
            return jsonify({
                'success': False,
                'message': f'Too many failed attempts. Try again in {remaining} seconds.',
            }), 429

        creds = _get_admin_credentials()
        if not creds['email'] or not creds['password']:
            return jsonify({'success': False, 'message': 'Admin credentials are not configured'}), 500

        if hmac.compare_digest(email, creds['email']) and hmac.compare_digest(password, creds['password']):
            session['is_admin'] = True
            session['admin_email'] = email
            session['admin_login_at'] = time.time()
            _ADMIN_LOGIN_ATTEMPTS.pop(client_ip, None)
            _log_action('admin_login', '', {'ip': client_ip, 'email': email, 'success': True})
            return jsonify({'success': True, 'redirect': '/admin/dashboard'})

        attempts.append(now_ts)
        _ADMIN_LOGIN_ATTEMPTS[client_ip] = attempts
        _log_action('admin_login_failed', '', {'ip': client_ip, 'email': email, 'attempts': len(attempts)})
        return jsonify({'success': False, 'message': 'Invalid admin credentials'}), 401

    @admin_bp.route('/admin/logout')
    def admin_logout_page():
        session.pop('is_admin', None)
        session.pop('admin_email', None)
        return redirect(url_for('admin.admin_login_page'))

    @admin_bp.route('/admin/dashboard')
    @require_admin_session
    def admin_dashboard_page():
        supabase_url = (os.getenv('SUPABASE_URL') or '').strip().rstrip('/')
        return render_template('admin_dashboard.html',
                               admin_email=session.get('admin_email', ''),
                               supabase_url=supabase_url)

    # ── Overview ──────────────────────────────────────────────────────────

    @admin_bp.route('/api/admin/overview', methods=['GET'])
    @require_admin_api
    def admin_overview():
        users = _list_auth_users()
        cache_meta = _get_cache_meta()
        total_users = len(users)
        verified_users = 0
        active_users = 0
        now = datetime.utcnow()

        for user in users:
            confirmed_at = getattr(user, 'email_confirmed_at', None)
            banned_until = getattr(user, 'banned_until', None)
            last_sign_in = getattr(user, 'last_sign_in_at', None)
            if confirmed_at:
                verified_users += 1
            if not banned_until and last_sign_in:
                try:
                    last_dt = datetime.fromisoformat(str(last_sign_in).replace('Z', '+00:00')).replace(tzinfo=None)
                    if (now - last_dt).days <= 30:
                        active_users += 1
                except Exception:
                    active_users += 1

        range_raw = str(request.args.get('range') or '7d').strip().lower()
        if range_raw not in {'24h', '7d', '30d', '90d'}:
            range_raw = '7d'

        total_posts = 0
        posts_today = 0
        failed_posts = 0

        if range_raw == '24h':
            chart_labels = [(now - timedelta(hours=i)).strftime('%H:00') for i in range(23, -1, -1)]
            chart_values = [0 for _ in range(24)]
        else:
            days = {'7d': 7, '30d': 30, '90d': 90}[range_raw]
            chart_labels = [(now - timedelta(days=i)).strftime('%b %d') for i in range(days - 1, -1, -1)]
            chart_values = [0 for _ in range(days)]

        try:
            if auth_supabase:
                posts_res = auth_supabase.table('posts').select('created_at,status').execute()
                posts_data = posts_res.data or []
                total_posts = len(posts_data)
                today_date = now.date()
                for row in posts_data:
                    status = (row.get('status') or '').lower()
                    created_at = row.get('created_at')
                    if status == 'failed':
                        failed_posts += 1
                    if not created_at:
                        continue
                    try:
                        created_dt = datetime.fromisoformat(str(created_at).replace('Z', '+00:00')).replace(tzinfo=None)
                        if created_dt.date() == today_date:
                            posts_today += 1
                        if range_raw == '24h':
                            diff_hours = int((now - created_dt).total_seconds() // 3600)
                            if 0 <= diff_hours <= 23:
                                chart_values[23 - diff_hours] += 1
                        else:
                            diff_days = (now.date() - created_dt.date()).days
                            max_days = len(chart_values)
                            if 0 <= diff_days < max_days:
                                chart_values[max_days - 1 - diff_days] += 1
                    except Exception:
                        continue
        except Exception as e:
            logger.error("Admin overview post stats failed: %s", e)

        # ── Plan distribution + revenue estimate ──────────────────────────
        plan_distribution = {'free': 0, '1_month': 0, '3_month': 0, '12_month': 0}
        revenue_estimate_inr = 0
        avg_posts_per_user = 0.0
        top_referrers = []
        try:
            if auth_supabase:
                subs_res = auth_supabase.table('subscriptions').select('plan,status').execute()
                for row in (subs_res.data or []):
                    plan_key = str(row.get('plan') or 'free').lower()
                    # Normalise legacy names
                    if plan_key in ('pro', '1m', 'monthly'):
                        plan_key = '1_month'
                    elif plan_key in ('3m', 'quarterly'):
                        plan_key = '3_month'
                    elif plan_key in ('12m', 'yearly', 'annual', 'agency'):
                        plan_key = '12_month'
                    if plan_key not in plan_distribution:
                        plan_key = 'free'
                    if str(row.get('status') or '').lower() == 'active':
                        plan_distribution[plan_key] += 1
                price_map = {'1_month': 999, '3_month': 2499, '12_month': 8999}
                for plan_key, count in plan_distribution.items():
                    revenue_estimate_inr += price_map.get(plan_key, 0) * count
        except Exception as e:
            logger.error("Admin overview plan distribution failed: %s", e)

        try:
            if auth_supabase and total_users > 0:
                usage_res = auth_supabase.table('usage_monthly').select('posts_generated').execute()
                usage_rows = usage_res.data or []
                total_generated = sum(int(r.get('posts_generated') or 0) for r in usage_rows)
                avg_posts_per_user = round(total_generated / total_users, 1)
        except Exception as e:
            logger.error("Admin overview avg posts failed: %s", e)

        try:
            if auth_supabase:
                ref_res = auth_supabase.table('user_profiles').select(
                    'user_id,referral_count'
                ).gt('referral_count', 0).order('referral_count', desc=True).limit(5).execute()
                top_referrers = [
                    {'user_id': r.get('user_id'), 'referral_count': r.get('referral_count')}
                    for r in (ref_res.data or [])
                ]
        except Exception as e:
            logger.error("Admin overview referral stats failed: %s", e)

        return jsonify({
            'success': True,
            'warning': cache_meta.get('warning', ''),
            'stale_users': bool(cache_meta.get('stale')),
            'cards': {
                'total_users': total_users, 'verified_users': verified_users,
                'active_users': active_users, 'total_posts': total_posts,
                'posts_today': posts_today, 'failed_posts': failed_posts,
            },
            'charts': {
                'weekly_labels': chart_labels, 'weekly_posts': chart_values,
                'user_breakdown': [total_users, verified_users, active_users],
                'selected_range': range_raw,
            },
            'analytics': {
                'plan_distribution': plan_distribution,
                'revenue_estimate_inr': revenue_estimate_inr,
                'avg_posts_per_user': avg_posts_per_user,
                'top_referrers': top_referrers,
            },
        })

    # ── Users CRUD ────────────────────────────────────────────────────────

    @admin_bp.route('/api/admin/users', methods=['GET'])
    @require_admin_api
    def admin_users():
        try:
            page = max(1, int(request.args.get('page', 1)))
        except Exception:
            page = 1
        try:
            page_size = max(1, min(100, int(request.args.get('page_size', 10))))
        except Exception:
            page_size = 10
        sort_by = str(request.args.get('sort_by') or 'signup_desc').strip()
        active_filter = str(request.args.get('filter') or 'all').strip().lower()
        search_query = str(request.args.get('search') or '').strip().lower()
        filter_country = str(request.args.get('country') or '').strip().lower()
        filter_plan = str(request.args.get('plan') or '').strip().lower()
        filter_signup_from = str(request.args.get('signup_from') or '').strip()
        filter_signup_to = str(request.args.get('signup_to') or '').strip()

        users = _list_all_auth_users()
        user_ids = []
        for u in users:
            if isinstance(u, dict):
                u_obj = u
            else:
                u_obj = getattr(u, 'user', None) or u
            user_id = str(getattr(u_obj, 'id', '') or (u_obj.get('id') if isinstance(u_obj, dict) else ''))
            if user_id:
                user_ids.append(user_id)

        subscription_map = {}
        try:
            if auth_supabase and user_ids:
                subs = auth_supabase.table('subscriptions').select(
                    'user_id,plan,status,current_period_start,current_period_end,cancel_at_period_end'
                ).in_('user_id', user_ids).execute().data or []
                subscription_map = {str(row.get('user_id')): row for row in subs}
        except Exception as e:
            logger.error("Admin users subscription lookup failed: %s", e)

        filtered_users = []
        for u in users:
            if isinstance(u, dict):
                u_obj = u
            else:
                u_obj = getattr(u, 'user', None) or u
            md = (u_obj.get('user_metadata') if isinstance(u_obj, dict) else getattr(u_obj, 'user_metadata', {})) or {}
            if bool(md.get('soft_deleted')):
                continue
            row = _user_to_admin_row(u_obj, subscription_map)
            if active_filter == 'active' and not row.get('active'):
                continue
            if active_filter == 'verified' and not row.get('verified'):
                continue
            if active_filter == 'paid' and str(row.get('plan', '')).lower() == 'free':
                continue
            if search_query:
                haystack = ' '.join([
                    str(row.get('email', '')), str(row.get('first_name', '')), str(row.get('last_name', '')),
                    str(row.get('country', '')), str(row.get('plan', '')), str(row.get('subscription_status', ''))
                ]).lower()
                if search_query not in haystack:
                    continue
            if filter_country and filter_country not in str(row.get('country', '')).lower():
                continue
            if filter_plan and filter_plan not in str(row.get('plan', '')).lower():
                continue
            try:
                if filter_signup_from or filter_signup_to:
                    signup_date = row.get('signup_date')
                    if signup_date:
                        signup_dt = _parse_iso_utc(signup_date)
                        if signup_dt and filter_signup_from:
                            from_dt = datetime.fromisoformat(filter_signup_from)
                            if signup_dt.date() < from_dt.date():
                                continue
                        if signup_dt and filter_signup_to:
                            to_dt = datetime.fromisoformat(filter_signup_to)
                            if signup_dt.date() > to_dt.date():
                                continue
            except Exception as e:
                logger.debug("Date filter parse failed: %s", e)
            filtered_users.append(row)

        if sort_by == 'signup_asc':
            filtered_users.sort(key=lambda item: item.get('signup_date') or '')
        elif sort_by == 'name_asc':
            filtered_users.sort(key=lambda item: f"{item.get('first_name', '')} {item.get('last_name', '')}".strip().lower())
        elif sort_by == 'email_asc':
            filtered_users.sort(key=lambda item: str(item.get('email', '') or '').lower())
        elif sort_by == 'plan_asc':
            filtered_users.sort(key=lambda item: str(item.get('plan', '') or '').lower())
        else:
            filtered_users.sort(key=lambda item: item.get('signup_date') or '', reverse=True)

        total = len(filtered_users)
        start = (page - 1) * page_size
        rows = filtered_users[start:start + page_size]

        cache_meta = _get_cache_meta()
        auth_configured = bool(auth_supabase)
        return jsonify({
            'success': True,
            'users': rows,
            'total': total,
            'page': page,
            'page_size': page_size,
            'auth_configured': auth_configured,
            'stale_users': bool(cache_meta.get('stale')),
            'warning': cache_meta.get('warning', ''),
            'message': '' if auth_configured else 'Supabase authentication is not configured. Add SUPABASE_URL and SUPABASE_ANON_KEY (or SUPABASE_SERVICE_ROLE_KEY) in .env and restart the server.',
        })

    @admin_bp.route('/api/admin/users/create', methods=['POST'])
    @require_admin_api
    def admin_create_user():
        if not auth_supabase:
            return jsonify({'success': False, 'message': 'Supabase not configured'}), 500
        data = request.get_json() or {}
        email = str(data.get('email') or '').strip().lower()
        password = str(data.get('password') or '').strip()
        first_name = str(data.get('first_name') or '').strip()
        last_name = str(data.get('last_name') or '').strip()
        country = str(data.get('country') or '').strip()
        if '@' not in email:
            return jsonify({'success': False, 'message': 'Valid email is required'}), 400
        if len(password) < 8:
            return jsonify({'success': False, 'message': 'Password must be at least 8 characters'}), 400
        try:
            response = auth_supabase.auth.admin.create_user({
                'email': email, 'password': password, 'email_confirm': True,
                'user_metadata': {
                    'first_name': first_name, 'last_name': last_name,
                    'country': country, 'auth_provider': 'email',
                },
            })
            user_obj = getattr(response, 'user', None)
            if user_obj is None and isinstance(response, dict):
                user_obj = response.get('user')
            user_id = str(getattr(user_obj, 'id', '') or (user_obj.get('id') if isinstance(user_obj, dict) else ''))
            _log_action('create_user', user_id, {'email': email})
            return jsonify({'success': True, 'message': 'User created successfully', 'user_id': user_id, 'email': email})
        except Exception as e:
            logger.error("Admin create user failed: %s", e)
            return _safe_api_error('Failed to create user', e)

    @admin_bp.route('/api/admin/users/<user_id>', methods=['GET'])
    @require_admin_api
    def admin_user_details(user_id):
        selected = _find_auth_user_by_id(user_id)
        if not selected:
            return jsonify({'success': False, 'message': 'User not found'}), 404
        subscription_map = {}
        try:
            if auth_supabase:
                sub_row = auth_supabase.table('subscriptions').select(
                    'user_id,plan,status,current_period_start,current_period_end,cancel_at_period_end'
                ).eq('user_id', user_id).limit(1).execute().data or []
                if sub_row:
                    subscription_map = {str(user_id): sub_row[0]}
        except Exception as e:
            logger.error("Admin user details subscription lookup failed: %s", e)
        details = _user_to_admin_row(selected, subscription_map)
        posts = []
        analytics = {
            'total_posts': 0,
            'published_posts': 0,
            'scheduled_posts': 0,
            'failed_posts': 0,
            'posts_this_month': 0,
            'last_activity': None,
            'success_rate': 0.0,
            'plan_limit': 0,
            'usage_percent': 0.0,
        }
        try:
            if auth_supabase:
                posts = auth_supabase.table('posts').select(
                    'id,content,status,created_at,scheduled_for,posted_at,error_message'
                ).eq('user_id', user_id).order('created_at', desc=True).limit(50).execute().data or []
        except Exception as e:
            logger.error("Admin user details posts lookup failed: %s", e)

        try:
            if auth_supabase:
                month_start = datetime.utcnow().date().replace(day=1).isoformat()
                usage_rows = auth_supabase.table('usage_monthly').select('month,posts_generated').eq('user_id', user_id).eq('month', month_start).limit(1).execute().data or []
                if usage_rows:
                    analytics['posts_this_month'] = int(usage_rows[0].get('posts_generated') or 0)
        except Exception as e:
            logger.error("Admin user details usage lookup failed: %s", e)

        last_dates = []
        for post in posts:
            post['content_preview'] = (post.get('content') or '')[:180]
            status = str(post.get('status') or '').strip().lower()
            if status == 'posted':
                analytics['published_posts'] += 1
            if status == 'scheduled':
                analytics['scheduled_posts'] += 1
            if post.get('error_message'):
                analytics['failed_posts'] += 1
            analytics['total_posts'] += 1
            for field in ('posted_at', 'scheduled_for', 'created_at'):
                parsed = _parse_iso_utc(post.get(field))
                if parsed is not None:
                    last_dates.append(parsed)
        if last_dates:
            analytics['last_activity'] = max(last_dates).isoformat() + 'Z'

        try:
            posted_count = analytics.get('published_posts', 0)
            total_count = analytics.get('total_posts', 1)
            if total_count > 0:
                analytics['success_rate'] = round((posted_count / total_count) * 100, 1)
        except Exception as e:
            logger.error("Success rate calculation failed: %s", e)

        try:
            user_plan = str(details.get('plan', 'free') or 'free').lower().replace(' ', '_')
            from freemium import get_plan_limits
            plan_limits = get_plan_limits(user_plan)
            analytics['plan_limit'] = plan_limits.get('posts_generated', 0)
            posts_this_month = analytics.get('posts_this_month', 0)
            if analytics['plan_limit'] > 0:
                analytics['usage_percent'] = round((posts_this_month / analytics['plan_limit']) * 100, 1)
        except Exception as e:
            logger.error("Plan limits calculation failed: %s", e)

        return jsonify({'success': True, 'user': details, 'posts': posts, 'analytics': analytics})

    @admin_bp.route('/api/admin/users/<user_id>/status', methods=['POST'])
    @require_admin_api
    def admin_toggle_user_status(user_id):
        data = request.get_json() or {}
        active = bool(data.get('active', True))
        if not auth_supabase:
            return jsonify({'success': False, 'message': 'Supabase not configured'}), 500
        try:
            user_res = auth_supabase.auth.admin.get_user_by_id(user_id)
            user_obj = getattr(user_res, 'user', None)
            if user_obj is None and isinstance(user_res, dict):
                user_obj = user_res.get('user')
            if isinstance(user_obj, dict):
                current_metadata = user_obj.get('user_metadata', {}) or {}
            else:
                current_metadata = getattr(user_obj, 'user_metadata', {}) if user_obj else {}
            current_metadata = current_metadata or {}
            before_state = {'is_active': bool(current_metadata.get('is_active', True))}
            current_metadata['is_active'] = active
            attributes = {'user_metadata': current_metadata, 'ban_duration': 'none' if active else '876000h'}
            auth_supabase.auth.admin.update_user_by_id(user_id, attributes)
            after_state = {'is_active': active}
            _log_action('toggle_user_status', user_id, {
                'active': active,
                'before': before_state,
                'after': after_state,
                'diff': _dict_diff(before_state, after_state),
            })
            return jsonify({'success': True, 'message': 'User activated' if active else 'User deactivated'})
        except Exception as e:
            logger.error("Admin status update failed: %s", e)
            return _safe_api_error('Failed to update user status', e)

    @admin_bp.route('/api/admin/users/<user_id>', methods=['DELETE'])
    @require_admin_api
    def admin_delete_user(user_id):
        if not auth_supabase:
            return jsonify({'success': False, 'message': 'Supabase not configured'}), 500
        if not _is_valid_uuid(user_id):
            return jsonify({'success': False, 'message': 'Invalid user ID format'}), 400

        payload = request.get_json(silent=True) or {}
        confirm_value = (payload.get('confirm') or '').strip()
        force_delete = bool(payload.get('force'))

        expected_email = ''
        try:
            user_res = auth_supabase.auth.admin.get_user_by_id(user_id)
            user_obj = getattr(user_res, 'user', None)
            if user_obj is None and isinstance(user_res, dict):
                user_obj = user_res.get('user')
            if isinstance(user_obj, dict):
                expected_email = (user_obj.get('email') or '').strip()
            else:
                expected_email = getattr(user_obj, 'email', '') if user_obj else ''
        except Exception:
            expected_email = ''

        expected_token = f'DELETE {user_id}'
        if not force_delete:
            if not confirm_value or (expected_email and confirm_value != expected_email):
                return jsonify({
                    'success': False,
                    'message': 'Missing or incorrect confirmation for soft-delete. Send JSON {"confirm":"<user_email>"} to soft-delete.',
                }), 400
            try:
                try:
                    user_res = auth_supabase.auth.admin.get_user_by_id(user_id)
                except Exception:
                    user_res = None
                attrs = {'user_metadata': {}}
                if user_res:
                    uobj = getattr(user_res, 'user', None) or (user_res if isinstance(user_res, dict) else {})
                    current_md = (uobj.get('user_metadata') if isinstance(uobj, dict) else getattr(uobj, 'user_metadata', {})) or {}
                else:
                    current_md = {}
                current_md['soft_deleted'] = True
                current_md['deleted_at'] = datetime.utcnow().isoformat() + 'Z'
                attrs['user_metadata'] = current_md
                attrs['ban_duration'] = '876000h'
                auth_supabase.auth.admin.update_user_by_id(user_id, attrs)
                _log_action('soft_delete_user', user_id, {
                    'confirmed_by': session.get('admin_email', ''), 'confirmation': confirm_value,
                })
                return jsonify({
                    'success': True,
                    'message': 'User soft-deleted. To permanently remove the user, call DELETE with {"force": true, "confirm": "DELETE <user_id>"}',
                })
            except Exception as e:
                logger.error('Soft-delete failed for %s: %s', user_id, e)
                return _safe_api_error('Failed to soft-delete user', e)

        if not confirm_value or (confirm_value != expected_token and (expected_email and confirm_value != expected_email)):
            return jsonify({
                'success': False,
                'message': 'Missing or incorrect confirmation. To permanently delete, send JSON {"force": true, "confirm":"DELETE <user_id>"} or provide the user email.',
            }), 400

        cleanup_errors = []
        for table_name in ('posts', 'subscriptions', 'usage_monthly'):
            try:
                auth_supabase.table(table_name).delete().eq('user_id', user_id).execute()
            except Exception as table_err:
                logger.warning("Admin delete – cleanup %s for %s: %s", table_name, user_id, table_err)
                cleanup_errors.append(f'{table_name}: {table_err}')

        try:
            auth_supabase.auth.admin.delete_user(user_id)
        except Exception as e:
            err_str = str(e).lower()
            if 'not found' not in err_str and 'user not found' not in err_str:
                logger.error("Admin delete user failed: %s", e)
                return _safe_api_error('Failed to delete user', e)
            logger.info("Admin delete – user %s already removed from auth", user_id)

        log_details = {'cleanup_errors': cleanup_errors}
        try:
            if force_delete:
                log_details['confirmation'] = confirm_value
        except Exception:
            pass
        _log_action('delete_user', user_id, log_details)

        message = 'User deleted successfully'
        if cleanup_errors:
            message += f' (some data cleanup warnings: {"; ".join(cleanup_errors)})'
        return jsonify({'success': True, 'message': message})

    @admin_bp.route('/api/admin/users/<user_id>/restore', methods=['POST'])
    @require_admin_api
    def admin_restore_user(user_id):
        if not auth_supabase:
            return jsonify({'success': False, 'message': 'Supabase not configured'}), 500
        if not _is_valid_uuid(user_id):
            return jsonify({'success': False, 'message': 'Invalid user ID format'}), 400
        try:
            user_res = auth_supabase.auth.admin.get_user_by_id(user_id)
            user_obj = getattr(user_res, 'user', None)
            if user_obj is None and isinstance(user_res, dict):
                user_obj = user_res.get('user')
            if isinstance(user_obj, dict):
                current_metadata = user_obj.get('user_metadata', {}) or {}
            else:
                current_metadata = getattr(user_obj, 'user_metadata', {}) if user_obj else {}
            current_metadata = current_metadata or {}
            current_metadata.pop('soft_deleted', None)
            current_metadata.pop('deleted_at', None)
            auth_supabase.auth.admin.update_user_by_id(user_id, {
                'user_metadata': current_metadata, 'ban_duration': 'none',
            })
            _log_action('restore_user', user_id, {})
            return jsonify({'success': True, 'message': 'User restored successfully'})
        except Exception as e:
            logger.error('Restore user failed: %s', e)
            return _safe_api_error('Failed to restore user', e)

    @admin_bp.route('/api/admin/users/soft_deleted', methods=['GET'])
    @require_admin_api
    def admin_list_soft_deleted_users():
        try:
            users = _list_auth_users()
            soft = []
            for u in users:
                if isinstance(u, dict):
                    u_obj = u
                else:
                    u_obj = getattr(u, 'user', None) or u
                md = (u_obj.get('user_metadata') if isinstance(u_obj, dict) else getattr(u_obj, 'user_metadata', {})) or {}
                soft_flag = bool(md.get('soft_deleted'))
                deleted_at = md.get('deleted_at')
                if not soft_flag:
                    try:
                        uid = str((u_obj.get('id') if isinstance(u_obj, dict) else getattr(u_obj, 'id', '')) or '')
                        if uid and auth_supabase:
                            full_res = auth_supabase.auth.admin.get_user_by_id(uid)
                            full_user = getattr(full_res, 'user', None)
                            if full_user is None and isinstance(full_res, dict):
                                full_user = full_res.get('user')
                            full_md = ((full_user.get('user_metadata') if isinstance(full_user, dict) else getattr(full_user, 'user_metadata', {})) if full_user else {}) or {}
                            soft_flag = bool(full_md.get('soft_deleted'))
                            deleted_at = deleted_at or full_md.get('deleted_at')
                    except Exception:
                        pass

                if soft_flag:
                    uid_val = str((u_obj.get('id') if isinstance(u_obj, dict) else getattr(u_obj, 'id', '')) or '')
                    email_val = u_obj.get('email', '') if isinstance(u_obj, dict) else getattr(u_obj, 'email', '')
                    soft.append({
                        'id': uid_val, 'email': email_val,
                        'first_name': md.get('first_name', ''),
                        'last_name': md.get('last_name', ''),
                        'deleted_at': deleted_at,
                    })
            return jsonify({'success': True, 'users': soft})
        except Exception as e:
            logger.error('List soft-deleted users failed: %s', e)
            return _safe_api_error('An unexpected error occurred', e)

    @admin_bp.route('/api/admin/users/bulk_restore', methods=['POST'])
    @require_admin_api
    def admin_bulk_restore():
        try:
            payload = request.get_json(silent=True) or {}
            user_ids = payload.get('user_ids') or []
            if not isinstance(user_ids, list) or not user_ids:
                return jsonify({'success': False, 'message': 'user_ids must be a non-empty list'}), 400
            results = []
            for uid in user_ids:
                try:
                    user_res = auth_supabase.auth.admin.get_user_by_id(uid)
                    user_obj = getattr(user_res, 'user', None)
                    if user_obj is None and isinstance(user_res, dict):
                        user_obj = user_res.get('user')
                    if isinstance(user_obj, dict):
                        current_metadata = user_obj.get('user_metadata', {}) or {}
                    else:
                        current_metadata = getattr(user_obj, 'user_metadata', {}) if user_obj else {}
                    current_metadata = current_metadata or {}
                    current_metadata.pop('soft_deleted', None)
                    current_metadata.pop('deleted_at', None)
                    auth_supabase.auth.admin.update_user_by_id(uid, {
                        'user_metadata': current_metadata, 'ban_duration': 'none',
                    })
                    _log_action('bulk_restore', uid, {'by': session.get('admin_email', '')})
                    results.append({'id': uid, 'success': True})
                except Exception as e:
                    logger.error('Bulk restore failed for %s: %s', uid, e)
                    results.append({'id': uid, 'success': False, 'message': str(e)})
            return jsonify({'success': True, 'results': results})
        except Exception as e:
            logger.error('Bulk restore operation failed: %s', e)
            return _safe_api_error('An unexpected error occurred', e)

    @admin_bp.route('/api/admin/users/purge', methods=['POST'])
    @require_admin_api
    def admin_bulk_purge():
        try:
            payload = request.get_json(silent=True) or {}
            user_ids = payload.get('user_ids') or []
            confirm = (payload.get('confirm') or '').strip()
            if not isinstance(user_ids, list) or not user_ids:
                return jsonify({'success': False, 'message': 'user_ids must be a non-empty list'}), 400
            if confirm != 'PURGE':
                return jsonify({'success': False, 'message': 'Missing or incorrect confirmation. Set confirm="PURGE" to proceed.'}), 400

            summary = []
            for uid in user_ids:
                item = {'id': uid, 'deleted': False, 'errors': []}
                try:
                    for table_name in ('posts', 'subscriptions', 'usage_monthly'):
                        try:
                            auth_supabase.table(table_name).delete().eq('user_id', uid).execute()
                        except Exception as table_err:
                            item['errors'].append(f'{table_name}: {table_err}')
                    try:
                        auth_supabase.auth.admin.delete_user(uid)
                        item['deleted'] = True
                    except Exception as e:
                        if 'not found' in str(e).lower():
                            item['deleted'] = True
                        else:
                            item['errors'].append(str(e))
                    _log_action('bulk_purge_user', uid, {'by': session.get('admin_email', ''), 'errors': item['errors']})
                except Exception as e:
                    logger.error('Bulk purge error for %s: %s', uid, e)
                    item['errors'].append(str(e))
                summary.append(item)
            return jsonify({'success': True, 'summary': summary})
        except Exception as e:
            logger.error('Bulk purge operation failed: %s', e)
            return _safe_api_error('An unexpected error occurred', e)

    @admin_bp.route('/api/admin/users/purge_scheduled', methods=['POST'])
    @require_admin_api
    def admin_purge_scheduled():
        try:
            payload = request.get_json(silent=True) or {}
            days = int(payload.get('days') or 30)
            cutoff = datetime.utcnow() - timedelta(days=days)
            users = _list_auth_users()
            to_purge = []
            for u in users:
                u_obj = u if isinstance(u, dict) else getattr(u, 'user', {})
                md = (u_obj.get('user_metadata') if isinstance(u_obj, dict) else getattr(u_obj, 'user_metadata', {})) or {}
                deleted_at = md.get('deleted_at')
                if md.get('soft_deleted') and deleted_at:
                    try:
                        dt = datetime.fromisoformat(str(deleted_at).replace('Z', '+00:00')).replace(tzinfo=None)
                        if dt <= cutoff:
                            uid = str((u_obj.get('id') if isinstance(u_obj, dict) else getattr(u_obj, 'id', '')) or '')
                            to_purge.append(uid)
                    except Exception:
                        continue
            if not to_purge:
                return jsonify({'success': True, 'purged': 0, 'ids': []})
            purged = []
            for uid in to_purge:
                try:
                    for table_name in ('posts', 'subscriptions', 'usage_monthly'):
                        try:
                            auth_supabase.table(table_name).delete().eq('user_id', uid).execute()
                        except Exception:
                            pass
                    try:
                        auth_supabase.auth.admin.delete_user(uid)
                    except Exception:
                        pass
                    _log_action('scheduled_purge_user', uid, {'days': days})
                    purged.append(uid)
                except Exception:
                    pass
            return jsonify({'success': True, 'purged': len(purged), 'ids': purged})
        except Exception as e:
            logger.error('Scheduled purge failed: %s', e)
            return _safe_api_error('An unexpected error occurred', e)

    # ── Identity management ───────────────────────────────────────────────

    @admin_bp.route('/api/admin/users/<user_id>/attach_identity', methods=['POST'])
    @require_admin_api
    def admin_attach_identity(user_id):
        try:
            payload = request.get_json(silent=True) or {}
            provider = (payload.get('provider') or '').strip()
            provider_user_id = (payload.get('provider_user_id') or '').strip()
            if not provider or not provider_user_id:
                return jsonify({'success': False, 'message': 'provider and provider_user_id are required'}), 400
            user_res = auth_supabase.auth.admin.get_user_by_id(user_id)
            user_obj = getattr(user_res, 'user', None)
            if user_obj is None and isinstance(user_res, dict):
                user_obj = user_res.get('user')
            if isinstance(user_obj, dict):
                current_metadata = user_obj.get('user_metadata', {}) or {}
            else:
                current_metadata = getattr(user_obj, 'user_metadata', {}) if user_obj else {}
            current_metadata = current_metadata or {}
            linked = current_metadata.get('linked_identities') or []
            if not isinstance(linked, list):
                linked = []
            linked.append({
                'provider': provider, 'provider_user_id': provider_user_id,
                'attached_at': datetime.utcnow().isoformat() + 'Z',
                'attached_by': session.get('admin_email', ''),
            })
            current_metadata['linked_identities'] = linked
            auth_supabase.auth.admin.update_user_by_id(user_id, {'user_metadata': current_metadata})
            _log_action('attach_identity', user_id, {'provider': provider, 'provider_user_id': provider_user_id})
            return jsonify({'success': True, 'message': 'Identity attached to user metadata'})
        except Exception as e:
            logger.error('Attach identity failed: %s', e)
            return _safe_api_error('An unexpected error occurred', e)

    @admin_bp.route('/api/admin/users/<user_id>/detach_identity', methods=['POST'])
    @require_admin_api
    def admin_detach_identity(user_id):
        try:
            payload = request.get_json(silent=True) or {}
            provider = (payload.get('provider') or '').strip()
            provider_user_id = (payload.get('provider_user_id') or '').strip()
            if not provider or not provider_user_id:
                return jsonify({'success': False, 'message': 'provider and provider_user_id are required'}), 400
            user_res = auth_supabase.auth.admin.get_user_by_id(user_id)
            user_obj = getattr(user_res, 'user', None)
            if user_obj is None and isinstance(user_res, dict):
                user_obj = user_res.get('user')
            if isinstance(user_obj, dict):
                current_metadata = user_obj.get('user_metadata', {}) or {}
            else:
                current_metadata = getattr(user_obj, 'user_metadata', {}) if user_obj else {}
            current_metadata = current_metadata or {}
            linked = current_metadata.get('linked_identities') or []
            if not isinstance(linked, list):
                linked = []
            new_linked = [l for l in linked if not (l.get('provider') == provider and l.get('provider_user_id') == provider_user_id)]
            current_metadata['linked_identities'] = new_linked
            auth_supabase.auth.admin.update_user_by_id(user_id, {'user_metadata': current_metadata})
            _log_action('detach_identity', user_id, {'provider': provider, 'provider_user_id': provider_user_id})
            return jsonify({'success': True, 'message': 'Identity detached'})
        except Exception as e:
            logger.error('Detach identity failed: %s', e)
            return _safe_api_error('An unexpected error occurred', e)

    @admin_bp.route('/api/admin/users/<user_id>/posts', methods=['GET'])
    @require_admin_api
    def admin_user_posts(user_id):
        try:
            if not auth_supabase:
                return jsonify({'success': False, 'message': 'Supabase not configured'}), 500
            posts = auth_supabase.table('posts').select(
                'id,content,status,created_at,scheduled_for,posted_at,error_message'
            ).eq('user_id', user_id).order('created_at', desc=True).limit(100).execute().data or []
            for post in posts:
                post['content_preview'] = (post.get('content') or '')[:180]
            return jsonify({'success': True, 'posts': posts})
        except Exception as e:
            logger.error("Admin fetch user posts failed: %s", e)
            return _safe_api_error('An unexpected error occurred', e)

    # ── Legacy migration ──────────────────────────────────────────────────

    @admin_bp.route('/api/admin/migrate-legacy-content-owner', methods=['POST'])
    @require_admin_api
    def admin_migrate_legacy_content_owner():
        data = request.get_json(silent=True) or {}
        target_user_id = str(data.get('target_user_id') or '').strip()
        dry_run = bool(data.get('dry_run', False))
        if not _is_valid_uuid(target_user_id):
            return jsonify({'success': False, 'message': 'Valid target_user_id is required'}), 400
        try:
            posts = _read_json_list(POSTS_PATH)
            scheduled_posts = _read_json_list(SCHEDULED_POSTS_PATH)
            posts_migrated = 0
            for row in posts:
                if not str(row.get('user_id') or '').strip():
                    row['user_id'] = target_user_id
                    posts_migrated += 1
            scheduled_migrated = 0
            for row in scheduled_posts:
                if not str(row.get('user_id') or '').strip():
                    row['user_id'] = target_user_id
                    scheduled_migrated += 1
            if not dry_run:
                _write_json_list(POSTS_PATH, posts)
                _write_json_list(SCHEDULED_POSTS_PATH, scheduled_posts)
            _log_action('migrate_legacy_content_owner', target_user_id, {
                'dry_run': dry_run, 'posts_migrated': posts_migrated,
                'scheduled_migrated': scheduled_migrated,
            })
            return jsonify({
                'success': True, 'dry_run': dry_run,
                'target_user_id': target_user_id,
                'posts_migrated': posts_migrated,
                'scheduled_migrated': scheduled_migrated,
                'message': 'Dry run complete' if dry_run else 'Legacy ownership migration completed',
            })
        except Exception as e:
            logger.error('Admin legacy ownership migration failed: %s', e)
            return _safe_api_error('An unexpected error occurred', e)

    # ── Subscription admin ────────────────────────────────────────────────

    @admin_bp.route('/api/admin/users/<user_id>/subscription/set-plan', methods=['POST'])
    @require_admin_api
    def admin_set_subscription_plan(user_id):
        if not auth_supabase:
            return jsonify({'success': False, 'message': 'Supabase not configured'}), 500
        selected = _find_auth_user_by_id(user_id)
        if not selected:
            return jsonify({'success': False, 'message': 'User not found'}), 404
        data = request.get_json() or {}
        normalized = _normalize_subscription_plan(data.get('plan'))
        if not normalized:
            return jsonify({'success': False, 'message': 'Invalid plan. Use 1_month, 3_month, or 12_month.'}), 400
        plan, months = normalized
        now = datetime.utcnow()
        period_end = _add_months_utc(now, months)
        try:
            before_rows = auth_supabase.table('subscriptions').select('plan,status,current_period_end,cancel_at_period_end').eq('user_id', user_id).limit(1).execute().data or []
            before_state = before_rows[0] if before_rows else {}
            auth_supabase.table('subscriptions').upsert({
                'user_id': user_id, 'plan': plan, 'status': 'active',
                'billing_provider': 'manual',
                'current_period_start': now.isoformat() + 'Z',
                'current_period_end': period_end.isoformat() + 'Z',
                'cancel_at_period_end': False, 'updated_at': now.isoformat() + 'Z',
            }, on_conflict='user_id').execute()
            after_state = {
                'plan': plan,
                'status': 'active',
                'current_period_end': period_end.isoformat() + 'Z',
                'cancel_at_period_end': False,
            }
            _log_action('set_subscription_plan', user_id, {
                'plan': plan,
                'months': months,
                'before': before_state,
                'after': after_state,
                'diff': _dict_diff(before_state, after_state),
            })
            return jsonify({
                'success': True,
                'message': f'Subscription updated to {plan.replace("_", " ")}',
                'plan': plan, 'subscription_period_end': period_end.isoformat() + 'Z',
            })
        except Exception as e:
            logger.error("Admin set subscription failed: %s", e)
            return _safe_api_error('Failed to update subscription', e)

    @admin_bp.route('/api/admin/users/<user_id>/subscription/cancel', methods=['POST'])
    @require_admin_api
    def admin_cancel_subscription(user_id):
        if not auth_supabase:
            return jsonify({'success': False, 'message': 'Supabase not configured'}), 500
        try:
            now = datetime.utcnow().isoformat() + 'Z'
            before_rows = auth_supabase.table('subscriptions').select('status,cancel_at_period_end,updated_at').eq('user_id', user_id).limit(1).execute().data or []
            before_state = before_rows[0] if before_rows else {}
            auth_supabase.table('subscriptions').upsert({
                'user_id': user_id, 'status': 'cancelled',
                'cancel_at_period_end': True, 'updated_at': now,
            }, on_conflict='user_id').execute()
            after_state = {'status': 'cancelled', 'cancel_at_period_end': True, 'updated_at': now}
            _log_action('cancel_subscription', user_id, {
                'cancel_at_period_end': True,
                'before': before_state,
                'after': after_state,
                'diff': _dict_diff(before_state, after_state),
            })
            return jsonify({'success': True, 'message': 'Subscription marked to cancel'})
        except Exception as e:
            logger.error("Admin cancel subscription failed: %s", e)
            return _safe_api_error('Failed to cancel subscription', e)

    # ── Password & email management ───────────────────────────────────────

    @admin_bp.route('/api/admin/users/<user_id>/password/send-reset', methods=['POST'])
    @require_admin_api
    def admin_send_password_reset(user_id):
        selected = _find_auth_user_by_id(user_id)
        if not selected:
            return jsonify({'success': False, 'message': 'User not found'}), 404
        email = str(getattr(selected, 'email', '') or '').strip()
        if not email:
            return jsonify({'success': False, 'message': 'User email not found'}), 400
        success, message = request_password_reset(email)
        if success:
            _log_action('send_password_reset', user_id, {'email': email})
            return jsonify({'success': True, 'message': message, 'email': email})
        return jsonify({'success': False, 'message': message}), 400

    @admin_bp.route('/api/admin/users/<user_id>/password/set-temp', methods=['POST'])
    @require_admin_api
    def admin_set_temp_password(user_id):
        if not auth_supabase:
            return jsonify({'success': False, 'message': 'Supabase not configured'}), 500
        data = request.get_json() or {}
        temporary_password = str(data.get('temporary_password') or '').strip()
        if len(temporary_password) < 8:
            return jsonify({'success': False, 'message': 'Temporary password must be at least 8 characters'}), 400
        try:
            auth_supabase.auth.admin.update_user_by_id(user_id, {'password': temporary_password})
            _log_action('set_temp_password', user_id, {'password_length': len(temporary_password)})
            return jsonify({'success': True, 'message': 'Temporary password has been set'})
        except Exception as e:
            logger.error("Admin set temp password failed: %s", e)
            return _safe_api_error('Failed to set temporary password', e)

    @admin_bp.route('/api/admin/users/<user_id>/email/update', methods=['POST'])
    @require_admin_api
    def admin_update_user_email(user_id):
        if not auth_supabase:
            return jsonify({'success': False, 'message': 'Supabase not configured'}), 500
        data = request.get_json() or {}
        new_email = str(data.get('new_email') or '').strip().lower()
        if '@' not in new_email:
            return jsonify({'success': False, 'message': 'Valid email is required'}), 400
        try:
            selected = _find_auth_user_by_id(user_id)
            old_email = str(getattr(selected, 'email', '') or (selected.get('email', '') if isinstance(selected, dict) else '')).strip().lower() if selected else ''
            auth_supabase.auth.admin.update_user_by_id(user_id, {'email': new_email})
            before_state = {'email': old_email}
            after_state = {'email': new_email}
            _log_action('update_user_email', user_id, {
                'new_email': new_email,
                'before': before_state,
                'after': after_state,
                'diff': _dict_diff(before_state, after_state),
            })
            return jsonify({'success': True, 'message': 'User email updated successfully', 'email': new_email})
        except Exception as e:
            logger.error("Admin update user email failed: %s", e)
            return _safe_api_error('Failed to update user email', e)

    # ── Audit logs ────────────────────────────────────────────────────────

    @admin_bp.route('/api/admin/audit-logs', methods=['GET'])
    @require_admin_api
    def admin_audit_logs():
        if not auth_supabase:
            return jsonify({'success': False, 'message': 'Supabase not configured'}), 500
        try:
            raw_limit = request.args.get('limit', '20')
            try:
                limit = max(1, min(100, int(raw_limit)))
            except Exception:
                limit = 20
            rows = auth_supabase.table('system_logs') \
                .select('id,level,message,request_path,request_method,metadata,created_at') \
                .like('message', 'admin:%') \
                .order('created_at', desc=True) \
                .limit(limit) \
                .execute().data or []
            return jsonify({'success': True, 'logs': rows})
        except Exception as e:
            logger.error("Admin audit logs fetch failed: %s", e)
            return _safe_api_error('Failed to fetch audit logs', e)

    @admin_bp.route('/api/admin/users/<user_id>/audit-trail', methods=['GET'])
    @require_admin_api
    def admin_user_audit_trail(user_id):
        if not auth_supabase:
            return jsonify({'success': False, 'message': 'Supabase not configured'}), 500
        try:
            raw_limit = request.args.get('limit', '30')
            try:
                limit = max(1, min(100, int(raw_limit)))
            except Exception:
                limit = 30
            rows = auth_supabase.table('system_logs') \
                .select('id,level,message,request_path,request_method,metadata,created_at') \
                .like('message', 'admin:%') \
                .order('created_at', desc=True) \
                .limit(limit * 3) \
                .execute().data or []
            filtered_rows = [
                row for row in rows
                if row.get('metadata', {}).get('target_user_id') == user_id
                   or row.get('request_path', '').endswith(f'/users/{user_id}')
                   or row.get('request_path', '').startswith(f'/api/admin/users/{user_id}')
            ][:limit]
            return jsonify({'success': True, 'logs': filtered_rows})
        except Exception as e:
            logger.error("User audit trail fetch failed: %s", e)
            return _safe_api_error('Failed to fetch user audit trail', e)

    # ── Dead-Letter Queue (DLQ) visibility & retry ────────────────────────

    def _get_redis():
        """Lazy Redis connection for DLQ read/retry (reuses worker env vars)."""
        from redis import Redis
        return Redis(
            host=os.getenv('REDIS_HOST', '127.0.0.1'),
            port=int(os.getenv('REDIS_PORT', '6379')),
            db=int(os.getenv('REDIS_DB', '0')),
            password=os.getenv('REDIS_PASSWORD', None) or None,
            ssl=os.getenv('REDIS_SSL', '').lower() in {'1', 'true', 'yes'},
            decode_responses=True,
            socket_connect_timeout=5,
        )

    _DLQ_REDIS_KEY = f"rq:dlq:{os.getenv('DEAD_LETTER_QUEUE', 'dead_letter')}"

    @admin_bp.route('/api/admin/dlq', methods=['GET'])
    @require_admin_api
    def admin_dlq_list():
        """List dead-letter queue entries (newest first)."""
        try:
            r = _get_redis()
            raw_limit = request.args.get('limit', '50')
            try:
                limit = max(1, min(200, int(raw_limit)))
            except Exception:
                limit = 50
            # ZREVRANGEBYSCORE returns newest first (highest score = most recent)
            entries_raw = r.zrevrangebyscore(_DLQ_REDIS_KEY, '+inf', '-inf', start=0, num=limit, withscores=True)
            entries = []
            for payload_str, score in entries_raw:
                try:
                    entry = json.loads(payload_str)
                    entry['_score'] = score
                    entries.append(entry)
                except json.JSONDecodeError:
                    entries.append({'raw': payload_str, '_score': score})
            total = r.zcard(_DLQ_REDIS_KEY)
            return jsonify({'success': True, 'entries': entries, 'total': total})
        except Exception as e:
            return _safe_api_error('Failed to read DLQ', e)

    @admin_bp.route('/api/admin/dlq/<job_id>/retry', methods=['POST'])
    @require_admin_api
    def admin_dlq_retry(job_id):
        """Re-enqueue a DLQ job by job_id. Removes it from the DLQ."""
        try:
            import importlib
            from rq import Queue
            r_raw = _get_redis()
            # Search for the entry to get func_name and args
            all_entries = r_raw.zrangebyscore(_DLQ_REDIS_KEY, '-inf', '+inf')
            target = None
            target_raw = None
            for raw in all_entries:
                try:
                    entry = json.loads(raw)
                    if entry.get('job_id') == job_id:
                        target = entry
                        target_raw = raw
                        break
                except json.JSONDecodeError:
                    continue
            if not target:
                return jsonify({'success': False, 'message': f'Job {job_id} not found in DLQ'}), 404
            # Re-enqueue via RQ
            from redis import Redis as RawRedis
            conn = RawRedis(
                host=os.getenv('REDIS_HOST', '127.0.0.1'),
                port=int(os.getenv('REDIS_PORT', '6379')),
                db=int(os.getenv('REDIS_DB', '0')),
                password=os.getenv('REDIS_PASSWORD', None) or None,
                ssl=os.getenv('REDIS_SSL', '').lower() in {'1', 'true', 'yes'},
                decode_responses=False,
            )
            queue_name = os.getenv('KB_QUEUE_NAME', 'mantraj_kb_jobs')
            q = Queue(queue_name, connection=conn)
            func_name = target.get('func_name', '')
            # Resolve function reference
            if '.' in func_name:
                mod_path, fn_name = func_name.rsplit('.', 1)
                mod = importlib.import_module(mod_path)
                func = getattr(mod, fn_name)
            else:
                func = None
            if func:
                q.enqueue(func, *[str(a) for a in target.get('args', [])])
            # Remove from DLQ
            r_raw.zrem(_DLQ_REDIS_KEY, target_raw)
            _log_action(f'DLQ retry: {job_id} ({func_name})')
            return jsonify({'success': True, 'message': f'Job {job_id} re-enqueued'})
        except Exception as e:
            return _safe_api_error(f'Failed to retry DLQ job {job_id}', e)

    @admin_bp.route('/api/admin/dlq/<job_id>', methods=['DELETE'])
    @require_admin_api
    def admin_dlq_delete(job_id):
        """Remove a single entry from the DLQ by job_id."""
        try:
            r = _get_redis()
            all_entries = r.zrangebyscore(_DLQ_REDIS_KEY, '-inf', '+inf')
            removed = False
            for raw in all_entries:
                try:
                    entry = json.loads(raw)
                    if entry.get('job_id') == job_id:
                        r.zrem(_DLQ_REDIS_KEY, raw)
                        removed = True
                        break
                except json.JSONDecodeError:
                    continue
            if not removed:
                return jsonify({'success': False, 'message': f'Job {job_id} not found in DLQ'}), 404
            _log_action(f'DLQ delete: {job_id}')
            return jsonify({'success': True, 'message': f'Job {job_id} removed from DLQ'})
        except Exception as e:
            return _safe_api_error(f'Failed to delete DLQ job {job_id}', e)

    @admin_bp.route('/api/admin/dlq/purge', methods=['POST'])
    @require_admin_api
    def admin_dlq_purge():
        """Purge all entries from the DLQ."""
        try:
            r = _get_redis()
            count = r.zcard(_DLQ_REDIS_KEY)
            r.delete(_DLQ_REDIS_KEY)
            _log_action(f'DLQ purge: {count} entries removed')
            return jsonify({'success': True, 'message': f'Purged {count} DLQ entries'})
        except Exception as e:
            return _safe_api_error('Failed to purge DLQ', e)

    # ── Discount / Coupon Code CRUD ────────────────────────────────────────

    @admin_bp.route('/api/admin/coupons', methods=['GET'])
    @require_admin_api
    def admin_coupons_list():
        """List all discount codes."""
        try:
            if not auth_supabase:
                return jsonify({'success': False, 'message': 'Database not configured'}), 503
            res = auth_supabase.table('discount_codes').select('*').order('created_at', desc=True).execute()
            return jsonify({'success': True, 'coupons': res.data or []})
        except Exception as e:
            return _safe_api_error('Failed to list coupons', e)

    @admin_bp.route('/api/admin/coupons', methods=['POST'])
    @require_admin_api
    def admin_coupons_create():
        """Create a new discount code."""
        try:
            if not auth_supabase:
                return jsonify({'success': False, 'message': 'Database not configured'}), 503
            data = request.get_json(silent=True) or {}
            code = str(data.get('code') or '').strip().upper()
            discount_pct = int(data.get('discount_pct') or 0)
            max_uses = int(data.get('max_uses') or 100)
            valid_until = data.get('valid_until') or None  # ISO string or null

            if not code:
                return jsonify({'success': False, 'message': 'code is required'}), 400
            if not (1 <= discount_pct <= 100):
                return jsonify({'success': False, 'message': 'discount_pct must be 1-100'}), 400

            row = {
                'code': code,
                'discount_pct': discount_pct,
                'max_uses': max_uses,
                'is_active': True,
            }
            if valid_until:
                row['valid_until'] = valid_until

            res = auth_supabase.table('discount_codes').insert(row).execute()
            _log_action(f'Coupon created: {code} ({discount_pct}%)')
            return jsonify({'success': True, 'coupon': (res.data or [{}])[0]})
        except Exception as e:
            return _safe_api_error('Failed to create coupon', e)

    @admin_bp.route('/api/admin/coupons/<code>', methods=['PATCH'])
    @require_admin_api
    def admin_coupons_update(code):
        """Toggle is_active or update a coupon code."""
        try:
            if not auth_supabase:
                return jsonify({'success': False, 'message': 'Database not configured'}), 503
            data = request.get_json(silent=True) or {}
            updates = {}
            if 'is_active' in data:
                updates['is_active'] = bool(data['is_active'])
            if 'max_uses' in data:
                updates['max_uses'] = int(data['max_uses'])
            if 'valid_until' in data:
                updates['valid_until'] = data['valid_until']
            if not updates:
                return jsonify({'success': False, 'message': 'No fields to update'}), 400
            auth_supabase.table('discount_codes').update(updates).eq('code', code.upper()).execute()
            _log_action(f'Coupon updated: {code}')
            return jsonify({'success': True, 'message': f'Coupon {code} updated'})
        except Exception as e:
            return _safe_api_error(f'Failed to update coupon {code}', e)

    @admin_bp.route('/api/admin/coupons/<code>', methods=['DELETE'])
    @require_admin_api
    def admin_coupons_delete(code):
        """Delete a discount code."""
        try:
            if not auth_supabase:
                return jsonify({'success': False, 'message': 'Database not configured'}), 503
            auth_supabase.table('discount_codes').delete().eq('code', code.upper()).execute()
            _log_action(f'Coupon deleted: {code}')
            return jsonify({'success': True, 'message': f'Coupon {code} deleted'})
        except Exception as e:
            return _safe_api_error(f'Failed to delete coupon {code}', e)

    # ── Referral Analytics ─────────────────────────────────────────────────

    @admin_bp.route('/api/admin/referrals', methods=['GET'])
    @require_admin_api
    def admin_referrals():
        """Top referrers and referral count totals."""
        try:
            if not auth_supabase:
                return jsonify({'success': False, 'message': 'Database not configured'}), 503
            res = auth_supabase.table('user_profiles').select(
                'user_id,referral_code,referral_count,referred_by'
            ).gt('referral_count', 0).order('referral_count', desc=True).limit(50).execute()
            rows = res.data or []
            total_referrals = sum(int(r.get('referral_count') or 0) for r in rows)
            return jsonify({
                'success': True,
                'total_referrals': total_referrals,
                'top_referrers': rows,
            })
        except Exception as e:
            return _safe_api_error('Failed to fetch referral stats', e)

    # ── Advanced admin operations ───────────────────────────────────────

    @admin_bp.route('/api/admin/audit-export.csv', methods=['GET'])
    @require_admin_api
    def admin_audit_export_csv():
        """Export recent admin audit records as CSV, including before/after diff payloads."""
        if not auth_supabase:
            return jsonify({'success': False, 'message': 'Supabase not configured'}), 500
        try:
            raw_limit = request.args.get('limit', '500')
            try:
                limit = max(1, min(5000, int(raw_limit)))
            except Exception:
                limit = 500
            rows = auth_supabase.table('system_logs') \
                .select('id,level,message,request_path,request_method,metadata,created_at') \
                .like('message', 'admin:%') \
                .order('created_at', desc=True) \
                .limit(limit) \
                .execute().data or []

            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow([
                'id', 'created_at', 'action', 'admin_email', 'target_user_id', 'request_method',
                'request_path', 'before', 'after', 'diff', 'details',
            ])
            for row in rows:
                metadata = row.get('metadata', {}) or {}
                details = metadata.get('details', {}) or {}
                writer.writerow([
                    row.get('id', ''),
                    row.get('created_at', ''),
                    str(row.get('message', '')).replace('admin:', '', 1),
                    metadata.get('admin_email', ''),
                    metadata.get('target_user_id', ''),
                    row.get('request_method', ''),
                    row.get('request_path', ''),
                    json.dumps(details.get('before', {}), ensure_ascii=True),
                    json.dumps(details.get('after', {}), ensure_ascii=True),
                    json.dumps(details.get('diff', {}), ensure_ascii=True),
                    json.dumps(details, ensure_ascii=True),
                ])

            ts = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            csv_data = output.getvalue()
            output.close()
            return Response(
                csv_data,
                mimetype='text/csv',
                headers={'Content-Disposition': f'attachment; filename=admin_audit_export_{ts}.csv'},
            )
        except Exception as e:
            return _safe_api_error('Failed to export audit logs', e)

    @admin_bp.route('/api/admin/queue/health', methods=['GET'])
    @require_admin_api
    def admin_queue_health():
        """Queue/worker health with stuck and failed job visibility."""
        try:
            from redis import Redis as RawRedis
            from rq import Queue, Worker
            from rq.registry import FailedJobRegistry, FinishedJobRegistry, ScheduledJobRegistry, StartedJobRegistry

            queue_name = os.getenv('KB_QUEUE_NAME', 'mantraj_kb_jobs')
            conn = RawRedis(
                host=os.getenv('REDIS_HOST', '127.0.0.1'),
                port=int(os.getenv('REDIS_PORT', '6379')),
                db=int(os.getenv('REDIS_DB', '0')),
                password=os.getenv('REDIS_PASSWORD', None) or None,
                ssl=os.getenv('REDIS_SSL', '').lower() in {'1', 'true', 'yes'},
                decode_responses=False,
                socket_connect_timeout=5,
            )
            queue = Queue(queue_name, connection=conn)
            started = StartedJobRegistry(queue=queue)
            failed = FailedJobRegistry(queue=queue)
            scheduled = ScheduledJobRegistry(queue=queue)
            finished = FinishedJobRegistry(queue=queue)

            now = datetime.utcnow()
            stuck_threshold_min = max(1, min(240, int(request.args.get('stuck_minutes', '20'))))
            stuck_jobs = []
            for job_id in started.get_job_ids()[:200]:
                try:
                    job = queue.fetch_job(job_id)
                    if not job:
                        continue
                    started_at = job.started_at
                    if not started_at:
                        continue
                    elapsed_min = (now - started_at.replace(tzinfo=None)).total_seconds() / 60.0
                    if elapsed_min >= stuck_threshold_min:
                        stuck_jobs.append({
                            'job_id': job.id,
                            'func_name': job.func_name,
                            'enqueued_at': job.enqueued_at.isoformat() + 'Z' if job.enqueued_at else None,
                            'started_at': started_at.isoformat() + 'Z',
                            'elapsed_minutes': round(elapsed_min, 1),
                        })
                except Exception:
                    continue

            failed_jobs = []
            for job_id in failed.get_job_ids()[:50]:
                try:
                    job = queue.fetch_job(job_id)
                    if not job:
                        continue
                    failed_jobs.append({
                        'job_id': job.id,
                        'func_name': job.func_name,
                        'exc_info': (job.exc_info or '')[-600:],
                        'ended_at': job.ended_at.isoformat() + 'Z' if job.ended_at else None,
                    })
                except Exception:
                    continue

            worker_rows = []
            for worker in Worker.all(connection=conn):
                worker_rows.append({
                    'name': worker.name,
                    'state': worker.state,
                    'last_heartbeat': worker.last_heartbeat.isoformat() + 'Z' if worker.last_heartbeat else None,
                    'current_job_id': worker.get_current_job_id(),
                })

            return jsonify({
                'success': True,
                'queue_name': queue_name,
                'counts': {
                    'queued': queue.count,
                    'started': len(started),
                    'failed': len(failed),
                    'scheduled': len(scheduled),
                    'finished': len(finished),
                    'workers': len(worker_rows),
                    'stuck': len(stuck_jobs),
                },
                'workers': worker_rows,
                'stuck_jobs': stuck_jobs,
                'failed_jobs': failed_jobs,
            })
        except Exception as e:
            return _safe_api_error('Failed to fetch queue health', e)

    @admin_bp.route('/api/admin/queue/jobs/<job_id>/retry', methods=['POST'])
    @require_admin_api
    def admin_retry_queue_job(job_id):
        try:
            from redis import Redis as RawRedis
            from rq import Queue
            queue_name = os.getenv('KB_QUEUE_NAME', 'mantraj_kb_jobs')
            conn = RawRedis(
                host=os.getenv('REDIS_HOST', '127.0.0.1'),
                port=int(os.getenv('REDIS_PORT', '6379')),
                db=int(os.getenv('REDIS_DB', '0')),
                password=os.getenv('REDIS_PASSWORD', None) or None,
                ssl=os.getenv('REDIS_SSL', '').lower() in {'1', 'true', 'yes'},
                decode_responses=False,
                socket_connect_timeout=5,
            )
            queue = Queue(queue_name, connection=conn)
            job = queue.fetch_job(job_id)
            if not job:
                return jsonify({'success': False, 'message': 'Job not found'}), 404
            job.requeue()
            _log_action('queue_retry_job', '', {'job_id': job_id, 'queue_name': queue_name})
            return jsonify({'success': True, 'message': f'Job {job_id} re-queued'})
        except Exception as e:
            return _safe_api_error('Failed to retry queue job', e)

    @admin_bp.route('/api/admin/queue/jobs/<job_id>/cancel', methods=['POST'])
    @require_admin_api
    def admin_cancel_queue_job(job_id):
        try:
            from redis import Redis as RawRedis
            from rq import Queue
            queue_name = os.getenv('KB_QUEUE_NAME', 'mantraj_kb_jobs')
            conn = RawRedis(
                host=os.getenv('REDIS_HOST', '127.0.0.1'),
                port=int(os.getenv('REDIS_PORT', '6379')),
                db=int(os.getenv('REDIS_DB', '0')),
                password=os.getenv('REDIS_PASSWORD', None) or None,
                ssl=os.getenv('REDIS_SSL', '').lower() in {'1', 'true', 'yes'},
                decode_responses=False,
                socket_connect_timeout=5,
            )
            queue = Queue(queue_name, connection=conn)
            job = queue.fetch_job(job_id)
            if not job:
                return jsonify({'success': False, 'message': 'Job not found'}), 404
            job.cancel()
            _log_action('queue_cancel_job', '', {'job_id': job_id, 'queue_name': queue_name})
            return jsonify({'success': True, 'message': f'Job {job_id} canceled'})
        except Exception as e:
            return _safe_api_error('Failed to cancel queue job', e)

    @admin_bp.route('/api/admin/kb-diagnostics/<user_id>', methods=['GET'])
    @require_admin_api
    def admin_kb_diagnostics(user_id):
        """Inspect user KB ingestion stats and run a retrieval probe."""
        if not auth_supabase:
            return jsonify({'success': False, 'message': 'Supabase not configured'}), 500
        if not _is_valid_uuid(user_id):
            return jsonify({'success': False, 'message': 'Invalid user_id'}), 400
        try:
            query = str(request.args.get('query') or 'What are this user\'s top insights?').strip()

            files = auth_supabase.table('kb_files').select(
                'id,filename,status,chunk_count,error_message,created_at,processed_at'
            ).eq('user_id', user_id).order('created_at', desc=True).limit(50).execute().data or []

            file_count = len(files)
            indexed_files = sum(1 for f in files if str(f.get('status') or '').lower() == 'indexed')
            total_chunks = sum(int(f.get('chunk_count') or 0) for f in files)

            embedding_count = 0
            try:
                emb_count_resp = auth_supabase.table('kb_embeddings').select('id', count='exact').eq('user_id', user_id).limit(1).execute()
                embedding_count = int(getattr(emb_count_resp, 'count', 0) or 0)
            except Exception:
                embedding_count = 0

            retrieval = []
            try:
                from rag_system_pgvector import RAGStore
                rag = RAGStore(user_id=user_id)
                matches = rag.hybrid_search(query=query, k=5, min_similarity=0.05) or []
                for m in matches:
                    retrieval.append({
                        'source': m.get('source') or m.get('document_name') or 'unknown',
                        'similarity': round(float(m.get('similarity') or 0.0), 4),
                        'snippet': str(m.get('content') or '')[:280],
                    })
            except Exception as e:
                retrieval = [{'source': 'probe', 'similarity': 0.0, 'snippet': f'Retrieval probe failed: {e}'}]

            return jsonify({
                'success': True,
                'user_id': user_id,
                'stats': {
                    'file_count': file_count,
                    'indexed_files': indexed_files,
                    'total_chunks': total_chunks,
                    'embedding_count': embedding_count,
                },
                'files': files,
                'probe_query': query,
                'retrieval': retrieval,
            })
        except Exception as e:
            return _safe_api_error('Failed to run KB diagnostics', e)

    @admin_bp.route('/api/admin/impersonation/start', methods=['POST'])
    @require_admin_api
    def admin_impersonation_start():
        """Start a read-only impersonation context for support debugging."""
        payload = request.get_json(silent=True) or {}
        user_id = str(payload.get('user_id') or '').strip()
        if not _is_valid_uuid(user_id):
            return jsonify({'success': False, 'message': 'Valid user_id is required'}), 400
        selected = _find_auth_user_by_id(user_id)
        if not selected:
            return jsonify({'success': False, 'message': 'User not found'}), 404
        email = _extract_user_email(selected)
        session['admin_impersonation'] = {
            'user_id': user_id,
            'email': email,
            'mode': 'read_only',
            'started_at': datetime.utcnow().isoformat() + 'Z',
            'started_by': session.get('admin_email', ''),
        }
        _log_action('impersonation_start', user_id, {'mode': 'read_only', 'email': email})
        return jsonify({'success': True, 'impersonation': session.get('admin_impersonation')})

    @admin_bp.route('/api/admin/impersonation/stop', methods=['POST'])
    @require_admin_api
    def admin_impersonation_stop():
        current = session.pop('admin_impersonation', None)
        _log_action('impersonation_stop', (current or {}).get('user_id', ''), {'stopped': bool(current)})
        return jsonify({'success': True, 'stopped': bool(current)})

    @admin_bp.route('/api/admin/impersonation/status', methods=['GET'])
    @require_admin_api
    def admin_impersonation_status():
        return jsonify({'success': True, 'impersonation': session.get('admin_impersonation')})

    @admin_bp.route('/api/admin/impersonation/context', methods=['GET'])
    @require_admin_api
    def admin_impersonation_context():
        ctx = session.get('admin_impersonation') or {}
        user_id = str(ctx.get('user_id') or '').strip()
        if not user_id:
            return jsonify({'success': False, 'message': 'No active impersonation context'}), 404
        try:
            posts = auth_supabase.table('posts').select('id,status,created_at,scheduled_for,posted_at,error_message').eq('user_id', user_id).order('created_at', desc=True).limit(20).execute().data or []
            scheduled = auth_supabase.table('scheduled_posts_v2').select('id,status,scheduled_for,created_at').eq('user_id', user_id).order('created_at', desc=True).limit(20).execute().data or []
            sub = auth_supabase.table('subscriptions').select('*').eq('user_id', user_id).limit(1).execute().data or []
            kb_files = auth_supabase.table('kb_files').select('id,filename,status,chunk_count,created_at').eq('user_id', user_id).order('created_at', desc=True).limit(10).execute().data or []
            return jsonify({
                'success': True,
                'impersonation': ctx,
                'snapshot': {
                    'posts': posts,
                    'scheduled_posts': scheduled,
                    'subscription': sub[0] if sub else {},
                    'kb_files': kb_files,
                },
            })
        except Exception as e:
            return _safe_api_error('Failed to load impersonation context', e)

    @admin_bp.route('/api/admin/incident-controls', methods=['GET'])
    @require_admin_api
    def admin_incident_controls_get():
        try:
            keys = [
                'maintenance_mode',
                'kill_generate_preview',
                'kill_scheduler',
                'kill_kb_training',
                'kill_linkedin_posting',
            ]
            state = {}
            for key in keys:
                row = _get_feature_flag_row(key) or {}
                state[key] = {
                    'enabled': bool(row.get('is_enabled_globally', False)),
                    'config': row.get('config', {}) or {},
                    'updated_at': row.get('updated_at'),
                }
            return jsonify({'success': True, 'controls': state})
        except Exception as e:
            return _safe_api_error('Failed to fetch incident controls', e)

    @admin_bp.route('/api/admin/incident-controls', methods=['POST'])
    @require_admin_api
    def admin_incident_controls_update():
        payload = request.get_json(silent=True) or {}
        controls = payload.get('controls') or {}
        if not isinstance(controls, dict):
            return jsonify({'success': False, 'message': 'controls must be an object'}), 400
        try:
            updated = []
            for key, value in controls.items():
                if key not in {
                    'maintenance_mode',
                    'kill_generate_preview',
                    'kill_scheduler',
                    'kill_kb_training',
                    'kill_linkedin_posting',
                }:
                    continue
                enabled = bool((value or {}).get('enabled', False))
                config = (value or {}).get('config', {}) or {}
                config['updated_by'] = session.get('admin_email', '')
                config['updated_at'] = datetime.utcnow().isoformat() + 'Z'
                if _set_feature_flag(key, enabled, config=config):
                    updated.append({'key': key, 'enabled': enabled})
            _log_action('incident_controls_update', '', {'updated': updated})
            return jsonify({'success': True, 'updated': updated})
        except Exception as e:
            return _safe_api_error('Failed to update incident controls', e)

    @admin_bp.route('/api/admin/maintenance/notify', methods=['POST'])
    @require_admin_api
    def admin_maintenance_notify():
        """Broadcast maintenance upcoming/live emails to selected user scope."""
        payload = request.get_json(silent=True) or {}
        notice_type = str(payload.get('type') or 'upcoming').strip().lower()
        scope = str(payload.get('scope') or 'active').strip().lower()
        subject = str(payload.get('subject') or '').strip()
        message = str(payload.get('message') or '').strip()
        starts_at = str(payload.get('starts_at') or '').strip()
        ends_at = str(payload.get('ends_at') or '').strip()
        if notice_type not in {'upcoming', 'live'}:
            return jsonify({'success': False, 'message': 'type must be upcoming or live'}), 400
        if scope not in {'all', 'active', 'verified'}:
            return jsonify({'success': False, 'message': 'scope must be all, active, or verified'}), 400
        if not message:
            return jsonify({'success': False, 'message': 'message is required'}), 400
        try:
            from notifications import send_email_async, send_maintenance_live_email, send_maintenance_upcoming_email

            recipients = _collect_target_emails(scope=scope)
            if not recipients:
                return jsonify({'success': False, 'message': 'No recipients found for selected scope'}), 404

            if notice_type == 'upcoming':
                mail_subject = subject or 'Scheduled Maintenance Notice'
            else:
                mail_subject = subject or 'Service Restored: CryptoCEN is Live'

            sent = 0
            for email in recipients:
                try:
                    if subject:
                        html = f'<div style="font-family:Arial,sans-serif"><h2>{mail_subject}</h2><p>{message}</p></div>'
                        send_email_async(to_email=email, subject=mail_subject, html_content=html)
                    elif notice_type == 'upcoming':
                        send_maintenance_upcoming_email(to_email=email, message=message, starts_at=starts_at, ends_at=ends_at)
                    else:
                        send_maintenance_live_email(to_email=email, message=message)
                    sent += 1
                except Exception:
                    continue

            _log_action('maintenance_notify', '', {
                'type': notice_type,
                'scope': scope,
                'requested_recipients': len(recipients),
                'sent': sent,
                'subject': mail_subject,
            })
            return jsonify({'success': True, 'sent': sent, 'requested': len(recipients)})
        except Exception as e:
            return _safe_api_error('Failed to send maintenance notice', e)

    return admin_bp
