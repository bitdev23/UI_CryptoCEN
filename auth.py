"""
Authentication system for Velank AI
Handles user registration, login, JWT validation
"""

import os
import time
import threading
import requests
from pathlib import Path
from dotenv import load_dotenv, dotenv_values
import jwt
from functools import wraps
from flask import request, jsonify, g
from supabase import create_client, Client
from supabase.lib.client_options import ClientOptions
from typing import Optional, Dict, Tuple, Callable, Any
import logging

# Load environment variables
BASE_DIR = Path(__file__).resolve().parent
_ENV_PATH = BASE_DIR / '.env'
load_dotenv(dotenv_path=_ENV_PATH, override=False)
if _ENV_PATH.exists():
    for _key, _value in dotenv_values(_ENV_PATH).items():
        if _value is None:
            continue
        _current = os.getenv(_key)
        if _current is None or not str(_current).strip():
            os.environ[_key] = _value

logger = logging.getLogger("contentai.auth")

# Initialize Supabase client
supabase_url = os.getenv('SUPABASE_URL')
supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY') or os.getenv('SUPABASE_ANON_KEY')
_supabase_lock = threading.Lock()
supabase: Optional[Client] = None


def _auth_sdk_timeout() -> float:
    raw = (
        os.getenv('AUTH_SDK_TIMEOUT')
        or os.getenv('AUTH_HTTP_TIMEOUT')
        or os.getenv('AUTH_HTTP_READ_TIMEOUT')
        or '30'
    ).strip()
    try:
        return max(5.0, float(raw))
    except Exception:
        return 30.0


def _create_supabase_client() -> Optional[Client]:
    if not supabase_url or not supabase_key:
        logger.warning("SUPABASE_URL or SUPABASE_KEY not set. Auth will not work.")
        return None
    try:
        timeout = _auth_sdk_timeout()
        options = ClientOptions(
            postgrest_client_timeout=timeout,
            storage_client_timeout=max(20.0, timeout)
        )
        return create_client(supabase_url, supabase_key, options=options)
    except Exception as exc:
        logger.error("Failed to initialize Supabase client: %s", exc)
        return None


def _get_supabase_client(force_refresh: bool = False) -> Optional[Client]:
    global supabase
    with _supabase_lock:
        if force_refresh or supabase is None:
            supabase = _create_supabase_client()
        return supabase


def _run_supabase_with_recovery(operation: Callable[[Client], Any], operation_name: str):
    client = _get_supabase_client()
    if not client:
        raise RuntimeError("Supabase client not initialized")

    try:
        return _run_with_retries(lambda: operation(client), operation_name)
    except Exception as exc:
        if not _is_timeout_error(exc):
            raise
        logger.warning("%s timed out using existing Supabase client. Recreating client and retrying once.", operation_name)
        refreshed = _get_supabase_client(force_refresh=True)
        if not refreshed:
            raise
        return _run_with_retries(lambda: operation(refreshed), f"{operation_name} (refreshed)")


_get_supabase_client(force_refresh=True)


def _build_email_redirect_url() -> str:
    """Build callback URL used in Supabase email verification links."""
    explicit = (os.getenv('AUTH_REDIRECT_URL') or '').strip()
    if explicit:
        return explicit

    base_url = (os.getenv('APP_BASE_URL') or 'http://127.0.0.1:5050').strip().rstrip('/')
    return f"{base_url}/auth/callback"


def _build_password_reset_redirect_url() -> str:
    """Build callback URL used in Supabase password recovery emails."""
    explicit = (os.getenv('AUTH_RESET_REDIRECT_URL') or '').strip()
    if explicit:
        return explicit

    base_url = (os.getenv('APP_BASE_URL') or 'http://127.0.0.1:5050').strip().rstrip('/')
    return f"{base_url}/auth/reset-callback?type=recovery"


def _is_timeout_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    timeout_terms = ['timed out', 'timeout', 'read timeout', 'connect timeout']
    return any(term in msg for term in timeout_terms)


def _run_with_retries(operation: Callable[[], Any], operation_name: str, attempts: int = 3, delay_sec: float = 1.2):
    try:
        attempts = int((os.getenv('AUTH_RETRY_ATTEMPTS') or attempts))
    except Exception:
        attempts = attempts
    try:
        delay_sec = float((os.getenv('AUTH_RETRY_DELAY_SEC') or delay_sec))
    except Exception:
        delay_sec = delay_sec

    attempts = max(1, attempts)
    delay_sec = max(0.2, delay_sec)

    last_error = None
    for attempt in range(1, attempts + 1):
        try:
            return operation()
        except Exception as exc:
            last_error = exc
            if not _is_timeout_error(exc) or attempt == attempts:
                break
            logger.warning("%s timed out (attempt %d/%d). Retrying...", operation_name, attempt, attempts)
            time.sleep(delay_sec * attempt)

    if last_error:
        raise last_error
    raise RuntimeError(f"{operation_name} failed")


def _auth_api_key() -> str:
    return (os.getenv('SUPABASE_ANON_KEY') or os.getenv('SUPABASE_KEY') or '').strip()


def _auth_http_configured() -> bool:
    return bool((supabase_url or '').strip() and _auth_api_key())


def _auth_base_urls() -> list:
    urls = []
    primary = (supabase_url or '').strip()
    if primary:
        urls.append(primary.rstrip('/'))

    fallback_raw = (os.getenv('SUPABASE_AUTH_FALLBACK_URLS') or '').strip()
    if fallback_raw:
        for candidate in fallback_raw.split(','):
            value = candidate.strip().rstrip('/')
            if value and value not in urls:
                urls.append(value)
    return urls


