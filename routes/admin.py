"""Admin panel Blueprint — extracted from app.py monolith (P1-6).

All /admin/* and /api/admin/* routes live here.  The factory function
``create_admin_blueprint`` receives external dependencies (limiter, logger,
data_dir) so the module never imports from app.py, avoiding circular deps.
"""

from __future__ import annotations

import calendar
import hmac
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
        })

    # ── Users CRUD ────────────────────────────────────────────────────────

    @admin_bp.route('/api/admin/users', methods=['GET'])
    @require_admin_api
    def admin_users():
        users = _list_auth_users()
        filtered_users = []
        for u in users:
            if isinstance(u, dict):
                u_obj = u
            else:
                u_obj = getattr(u, 'user', None) or u
            md = (u_obj.get('user_metadata') if isinstance(u_obj, dict) else getattr(u_obj, 'user_metadata', {})) or {}
            if not bool(md.get('soft_deleted')):
                filtered_users.append(u)

        cache_meta = _get_cache_meta()
        auth_configured = bool(auth_supabase)
        subscription_map = {}
        try:
            if auth_supabase:
                subs = auth_supabase.table('subscriptions').select(
                    'user_id,plan,status,current_period_start,current_period_end,cancel_at_period_end'
                ).execute().data or []
                subscription_map = {str(row.get('user_id')): row for row in subs}
        except Exception as e:
            logger.error("Admin users subscription lookup failed: %s", e)

        rows = [_user_to_admin_row(user, subscription_map) for user in filtered_users]
        rows.sort(key=lambda item: item.get('signup_date') or '', reverse=True)
        return jsonify({
            'success': True, 'users': rows,
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
        try:
            if auth_supabase:
                posts = auth_supabase.table('posts').select(
                    'id,content,status,created_at,scheduled_for,posted_at,error_message'
                ).eq('user_id', user_id).order('created_at', desc=True).limit(50).execute().data or []
        except Exception as e:
            logger.error("Admin user details posts lookup failed: %s", e)
        for post in posts:
            post['content_preview'] = (post.get('content') or '')[:180]
        return jsonify({'success': True, 'user': details, 'posts': posts})

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
            current_metadata['is_active'] = active
            attributes = {'user_metadata': current_metadata, 'ban_duration': 'none' if active else '876000h'}
            auth_supabase.auth.admin.update_user_by_id(user_id, attributes)
            _log_action('toggle_user_status', user_id, {'active': active})
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
            auth_supabase.table('subscriptions').upsert({
                'user_id': user_id, 'plan': plan, 'status': 'active',
                'current_period_start': now.isoformat() + 'Z',
                'current_period_end': period_end.isoformat() + 'Z',
                'cancel_at_period_end': False, 'updated_at': now.isoformat() + 'Z',
            }, on_conflict='user_id').execute()
            _log_action('set_subscription_plan', user_id, {'plan': plan, 'months': months})
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
            auth_supabase.table('subscriptions').upsert({
                'user_id': user_id, 'status': 'cancelled',
                'cancel_at_period_end': True, 'updated_at': now,
            }, on_conflict='user_id').execute()
            _log_action('cancel_subscription', user_id, {'cancel_at_period_end': True})
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
            auth_supabase.auth.admin.update_user_by_id(user_id, {'email': new_email})
            _log_action('update_user_email', user_id, {'new_email': new_email})
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

    return admin_bp
