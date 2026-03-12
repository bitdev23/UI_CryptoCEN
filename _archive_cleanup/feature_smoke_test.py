import os
import uuid

import requests
from dotenv import dotenv_values

base = 'http://127.0.0.1:5050'


def get_json(response):
    try:
        return response.json()
    except Exception:
        print('non_json_response', response.status_code, response.text[:180])
        return {}


def create_user_via_admin(email, password, first_name='Smoke', last_name='User', country='IN'):
    cfg = dotenv_values('.env')
    supabase_url = (cfg.get('SUPABASE_URL') or os.getenv('SUPABASE_URL') or '').rstrip('/')
    service_role_key = (
        cfg.get('SUPABASE_SERVICE_ROLE_KEY')
        or cfg.get('SUPABASE_KEY')
        or os.getenv('SUPABASE_SERVICE_ROLE_KEY')
        or os.getenv('SUPABASE_KEY')
        or ''
    ).strip()
    if not supabase_url or not service_role_key:
        return False, 'service role not configured'

    response = requests.post(
        f'{supabase_url}/auth/v1/admin/users',
        headers={
            'Authorization': f'Bearer {service_role_key}',
            'apikey': service_role_key,
            'Content-Type': 'application/json',
        },
        json={
            'email': email,
            'password': password,
            'email_confirm': True,
            'user_metadata': {
                'first_name': first_name,
                'last_name': last_name,
                'country': country,
            },
        },
        timeout=20,
    )
    payload = get_json(response)
    if response.status_code in (200, 201):
        return True, 'created'
    message = payload.get('msg') or payload.get('message') or payload.get('error_description') or response.text[:180]
    lowered = str(message).lower()
    if 'already registered' in lowered or 'already exists' in lowered:
        return True, str(message)
    return False, str(message)


def get_auth_headers():
    email = os.getenv('SMOKE_TEST_EMAIL', '').strip().lower()
    password = os.getenv('SMOKE_TEST_PASSWORD', '').strip()

    if not email or not password:
        email = f"feature-smoke-{uuid.uuid4().hex[:8]}@mailinator.com"
        password = 'Smoke#123456'
        signup_payload = {
            'email': email,
            'password': password,
            'confirm_password': password,
            'first_name': 'Feature',
            'last_name': 'Smoke',
            'country': 'IN',
        }
        signup_response = requests.post(f'{base}/api/auth/signup', json=signup_payload, timeout=30)
        signup_json = get_json(signup_response)
        if not signup_json.get('success'):
            ok, message = create_user_via_admin(email, password, 'Feature', 'Smoke', 'IN')
            if not ok:
                raise RuntimeError(f'Unable to bootstrap smoke user: {message}')

    login_response = requests.post(
        f'{base}/api/auth/login',
        json={'email': email, 'password': password},
        timeout=30,
    )
    login_json = get_json(login_response)
    token = login_json.get('access_token')
    if not token:
        raise RuntimeError(f"Login failed for smoke user: {login_json.get('message') or login_json}")

    return {'Authorization': f'Bearer {token}'}, email


auth_headers, smoke_email = get_auth_headers()
print('smoke_user', smoke_email)

workspaces = get_json(requests.get(base + '/api/kb-workspaces', headers=auth_headers, timeout=30))
print('workspaces_get', workspaces.get('success'), 'count', len(workspaces.get('workspaces') or []))

file_options = get_json(requests.get(base + '/api/kb-file-options', headers=auth_headers, timeout=30))
print('file_options_get', file_options.get('success'), 'count', len(file_options.get('files') or []))

file_ids = [item['id'] for item in (file_options.get('files') or [])[:2] if item.get('id')]
workspace_save = get_json(requests.post(
    base + '/api/kb-workspaces',
    headers={**auth_headers, 'Content-Type': 'application/json'},
    json={'name': 'Auto Workspace Test', 'use_all_files': False, 'file_ids': file_ids},
    timeout=30,
))
print('workspace_save', workspace_save.get('success'), 'name', (workspace_save.get('workspace') or {}).get('name'))

presets = get_json(requests.get(base + '/api/generation-presets', headers=auth_headers, timeout=30))
print('presets_get', presets.get('success'), 'count', len(presets.get('presets') or []))

preset_save = get_json(requests.post(
    base + '/api/generation-presets/save',
    headers={**auth_headers, 'Content-Type': 'application/json'},
    json={
        'name': 'Integration Preset',
        'settings': {
            'hashtags': 2,
            'emojis': 'none',
            'word_count_mode': 'custom_range',
            'min_words': 80,
            'max_words': 110,
            'kb_mode': 'no_kb',
            'topics': ['tips'],
        },
    },
    timeout=30,
))
print('preset_save', preset_save.get('success'), 'count', len(preset_save.get('presets') or []))

preview = get_json(requests.post(
    base + '/api/generate-preview',
    headers={**auth_headers, 'Content-Type': 'application/json'},
    json={
        'topic': 'Automobile demand outlook',
        'industry': 'ecommerce',
        'role': 'ops',
        'kb_mode': 'no_kb',
        'word_count_mode': 'custom_range',
        'min_words': 80,
        'max_words': 110,
        'hashtags': 2,
        'emojis': 'none',
        'topics': ['trends'],
    },
    timeout=120,
))
print('preview_ok', preview.get('success'), 'kb_mode', (preview.get('settings_applied') or {}).get('kb_mode'))
print('settings', preview.get('settings_applied'))