def _auth_prefer_http() -> bool:
    raw = (os.getenv('AUTH_PREFER_HTTP') or 'true').strip().lower()
    return raw in {'1', 'true', 'yes', 'on'}


def _auth_headers() -> Dict[str, str]:
    api_key = _auth_api_key()
    return {
        'apikey': api_key,
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
        'Connection': 'close'
    }


def _auth_http_connect_timeout() -> float:
    raw = (os.getenv('AUTH_HTTP_CONNECT_TIMEOUT') or '10').strip()
    try:
        return max(2.0, float(raw))
    except Exception:
        return 10.0


def _auth_http_read_timeout() -> float:
    raw = (os.getenv('AUTH_HTTP_READ_TIMEOUT') or '20').strip()
    try:
        return max(5.0, float(raw))
    except Exception:
        return 20.0


def _auth_http_timeout(multiplier: float = 1.0):
    connect_timeout = _auth_http_connect_timeout()
    growth = 1.0 + (max(1.0, multiplier) - 1.0) * 0.25
    read_timeout = min(60.0, _auth_http_read_timeout() * growth)
    return (connect_timeout, read_timeout)


def _auth_warmup_attempts() -> int:
    raw = (os.getenv('AUTH_WARMUP_ATTEMPTS') or '2').strip()
    try:
        return max(1, int(raw))
    except Exception:
        return 2


def _auth_warmup_delay_sec() -> float:
    raw = (os.getenv('AUTH_WARMUP_DELAY_SEC') or '1.5').strip()
    try:
        return max(0.2, float(raw))
    except Exception:
        return 1.5


def auth_healthcheck() -> Tuple[bool, str]:
    if not _auth_http_configured():
        return False, 'Auth HTTP path not configured'

    urls = _auth_base_urls()
    if not urls:
        return False, 'No auth base URL configured'

    attempts = _auth_warmup_attempts()
    delay_sec = _auth_warmup_delay_sec()
    last_error = ''

    for base_url in urls:
        endpoint = f"{base_url}/auth/v1/settings"
        for attempt in range(1, attempts + 1):
            try:
                response = requests.get(
                    endpoint,
                    headers={
                        'apikey': _auth_api_key(),
                        'Authorization': f"Bearer {_auth_api_key()}",
                        'Connection': 'close'
                    },
                    timeout=_auth_http_timeout(multiplier=1.0)
                )
                if response.status_code < 500:
                    return True, f"auth settings reachable via {base_url} ({response.status_code})"
                last_error = f"{base_url} status {response.status_code}"
            except Exception as exc:
                last_error = f"{base_url}: {exc}"

            if attempt < attempts:
                time.sleep(delay_sec * attempt)

    return False, f"auth settings unreachable: {last_error or 'unknown error'}"


def _warm_auth_service(operation_name: str = 'Auth') -> bool:
    ok, detail = auth_healthcheck()
    if ok:
        logger.info("%s pre-warm succeeded: %s", operation_name, detail)
        return True
    logger.warning("%s pre-warm failed: %s", operation_name, detail)
    return False


def _post_json_with_retries(url: str, payload: Dict[str, Any], operation_name: str) -> Optional[requests.Response]:
    attempts_raw = (os.getenv('AUTH_HTTP_RETRIES') or '3').strip()
    delay_raw = (os.getenv('AUTH_HTTP_RETRY_DELAY_SEC') or '1.0').strip()
    try:
        attempts = max(1, int(attempts_raw))
    except Exception:
        attempts = 3
    try:
        delay_sec = max(0.2, float(delay_raw))
    except Exception:
        delay_sec = 1.0

    last_error: Optional[Exception] = None
    last_response: Optional[requests.Response] = None
    for attempt in range(1, attempts + 1):
        try:
            response = requests.post(
                url,
                headers=_auth_headers(),
                json=payload,
                timeout=_auth_http_timeout(multiplier=float(attempt))
            )
            last_response = response
            if response.status_code >= 500 and attempt < attempts:
                logger.warning(
                    "%s HTTP fallback got %d (attempt %d/%d). Retrying...",
                    operation_name,
                    response.status_code,
                    attempt,
                    attempts
                )
                time.sleep(delay_sec * attempt)
                continue
            return response
        except Exception as exc:
            last_error = exc
            if not _is_timeout_error(exc) or attempt == attempts:
                break
            if attempt == 1:
                _warm_auth_service(f"{operation_name} HTTP fallback")
            logger.warning("%s HTTP fallback timed out (attempt %d/%d). Retrying...", operation_name, attempt, attempts)
            time.sleep(delay_sec * attempt)

    if last_error:
        logger.error("%s HTTP fallback failed: %s", operation_name, last_error)
    return last_response


def _fallback_signup(email: str, password: str, metadata: Dict, redirect_to: str) -> Optional[Dict[str, Any]]:
    base_urls = _auth_base_urls()
    if not base_urls:
        return None
    try:
        payload = {
            'email': email,
            'password': password,
            'data': metadata,
            'email_redirect_to': redirect_to
        }
        for base_url in base_urls:
            response = _post_json_with_retries(
                f"{base_url}/auth/v1/signup",
                payload,
                f'Signup ({base_url})'
            )
            if response is None:
                continue
            if response.status_code >= 400:
                logger.error("HTTP fallback signup failed (%s): %s", base_url, response.text)
                continue
            return response.json() if response.content else None
        return None
    except Exception as exc:
        logger.error("HTTP fallback signup exception: %s", exc)
        return None


