import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import dotenv_values
import app as app_module

cfg = dotenv_values(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))
os.environ.setdefault('SUPABASE_URL', str(cfg.get('SUPABASE_URL') or '').strip())
os.environ.setdefault('SUPABASE_ANON_KEY', str(cfg.get('SUPABASE_ANON_KEY') or cfg.get('SUPABASE_KEY') or '').strip())

test_app = app_module.app
failures = []

with test_app.test_client() as c:
    # 1. Login page renders with SDK + implicit flow
    r = c.get('/login')
    html = r.get_data(as_text=True)
    assert r.status_code == 200, f"login page status {r.status_code}"
    checks = {
        'login_has_sdk_cdn': '@supabase/supabase-js@2' in html,
        'login_has_signInWithOAuth': 'signInWithOAuth' in html,
        'login_has_implicit_flow': "flowType: 'implicit'" in html,
        'login_NO_pkce': "flowType: 'pkce'" not in html,
        'login_has_supabase_url': "SUPABASE_URL" in html and "'None'" not in html,
    }
    for k, v in checks.items():
        status = 'PASS' if v else 'FAIL'
        if not v: failures.append(k)
        print(f'  {status} {k}')

    # 2. Callback page: NO SDK, direct hash parsing
    r2 = c.get('/auth/callback')
    html2 = r2.get_data(as_text=True)
    assert r2.status_code == 200, f"callback page status {r2.status_code}"
    checks2 = {
        'callback_NO_sdk_cdn': 'supabase.min.js' not in html2,
        'callback_NO_getSession': 'getSession' not in html2,
        'callback_NO_createClient': 'createClient' not in html2,
        'callback_has_hash_parse': 'access_token' in html2,
        'callback_has_verify_token': '/api/auth/verify-token' in html2,
        'callback_has_auth_me': '/api/auth/me' in html2,
        'callback_has_redirect_dashboard': "window.location.replace('/')" in html2,
    }
    for k, v in checks2.items():
        status = 'PASS' if v else 'FAIL'
        if not v: failures.append(k)
        print(f'  {status} {k}')

    # 3. Google start endpoint still works
    r3 = c.get('/api/auth/google/start')
    j3 = r3.get_json(silent=True) or {}
    ok3 = r3.status_code == 200 and j3.get('success') and 'response_type=token' in j3.get('auth_url', '')
    status = 'PASS' if ok3 else 'FAIL'
    if not ok3: failures.append('google_start_implicit')
    print(f'  {status} google_start_implicit (status={r3.status_code})')

    # 4. Verify-token rejects invalid token
    r4 = c.post('/api/auth/verify-token', json={'token': 'invalid'})
    ok4 = r4.status_code == 401
    status = 'PASS' if ok4 else 'FAIL'
    if not ok4: failures.append('verify_rejects_invalid')
    print(f'  {status} verify_rejects_invalid (status={r4.status_code})')

    # 5. Dashboard gate forwards hash tokens to callback
    r5 = c.get('/')
    html5 = r5.get_data(as_text=True)
    ok5 = "access_token=" in html5 and "/auth/callback" in html5
    status = 'PASS' if ok5 else 'FAIL'
    if not ok5: failures.append('dashboard_gate_forwards_hash')
    print(f'  {status} dashboard_gate_forwards_hash')

print()
if failures:
    print(f'SMOKE_RESULT=FAIL ({len(failures)} failures: {", ".join(failures)})')
    sys.exit(1)
else:
    print('SMOKE_RESULT=ALL_PASS')
