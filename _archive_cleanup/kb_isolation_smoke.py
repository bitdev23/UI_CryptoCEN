import json
import os
import time
import uuid
from pathlib import Path

import requests
from dotenv import load_dotenv

BASE = 'http://127.0.0.1:5050'
PDF_PATH = Path('data/pdfs/Main_123.pdf')

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL', '').rstrip('/')
SERVICE_ROLE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY')

if not PDF_PATH.exists():
    raise SystemExit('Missing test PDF: data/pdfs/Main_123.pdf')
if not SUPABASE_URL or not SERVICE_ROLE_KEY:
    raise SystemExit('Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY in environment')


def create_user_via_admin(email, password, first_name, last_name):
    response = requests.post(
        f'{SUPABASE_URL}/auth/v1/admin/users',
        headers={
            'Authorization': f'Bearer {SERVICE_ROLE_KEY}',
            'apikey': SERVICE_ROLE_KEY,
            'Content-Type': 'application/json',
        },
        json={
            'email': email,
            'password': password,
            'email_confirm': True,
            'user_metadata': {
                'first_name': first_name,
                'last_name': last_name,
                'country': 'IN',
            },
        },
        timeout=20,
    )
    if response.status_code not in (200, 201):
        raise RuntimeError(f'admin user create failed ({response.status_code}): {response.text[:300]}')


def signup_and_login(prefix):
    email = f"{prefix}_{uuid.uuid4().hex[:10]}@example.com"
    password = 'SmokeTest#1234'
    create_user_via_admin(email, password, prefix, 'User')

    session = requests.Session()
    login_result = session.post(
        f'{BASE}/api/auth/login',
        json={'email': email, 'password': password},
        timeout=20,
    ).json()
    if not login_result.get('success') or not login_result.get('access_token'):
        raise RuntimeError(f'login failed {prefix}: {login_result}')

    return {
        'email': email,
        'token': login_result['access_token'],
        'user_id': (login_result.get('user') or {}).get('id'),
    }


def auth_headers(token):
    return {'Authorization': f'Bearer {token}'}


requests.get(f'{BASE}/login', timeout=10)

account_a = signup_and_login('accta')
account_b = signup_and_login('acctb')

uploaded_name = f"isolation_{uuid.uuid4().hex[:8]}.pdf"
with PDF_PATH.open('rb') as file_handle:
    files = {'files': (uploaded_name, file_handle, 'application/pdf')}
    upload_response = requests.post(
        f'{BASE}/api/upload-knowledge-base',
        files=files,
        headers=auth_headers(account_a['token']),
        timeout=60,
    )
upload_json = upload_response.json()

train_response = requests.post(
    f'{BASE}/api/train-model',
    headers=auth_headers(account_a['token']),
    timeout=30,
)
train_json = train_response.json()

status_samples = []
for _ in range(5):
    status_response = requests.get(
        f'{BASE}/api/knowledge-base-status',
        headers=auth_headers(account_a['token']),
        timeout=20,
    )
    status_json = status_response.json()
    status_samples.append(
        {
            'code': status_response.status_code,
            'status': status_json.get('training_status') or status_json.get('status'),
            'pdf_count': status_json.get('pdf_count'),
        }
    )
    time.sleep(1.0)

b_list_response = requests.get(
    f'{BASE}/api/list-knowledge-base-files',
    headers=auth_headers(account_b['token']),
    timeout=20,
)
b_list_json = b_list_response.json()

b_status_response = requests.get(
    f'{BASE}/api/knowledge-base-status',
    headers=auth_headers(account_b['token']),
    timeout=20,
)
b_status_json = b_status_response.json()

b_delete_response = requests.post(
    f'{BASE}/api/delete-knowledge-base-file',
    json={'filename': uploaded_name},
    headers={**auth_headers(account_b['token']), 'Content-Type': 'application/json'},
    timeout=20,
)
b_delete_json = b_delete_response.json()

a_list_response = requests.get(
    f'{BASE}/api/list-knowledge-base-files',
    headers=auth_headers(account_a['token']),
    timeout=20,
)
a_list_json = a_list_response.json()

a_files = [
    (item.get('name') or item.get('filename')) if isinstance(item, dict) else None
    for item in (a_list_json.get('files') or [])
]
b_files = [
    (item.get('name') or item.get('filename')) if isinstance(item, dict) else None
    for item in (b_list_json.get('files') or [])
]

result = {
    'A': {'email': account_a['email'], 'user_id': account_a['user_id']},
    'B': {'email': account_b['email'], 'user_id': account_b['user_id']},
    'upload': {
        'http': upload_response.status_code,
        'ok': upload_json.get('success'),
        'message': upload_json.get('message'),
        'uploaded_name': uploaded_name,
    },
    'train': {
        'http': train_response.status_code,
        'ok': train_json.get('success'),
        'message': train_json.get('message'),
        'training_mode': train_json.get('training_mode'),
    },
    'A_status_samples': status_samples,
    'A_list_contains_uploaded': uploaded_name in a_files,
    'A_list_files': a_files,
    'B_list_http': b_list_response.status_code,
    'B_list_file_count': len(b_files),
    'B_list_contains_A_file': uploaded_name in b_files,
    'B_list_files': b_files,
    'B_status': {
        'http': b_status_response.status_code,
        'pdf_count': b_status_json.get('pdf_count'),
        'trained': b_status_json.get('trained'),
    },
    'B_delete_attempt': {
        'http': b_delete_response.status_code,
        'success': b_delete_json.get('success'),
        'message': b_delete_json.get('message'),
    },
}

print(json.dumps(result, indent=2))