def _fallback_login(email: str, password: str) -> Optional[Dict[str, Any]]:
    base_urls = _auth_base_urls()
    if not base_urls:
        return None
    try:
        payload = {
            'email': email,
            'password': password
        }
        for base_url in base_urls:
            response = _post_json_with_retries(
                f"{base_url}/auth/v1/token?grant_type=password",
                payload,
                f'Login ({base_url})'
            )
            if response is None:
                continue
            if response.status_code >= 400:
                logger.error("HTTP fallback login failed (%s): %s", base_url, response.text)
                continue
            return response.json() if response.content else None
        return None
    except Exception as exc:
        logger.error("HTTP fallback login exception: %s", exc)
        return None


def _fallback_login_response(email: str, password: str) -> Tuple[Optional[Dict[str, Any]], Optional[int], str]:
    base_urls = _auth_base_urls()
    if not base_urls:
        return None, None, 'Supabase URL missing'
    payload = {
        'email': email,
        'password': password
    }
    last_raw = 'timeout'

    for base_url in base_urls:
        response = _post_json_with_retries(
            f"{base_url}/auth/v1/token?grant_type=password",
            payload,
            f'Login ({base_url})'
        )
        if response is None:
            last_raw = f"timeout ({base_url})"
            continue

        body: Optional[Dict[str, Any]] = None
        try:
            body = response.json() if response.content else {}
        except Exception:
            body = {}

        response_text = ''
        try:
            response_text = response.text or ''
        except Exception:
            response_text = ''

        return body, response.status_code, response_text

    return None, None, last_raw


def require_auth(f):
    """
    Decorator to protect routes that require authentication
    Extracts user_id from JWT token and sets g.user_id
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization')

        # In TEST_MODE, allow fallback user only in local dev (never in production).
        # Production is detected via FLASK_ENV=production in .env (loaded by systemd EnvironmentFile).
        if os.getenv('TEST_MODE') == 'true' and not auth_header and os.getenv('FLASK_ENV') != 'production':
            g.user_id = os.getenv('TEST_USER_ID', '00000000-0000-0000-0000-000000000000')
            g.user_email = 'test@example.com'
            g.user = {
                'id': g.user_id,
                'email': g.user_email,
                'first_name': 'Test',
                'last_name': 'User',
                'country': ''
            }
            return f(*args, **kwargs)
        
        if not auth_header:
            return jsonify({'error': 'Missing authorization header'}), 401
        
        try:
            # Extract token (format: "Bearer <token>")
            scheme, token = auth_header.split()
            
            if scheme.lower() != 'bearer':
                return jsonify({'error': 'Invalid authorization scheme'}), 401
            
            # Verify token with Supabase
            user = verify_token(token)
            
            if not user:
                return jsonify({'error': 'Invalid or expired token'}), 401
            
            # Set user context
            g.user_id = user['id']
            g.user_email = user.get('email')
            g.user = user
            
            return f(*args, **kwargs)
            
        except ValueError:
            return jsonify({'error': 'Invalid authorization header format'}), 401
        except Exception as e:
            logger.error(f"Auth error: {e}")
            return jsonify({'error': 'Authentication failed'}), 401
    
    return decorated_function


def verify_token(token: str) -> Optional[Dict]:
    """
    Verify JWT token with Supabase.

    Always uses a direct stateless HTTP call to /auth/v1/user.  The Supabase
    Python SDK is intentionally avoided here: it holds mutable internal session
    state that becomes corrupted when verify_token is called concurrently from
    multiple threads (which happens every time the dashboard loads).

    Returns:
        User dict if valid, None otherwise
    """

    def _http_verify() -> Optional[Dict]:
        """Call /auth/v1/user directly via requests — stateless and thread-safe."""
        base_urls = _auth_base_urls()
        for base_url in base_urls:
            try:
                response = requests.get(
                    f"{base_url}/auth/v1/user",
                    headers={
                        'apikey': _auth_api_key(),
                        'Authorization': f'Bearer {token}',
                        'Content-Type': 'application/json',
                        'Connection': 'close'
                    },
                    timeout=_auth_http_timeout(multiplier=1.0)
                )
                if response.status_code >= 400:
                    # 401 means the token itself is invalid — log at debug level only
                    if response.status_code == 401:
                        logger.debug("Token verification: Supabase returned 401 (invalid/expired token)")
                    else:
                        logger.warning(
                            "Token verification HTTP returned %d via %s",
                            response.status_code, base_url
                        )
                    # Don't try the next URL for auth errors — token is the same everywhere
                    if response.status_code in (400, 401, 403):
                        return None
                    continue
                payload = response.json() if response.content else {}
                user_id = payload.get('id', '')
                if not user_id:
                    logger.warning("Token verification: Supabase returned 200 but no user id")
                    continue
                metadata = payload.get('user_metadata') or {}
                # Try to infer auth provider from identities or app_metadata
                provider = ''
                try:
                    identities = payload.get('identities') or []
                    if isinstance(identities, list) and len(identities) > 0:
                        first = identities[0] or {}
                        provider = first.get('provider') or ''
                except Exception:
                    provider = ''

                if not provider:
                    provider = (payload.get('app_metadata') or {}).get('provider') or metadata.get('auth_provider') or ''

                return {
                    'id': user_id,
                    'email': payload.get('email', ''),
                    'first_name': metadata.get('first_name', ''),
                    'last_name': metadata.get('last_name', ''),
                    'country': metadata.get('country', ''),
                    'email_confirmed_at': payload.get('email_confirmed_at'),
                    'created_at': payload.get('created_at'),
                    'updated_at': payload.get('updated_at'),
                    'auth_provider': provider or metadata.get('auth_provider', '')
                }
            except Exception as http_exc:
                logger.warning("Token verification HTTP failed via %s: %s", base_url, http_exc)
        return None

    # ── When HTTP is configured use only the stateless HTTP path ──────────────
    # Never invoke the Supabase SDK here: it maintains shared session state that
    # gets corrupted when called concurrently from multiple request threads.
    if _auth_http_configured():
        return _http_verify()

    # ── SDK fallback — only reached when SUPABASE_URL / ANON_KEY are missing ──
    logger.warning("verify_token: HTTP path not available, falling back to SDK")
    try:
        client = _get_supabase_client()
        if not client:
            logger.error("Supabase client not initialized and HTTP not configured")
            return None

        user = _run_supabase_with_recovery(
            lambda c: c.auth.get_user(token), 'Token verification (SDK)'
        )

        if user and user.user:
            metadata = getattr(user.user, 'user_metadata', {}) or {}
            return {
                'id': user.user.id,
                'email': user.user.email,
                'first_name': metadata.get('first_name', ''),
                'last_name': metadata.get('last_name', ''),
                'country': metadata.get('country', ''),
                'email_confirmed_at': user.user.email_confirmed_at,
                'created_at': user.user.created_at,
                'updated_at': user.user.updated_at
            }
        return None

    except Exception as e:
        logger.error("Token verification (SDK) failed: %s", e)
        return None


def signup_user(email: str, password: str, metadata: Optional[Dict] = None) -> Tuple[bool, str, Optional[Dict]]:
    """
    Sign up a new user
    
    Returns:
        (success, message, user_data)
    """
    try:
        if not _get_supabase_client() and not _auth_http_configured():
            return False, "Authentication service not configured", None

        redirect_to = _build_email_redirect_url()

        # Sign up with Supabase
        user_metadata = metadata or {}
        # Record that this account was created with email/password
        try:
            if isinstance(user_metadata, dict):
                user_metadata['auth_provider'] = user_metadata.get('auth_provider') or 'email'
        except Exception:
            pass

        response = _run_supabase_with_recovery(lambda client: client.auth.sign_up({
            'email': email,
            'password': password,
            'options': {
                'data': user_metadata,
                'email_redirect_to': redirect_to
            }
        }), 'Signup')

        # Normalize response to user object/dict
        user_obj = None
        if response is not None:
            user_obj = getattr(response, 'user', None)
            if user_obj is None and isinstance(response, dict):
                user_obj = response.get('user')

        if user_obj:
            logger.info(f"User signed up: {email}")
            # user_obj may be an SDK object or a dict
            uid = getattr(user_obj, 'id', None) or (user_obj.get('id') if isinstance(user_obj, dict) else '')
            uemail = getattr(user_obj, 'email', None) or (user_obj.get('email') if isinstance(user_obj, dict) else email)
            return True, "Signup successful. Please verify your email to continue.", {
                'id': uid,
                'email': uemail,
                'first_name': user_metadata.get('first_name', ''),
                'last_name': user_metadata.get('last_name', ''),
                'country': user_metadata.get('country', ''),
                'role': user_metadata.get('role', ''),
                'industry': user_metadata.get('industry', ''),
                'auth_provider': user_metadata.get('auth_provider', 'email')
            }

        return False, "Signup failed", None

    except Exception as e:
        logger.error(f"Signup error: {e}")
        error_msg = str(e)

        if _is_timeout_error(e):
            fallback_data = _fallback_signup(email, password, metadata or {}, _build_email_redirect_url())
            if fallback_data and fallback_data.get('user'):
                user_obj = fallback_data.get('user') or {}
                md = metadata or {}
                return True, "Signup successful. Please verify your email to continue.", {
                    'id': user_obj.get('id', ''),
                    'email': user_obj.get('email', email),
                    'first_name': md.get('first_name', ''),
                    'last_name': md.get('last_name', ''),
                    'country': md.get('country', ''),
                    'role': md.get('role', ''),
                    'industry': md.get('industry', ''),
                    'auth_provider': md.get('auth_provider', 'email')
                }
            return False, "Authentication service temporarily unavailable (timeout). Please try again in a moment.", None

        if 'already registered' in error_msg.lower():
            return False, "Email already registered", None
        elif 'password' in error_msg.lower():
            return False, "Password does not meet requirements", None
        else:
            return False, f"Signup failed: {error_msg}", None



def check_user_oauth_only(email: str) -> Tuple[bool, list]:
    """
    Check if a user account exists but only has OAuth methods (no email/password).
    
    Args:
        email: User's email address
        
    Returns:
        (is_oauth_only, linked_providers_list)
        Where is_oauth_only=True means user exists but can't login with password
    """
    logger.info(f"[OAUTH_CHECK] Starting check for email: {email}")
    try:
        # Use Supabase Admin API via HTTP to check user identities
        service_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY', '').strip()
        supabase_url = os.getenv('SUPABASE_URL', '').strip().rstrip('/')
        
        logger.info(f"[OAUTH_CHECK] Config - Service key present: {bool(service_key)}, URL: {bool(supabase_url)}")
        
        if not service_key or not supabase_url:
            logger.info("[OAUTH_CHECK] Missing service key or URL, returning False")
            return False, []
        
        # Query the admin API to get user by email
        admin_url = f"{supabase_url}/auth/v1/admin/users?email={email}"
        logger.info(f"[OAUTH_CHECK] Calling Admin API...")
        
        response = requests.get(
            admin_url,
            headers={
                'Authorization': f'Bearer {service_key}',
                'apikey': os.getenv('SUPABASE_ANON_KEY', service_key),
                'Content-Type': 'application/json'
            },
            timeout=5.0
        )
        
        logger.info(f"[OAUTH_CHECK] Admin API status: {response.status_code}")
        
        if response.status_code != 200:
            logger.error(f"[OAUTH_CHECK] API failed (status {response.status_code}). Response: {response.text[:200]}")
            return False, []
        
        data = response.json()
        users = data.get('users', [])
        logger.info(f"[OAUTH_CHECK] Found {len(users)} user(s)")
        logger.info(f"[OAUTH_CHECK] Full response: {data}")
        
        if not users or len(users) == 0:
            logger.info(f"[OAUTH_CHECK] No user found, returning False")
            return False, []
        
        # Find the user matching the email address (don't just take first one)
        user = None
        for u in users:
            if u.get('email', '').lower() == email.lower():
                user = u
                logger.info(f"[OAUTH_CHECK] Found matching user: {u.get('email')}")
                break
        
        if not user:
            logger.info(f"[OAUTH_CHECK] No user found matching email {email}. Users in response: {[u.get('email') for u in users]}")
            return False, []
        
        # Try to get providers from two possible locations:
        # 1. app_metadata.providers (Supabase stores this)
        # 2. identities array (fallback)
        
        providers = []
        app_metadata = user.get('app_metadata', {}) or {}
        
        # First try app_metadata.providers (more reliable)
        if app_metadata.get('providers'):
            providers = app_metadata.get('providers', [])
            logger.info(f"[OAUTH_CHECK] Got providers from app_metadata.providers: {providers}")
        else:
            # Fallback to identities array
            identities = user.get('identities', [])
            logger.info(f"[OAUTH_CHECK] Raw identities for {email}: {identities}")
            
            if isinstance(identities, list):
                for identity in identities:
                    if isinstance(identity, dict):
                        provider = identity.get('provider', '').lower()
                        if provider:
                            providers.append(provider)
            logger.info(f"[OAUTH_CHECK] Extracted providers from identities: {providers}")
        
        has_email_provider = 'email' in [p.lower() for p in providers]
        logger.info(f"[OAUTH_CHECK] Providers: {providers}, has_email: {has_email_provider}")
        
        # If user exists but doesn't have email provider, they can't login with password
        is_oauth_only = len(providers) > 0 and not has_email_provider
        logger.info(f"[OAUTH_CHECK] Result: is_oauth_only={is_oauth_only}, providers={providers}")
        
        return is_oauth_only, providers
        
    except requests.RequestException as e:
        logger.error(f"[OAUTH_CHECK] HTTP request failed: {e}")
        return False, []
    except Exception as e:
        logger.error(f"[OAUTH_CHECK] Exception: {e}", exc_info=True)
        return False, []


def login_user(email: str, password: str) -> Tuple[bool, str, Optional[Dict]]:
    """
    Log in a user
    
    Returns:
        (success, message, auth_data)
        auth_data contains: access_token, refresh_token, user
    """
    try:
        has_http = _auth_http_configured()
        has_sdk = _get_supabase_client() is not None

        if not has_sdk and not has_http:
            return False, "Authentication service not configured", None

        prewarm_enabled = (os.getenv('AUTH_PREWARM_ON_LOGIN') or 'true').strip().lower() in {'1', 'true', 'yes', 'on'}
        if has_http and prewarm_enabled:
            _warm_auth_service('Login')

        def _build_success_from_payload(payload: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
            user_obj = payload.get('user') or {}
            user_metadata = user_obj.get('user_metadata') or {}
            return True, "Login successful", {
                'access_token': payload.get('access_token'),
                'refresh_token': payload.get('refresh_token'),
                'expires_in': payload.get('expires_in'),
                'user': {
                    'id': user_obj.get('id', ''),
                    'email': user_obj.get('email', email),
                    'first_name': user_metadata.get('first_name', ''),
                    'last_name': user_metadata.get('last_name', ''),
                    'country': user_metadata.get('country', ''),
                    'role': user_metadata.get('role', ''),
                    'industry': user_metadata.get('industry', '')
                }
            }

        def _try_http_login() -> Tuple[bool, str, Optional[Dict], Optional[int], str]:
            body, status_code, raw_text = _fallback_login_response(email, password)
            if status_code and status_code < 400 and body and body.get('access_token'):
                logger.info(f"User logged in (HTTP): {email}")
                ok, msg, data = _build_success_from_payload(body)
                return ok, msg, data, status_code, raw_text

            if status_code in {400, 401, 403}:
                lowered = str((body or {}).get('error_description') or (body or {}).get('msg') or (body or {}).get('error') or '').lower()
                if 'invalid' in lowered or 'credentials' in lowered or 'grant' in lowered:
                    return False, "Invalid email or password", None, status_code, raw_text
                if 'not confirmed' in lowered or 'email not confirmed' in lowered:
                    return False, "Please verify your email before logging in", None, status_code, raw_text
                return False, (body or {}).get('error_description') or (body or {}).get('msg') or "Login failed", None, status_code, raw_text

            return False, "Authentication service temporarily unavailable (timeout). Please try again in a moment.", None, status_code, raw_text

        if _auth_prefer_http() and has_http:
            success, message, auth_data, status_code, raw_text = _try_http_login()
            if success:
                return success, message, auth_data

            if status_code in {400, 401, 403}:
                # Check if this is an OAuth-only account before returning generic error
                logger.info(f"[LOGIN_HTTP_ERROR] HTTP login failed with status {status_code}. Message: {message}")
                if 'invalid' in message.lower() or 'credentials' in message.lower():
                    logger.info(f"[LOGIN_HTTP_ERROR] Credential error detected, checking if OAuth-only account...")
                    is_oauth_only, oauth_providers = check_user_oauth_only(email)
                    logger.info(f"[LOGIN_HTTP_ERROR] OAuth check result: is_oauth_only={is_oauth_only}, providers={oauth_providers}")
                    
                    if is_oauth_only and oauth_providers:
                        provider_names = ', '.join(oauth_providers).title()
                        return False, f"no_password|This account was created with {provider_names} and has no password. Please log in with {provider_names} or reset your password.", None
                
                return False, message, None

            logger.warning("HTTP login path failed (status=%s). Attempting SDK fallback.", status_code)
            if has_sdk:
                try:
                    response = _run_supabase_with_recovery(lambda client: client.auth.sign_in_with_password({
                        'email': email,
                        'password': password
                    }), 'Login SDK fallback')
                    if response.user and response.session:
                        logger.info(f"User logged in (SDK fallback): {email}")
                        return True, "Login successful", {
                            'access_token': response.session.access_token,
                            'refresh_token': response.session.refresh_token,
                            'expires_in': response.session.expires_in,
                            'user': {
                                'id': response.user.id,
                                'email': response.user.email,
                                'first_name': (getattr(response.user, 'user_metadata', {}) or {}).get('first_name', ''),
                                'last_name': (getattr(response.user, 'user_metadata', {}) or {}).get('last_name', ''),
                                'country': (getattr(response.user, 'user_metadata', {}) or {}).get('country', ''),
                                'role': (getattr(response.user, 'user_metadata', {}) or {}).get('role', ''),
                                'industry': (getattr(response.user, 'user_metadata', {}) or {}).get('industry', '')
                            }
                        }
                except Exception as sdk_exc:
                    logger.error("SDK fallback login failed after HTTP path failure: %s", sdk_exc)

            logger.error("Login HTTP path failed without successful SDK fallback. Raw: %s", raw_text[:300] if raw_text else 'N/A')
            return False, "Authentication service temporarily unavailable (timeout). Please try again in a moment.", None

        if not _get_supabase_client():
            return False, "Authentication service temporarily unavailable", None
        
        # Sign in with Supabase SDK first (default path)
        response = _run_supabase_with_recovery(lambda client: client.auth.sign_in_with_password({
            'email': email,
            'password': password
        }), 'Login')
        
        if response.user and response.session:
            user_metadata = getattr(response.user, 'user_metadata', {}) or {}
            logger.info(f"User logged in: {email}")
            return True, "Login successful", {
                'access_token': response.session.access_token,
                'refresh_token': response.session.refresh_token,
                'expires_in': response.session.expires_in,
                'user': {
                    'id': response.user.id,
                    'email': response.user.email,
                    'first_name': user_metadata.get('first_name', ''),
                    'last_name': user_metadata.get('last_name', ''),
                    'country': user_metadata.get('country', '')
                }
            }
        else:
            return False, "Login failed", None
            
    except Exception as e:
        logger.error(f"Login error: {e}")
        error_msg = str(e)

        if _is_timeout_error(e):
            if _auth_http_configured():
                _warm_auth_service('Login timeout recovery')
                fallback_data = _fallback_login(email, password)
                if fallback_data and fallback_data.get('access_token'):
                    user_obj = fallback_data.get('user') or {}
                    user_metadata = user_obj.get('user_metadata') or {}
                    return True, "Login successful", {
                        'access_token': fallback_data.get('access_token'),
                        'refresh_token': fallback_data.get('refresh_token'),
                        'expires_in': fallback_data.get('expires_in'),
                        'user': {
                            'id': user_obj.get('id', ''),
                            'email': user_obj.get('email', email),
                            'first_name': user_metadata.get('first_name', ''),
                            'last_name': user_metadata.get('last_name', ''),
                            'country': user_metadata.get('country', '')
                        }
                    }
            return False, "Authentication service temporarily unavailable (timeout). Please try again in a moment.", None
        
        logger.info(f"[LOGIN_ERROR] Error message: {error_msg[:100]}")
        logger.info(f"[LOGIN_ERROR] Contains 'invalid': {'invalid' in error_msg.lower()}")
        logger.info(f"[LOGIN_ERROR] Contains 'credentials': {'credentials' in error_msg.lower()}")
        logger.info(f"[LOGIN_ERROR] Contains 'unauthorized': {'unauthorized' in error_msg.lower()}")
        
        # Check for invalid credentials (covers 'invalid', 'credentials', 'unauthorized')
        if any(x in error_msg.lower() for x in ['invalid', 'credentials', 'unauthorized', 'failed']):
            logger.info(f"[LOGIN_ERROR] Matched error pattern, checking if OAuth-only account...")
            # Check if user exists but only has OAuth (no password set)
            is_oauth_only, oauth_providers = check_user_oauth_only(email)
            
            logger.info(f"[LOGIN_ERROR] OAuth check result: is_oauth_only={is_oauth_only}, providers={oauth_providers}")
            
            if is_oauth_only and oauth_providers:
                # User exists but has no password - suggest OAuth login or reset
                provider_names = ', '.join(oauth_providers).title()
                return False, f"no_password|This account was created with {provider_names} and has no password. Please log in with {provider_names} or reset your password.", None
            
            return False, "Invalid email or password", None
        elif 'not confirmed' in error_msg.lower():
            return False, "Please verify your email before logging in", None
        else:
            return False, f"Login failed: {error_msg}", None


def logout_user(token: str) -> Tuple[bool, str]:
    """
    Log out a user (invalidate token)
    
    Returns:
        (success, message)
    """
    try:
        client = _get_supabase_client()
        if not client:
            return False, "Authentication service not configured"
        
        client.auth.sign_out()
        return True, "Logout successful"
        
    except Exception as e:
        logger.error(f"Logout error: {e}")
        return False, f"Logout failed: {str(e)}"


def request_password_reset(email: str) -> Tuple[bool, str]:
    """
    Send password reset email
    
    Returns:
        (success, message)
    """
    try:
        client = _get_supabase_client()
        if not client:
            return False, "Authentication service not configured"

        redirect_to = _build_password_reset_redirect_url()
        try:
            client.auth.reset_password_email(email, {'redirect_to': redirect_to})
        except TypeError:
            # SDK compatibility fallback for versions expecting kwargs
            client.auth.reset_password_email(email, redirect_to=redirect_to)
        return True, "Password reset email sent. Please check your inbox."
        
    except Exception as e:
        logger.error(f"Password reset error: {e}")
        return False, f"Failed to send reset email: {str(e)}"


def update_password(token: str, new_password: str) -> Tuple[bool, str]:
    """
    Update user password
    
    Returns:
        (success, message)
    """
    try:
        client = _get_supabase_client()
        if not client:
            return False, "Authentication service not configured"
        
        # Verify token first
        user = verify_token(token)
        if not user:
            return False, "Invalid or expired token"
        
        # Update password
        client.auth.update_user({
            'password': new_password
        })
        
        return True, "Password updated successfully"
        
    except Exception as e:
        logger.error(f"Password update error: {e}")
        return False, f"Failed to update password: {str(e)}"


def resend_verification_email(email: str) -> Tuple[bool, str]:
    """
    Resend email verification
    
    Returns:
        (success, message)
    """
    try:
        client = _get_supabase_client()
        if not client:
            return False, "Authentication service not configured"
        
        # Supabase automatically resends verification when user signs up again
        # Or you can use the resend API
        client.auth.resend({
            'type': 'signup',
            'email': email
        })
        
        return True, "Verification email sent"
        
    except Exception as e:
        logger.error(f"Resend verification error: {e}")
        return False, f"Failed to resend verification: {str(e)}"


def get_current_user(token: str) -> Optional[Dict]:
    """
    Get current user info from token
    
    Returns:
        User dict or None
    """
    return verify_token(token)


def refresh_access_token(refresh_token: str) -> Tuple[bool, str, Optional[Dict]]:
    """
    Refresh access token using refresh token
    
    Returns:
        (success, message, auth_data)
    """
    def _from_payload(payload: Dict[str, Any]) -> Tuple[bool, str, Optional[Dict]]:
        if not payload or not payload.get('access_token'):
            return False, "Failed to refresh token", None
        return True, "Token refreshed", {
            'access_token': payload.get('access_token'),
            'refresh_token': payload.get('refresh_token') or refresh_token,
            'expires_in': payload.get('expires_in')
        }

    def _http_refresh() -> Tuple[bool, str, Optional[Dict]]:
        base_urls = _auth_base_urls()
        if not base_urls:
            return False, "Authentication service not configured", None

        payload = {'refresh_token': refresh_token}
        last_message = 'Failed to refresh token'
        for base_url in base_urls:
            response = _post_json_with_retries(
                f"{base_url}/auth/v1/token?grant_type=refresh_token",
                payload,
                f"Refresh token ({base_url})"
            )
            if response is None:
                continue

            body = {}
            try:
                body = response.json() if response.content else {}
            except Exception:
                body = {}

            if response.status_code < 400:
                return _from_payload(body)

            last_message = (
                str(body.get('error_description') or body.get('msg') or body.get('error') or '').strip()
                or f"Refresh failed ({response.status_code})"
            )

        return False, last_message, None

    try:
        if _auth_prefer_http() and _auth_http_configured():
            ok, msg, data = _http_refresh()
            if ok:
                return ok, msg, data

        client = _get_supabase_client()
        if client:
            try:
                response = _run_supabase_with_recovery(
                    lambda active_client: active_client.auth.refresh_session(refresh_token),
                    'Refresh token'
                )
                if response and response.session:
                    return True, "Token refreshed", {
                        'access_token': response.session.access_token,
                        'refresh_token': response.session.refresh_token or refresh_token,
                        'expires_in': response.session.expires_in
                    }
            except Exception as sdk_error:
                logger.warning("SDK refresh failed, trying HTTP refresh fallback: %s", sdk_error)

        if _auth_http_configured():
            return _http_refresh()

        return False, "Authentication service not configured", None
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        return False, f"Failed to refresh token: {str(e)}", None


# Optional: Admin check decorator
def require_admin(f):
    """
    Decorator to protect admin-only routes
    Requires user to be authenticated AND have admin role
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # First check authentication
        auth_header = request.headers.get('Authorization')
        
        if not auth_header:
            return jsonify({'error': 'Missing authorization header'}), 401
        
        try:
            scheme, token = auth_header.split()
            
            if scheme.lower() != 'bearer':
                return jsonify({'error': 'Invalid authorization scheme'}), 401
            
            user = verify_token(token)
            
            if not user:
                return jsonify({'error': 'Invalid or expired token'}), 401
            
            # Check if user is admin (you can customize this logic)
            # For now, check if email matches admin email from env
            admin_email = os.getenv('ADMIN_EMAIL', 'admin@yourdomain.com')
            
            if user.get('email') != admin_email:
                return jsonify({'error': 'Admin access required'}), 403
            
            g.user_id = user['id']
            g.user_email = user['email']
            g.user = user
            g.is_admin = True
            
            return f(*args, **kwargs)
            
        except Exception as e:
            logger.error(f"Admin auth error: {e}")
            return jsonify({'error': 'Authentication failed'}), 401
    
    return decorated_function


# ============================================================================
# ACCOUNT LINKING FUNCTIONS
# Allow users to authenticate with multiple methods (email/password + OAuth)
# ============================================================================

def find_existing_user_by_email(email: str) -> Optional[Dict]:
    """
    Find an existing user by email across all linked identities
    
    Returns:
        User dict if found, None otherwise
    """
    try:
        if not _auth_http_configured():
            return None
        
        # Query the find_user_by_email function
        client = _get_supabase_client()
        if not client:
            return None
        
        result = _run_supabase_with_recovery(
            lambda c: c.rpc('find_user_by_email', {'p_email': email}),
            'Find user by email'
        )
        
        if result:
            user_id = result
            # Now fetch the full user data from Supabase
            # Note: This would require service role key
            logger.debug(f"Found existing user for email {email}: {user_id}")
            return {'id': user_id, 'email': email}
        
        return None
    except Exception as e:
        logger.debug(f"Could not find user by email {email}: {e}")
        return None


def check_if_identity_linked(provider: str, provider_user_id: str) -> Tuple[bool, str]:
    """
    Check if an OAuth identity is already linked to an account
    
    Returns:
        (is_linked, message)
    """
    try:
        if not _auth_http_configured():
            return False, "Auth not configured"
        
        client = _get_supabase_client()
        if not client:
            return False, "Supabase not configured"
        
        result = _run_supabase_with_recovery(
            lambda c: c.rpc('is_identity_linked', {
                'p_provider': provider,
                'p_provider_user_id': provider_user_id
            }),
            'Check identity linked'
        )
        
        return bool(result), "linked" if result else "not linked"
    except Exception as e:
        logger.debug(f"Could not check identity link: {e}")
        return False, "unknown"


def link_oauth_to_account(user_id: str, provider: str, provider_user_id: str, email: str) -> Tuple[bool, str]:
    """
    Link an OAuth identity to an existing user account
    
    Args:
        user_id: The user's UUID
        provider: OAuth provider ('google', 'github', etc.)
        provider_user_id: The provider's unique ID for the user
        email: Email associated with the OAuth identity
    
    Returns:
        (success, message)
    """
    try:
        if not _auth_http_configured():
            return False, "Auth not configured"
        
        client = _get_supabase_client()
        if not client:
            return False, "Supabase not configured"
        
        result = _run_supabase_with_recovery(
            lambda c: c.rpc('link_identity_to_user', {
                'p_user_id': user_id,
                'p_provider': provider,
                'p_provider_user_id': provider_user_id,
                'p_email': email
            }),
            'Link identity to account'
        )
        
        if result:
            logger.info(f"Successfully linked {provider} identity to user {user_id}")
            return True, f"Linked {provider} account successfully"
        return False, "Failed to link account"
    except Exception as e:
        logger.error(f"Error linking identity: {e}")
        if 'already linked' in str(e).lower():
            return False, "This OAuth account is already linked to another user account"
        return False, f"Failed to link account: {str(e)}"


def get_user_linked_providers(user_id: str) -> Tuple[bool, list]:
    """
    Get all linked authentication methods for a user
    
    Returns:
        (success, providers_list)
    """
    try:
        if not _auth_http_configured():
            return False, []
        
        client = _get_supabase_client()
        if not client:
            return False, []
        
        result = _run_supabase_with_recovery(
            lambda c: c.rpc('get_user_linked_providers', {'p_user_id': user_id}),
            'Get linked providers'
        )
        
        if isinstance(result, list):
            return True, result
        return False, []
    except Exception as e:
        logger.debug(f"Could not retrieve linked providers: {e}")
        return False, []


def handle_oauth_account_linking(oauth_user: Dict, provider: str) -> Tuple[bool, str, Optional[str], Optional[str]]:
    """
    Handle account linking when user authenticates with OAuth
    
    Args:
        oauth_user: User object from OAuth token verification
        provider: OAuth provider ('google', 'github', etc.)
    
    Returns:
        (success, message, user_id, conflict_action)
        conflict_action can be:
        - None: No conflict, authentication successful
        - 'link_required': User needs to link accounts
        - 'already_linked': Account already linked
    """
    try:
        user_id = oauth_user.get('id')
        email = oauth_user.get('email', '').lower()
        auth_provider = oauth_user.get('auth_provider', '')
        
        # Check if user was originally created with a different auth method
        if auth_provider and auth_provider != provider and auth_provider != 'email':
            # User was created with OAuth but trying to login with different provider
            # This is allowed - they can have multiple OAuth providers
            return True, f"Authenticated with {provider}", user_id, None
        
        # If user originally signed up with email/password, allow linking with OAuth
        if auth_provider == 'email' or auth_provider == '':
            # This is the key case: email/password user trying to OAuth
            # We'll allow them to proceed, system will link automatically
            return True, f"Authenticated with {provider}", user_id, None
        
        # Otherwise authentication is fine as-is
        return True, f"Authenticated with {provider}", user_id, None
        
    except Exception as e:
        logger.error(f"Error handling OAuth account linking: {e}")
        return False, f"Account linking check failed: {str(e)}", None, None
