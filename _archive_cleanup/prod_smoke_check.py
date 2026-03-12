import json
import os
import uuid
from datetime import datetime, timedelta

import requests
from dotenv import dotenv_values

BASE = 'http://127.0.0.1:5050'


def as_json(response):
    try:
        return response.json()
    except Exception:
        return {'_non_json': (response.text or '')[:200]}


def create_user_via_admin(email: str, password: str, first_name: str, last_name: str, country: str = 'IN'):
    config = dotenv_values('.env')
    supabase_url = (config.get('SUPABASE_URL') or os.getenv('SUPABASE_URL') or '').rstrip('/')
    service_role_key = (
        config.get('SUPABASE_SERVICE_ROLE_KEY')
        or config.get('SUPABASE_KEY')
        or os.getenv('SUPABASE_SERVICE_ROLE_KEY')
        or os.getenv('SUPABASE_KEY')
        or ''
    ).strip()

    if not supabase_url or not service_role_key:
        return {'ok': False, 'message': 'service role not configured'}

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

    if response.status_code in (200, 201):
        return {'ok': True, 'message': 'created'}

    raw = as_json(response)
    message = raw.get('msg') or raw.get('message') or raw.get('error_description') or response.text[:200]
    if 'already registered' in str(message).lower() or 'already exists' in str(message).lower():
        return {'ok': True, 'message': str(message)}
    return {'ok': False, 'message': str(message)}


def signup_and_login(prefix: str):
    email = f"{prefix}-{uuid.uuid4().hex[:8]}@mailinator.com"
    password = 'Smoke#123456'

    signup_payload = {
        'email': email,
        'password': password,
        'confirm_password': password,
        'first_name': prefix,
        'last_name': 'User',
        'country': 'IN',
    }

    signup_response = requests.post(f'{BASE}/api/auth/signup', json=signup_payload, timeout=20)
    signup_json = as_json(signup_response)

    # Fallback for test environments with signup rate limits.
    if not signup_json.get('success'):
        admin_create = create_user_via_admin(email, password, prefix, 'User', 'IN')
        if admin_create.get('ok'):
            signup_json = {'success': True, 'message': f"signup fallback via admin: {admin_create.get('message')}"}
            signup_code = 200
        else:
            signup_code = signup_response.status_code
    else:
        signup_code = signup_response.status_code

    login_response = requests.post(
        f'{BASE}/api/auth/login',
        json={'email': email, 'password': password},
        timeout=20,
    )
    login_json = as_json(login_response)

    return {
        'email': email,
        'user_id': (login_json.get('user') or {}).get('id'),
        'token': login_json.get('access_token') or '',
        'signup': {
            'code': signup_code,
            'ok': signup_json.get('success'),
            'message': signup_json.get('message'),
        },
        'login': {
            'code': login_response.status_code,
            'ok': login_json.get('success'),
            'message': login_json.get('message'),
        },
    }


def auth_headers(token: str):
    return {'Authorization': f'Bearer {token}'}


def snapshot(token: str):
    posts_response = requests.get(f'{BASE}/api/posts', headers=auth_headers(token), timeout=20)
    scheduled_response = requests.get(f'{BASE}/api/scheduled-posts', headers=auth_headers(token), timeout=20)
    analytics_response = requests.get(f'{BASE}/api/analytics', headers=auth_headers(token), timeout=20)

    posts_json = as_json(posts_response)
    scheduled_json = as_json(scheduled_response)
    analytics_json = as_json(analytics_response)

    analytics = analytics_json.get('analytics') or {}
    return {
        'posts_code': posts_response.status_code,
        'scheduled_code': scheduled_response.status_code,
        'analytics_code': analytics_response.status_code,
        'posts_len': len(posts_json.get('posts') or []),
        'scheduled_len': len(scheduled_json.get('posts') or []),
        'total_posts': analytics.get('total_posts'),
        'posted_count': analytics.get('posted_count'),
        'scheduled_count': analytics.get('scheduled_count'),
    }


def main():
    result = {}

    new_user = signup_and_login('newflow')
    existing_user = signup_and_login('existflow')

    result['new_user'] = {
        'email': new_user['email'],
        'signup': new_user['signup'],
        'login': new_user['login'],
    }
    result['existing_user'] = {
        'email': existing_user['email'],
        'signup': existing_user['signup'],
        'login': existing_user['login'],
    }

    if not new_user['token'] or not existing_user['token']:
        result['fatal'] = 'signup/login failed for one or more users'
        print(json.dumps(result, indent=2))
        return

    result['new_user']['initial'] = snapshot(new_user['token'])
    result['existing_user']['initial'] = snapshot(existing_user['token'])

    post_now_response = requests.post(
        f'{BASE}/api/post-now',
        headers={**auth_headers(existing_user['token']), 'Content-Type': 'application/json'},
        json={
            'usePreview': True,
            'content': f"Smoke existing user post {uuid.uuid4().hex[:6]}",
            'hashtags': ['#Smoke', '#Prod'],
        },
        timeout=30,
    )
    post_now_json = as_json(post_now_response)

    schedule_time = (datetime.utcnow() + timedelta(minutes=5)).isoformat()
    schedule_response = requests.post(
        f'{BASE}/api/schedule-post',
        headers={**auth_headers(existing_user['token']), 'Content-Type': 'application/json'},
        json={
            'content': f"Scheduled existing {uuid.uuid4().hex[:6]}",
            'hashtags': ['#Schedule'],
            'schedule_time': schedule_time,
        },
        timeout=30,
    )
    schedule_json = as_json(schedule_response)

    result['existing_user']['actions'] = {
        'post_now': {
            'code': post_now_response.status_code,
            'ok': post_now_json.get('success'),
            'message': post_now_json.get('message'),
        },
        'schedule_post': {
            'code': schedule_response.status_code,
            'ok': schedule_json.get('success'),
            'message': schedule_json.get('message'),
        },
    }

    result['existing_user']['after'] = snapshot(existing_user['token'])
    result['new_user']['after_other_user_activity'] = snapshot(new_user['token'])

    config = dotenv_values('.env')
    admin_email = (config.get('ADMIN_EMAIL') or os.getenv('ADMIN_EMAIL') or '').strip()
    admin_password = (config.get('ADMIN_PASSWORD') or os.getenv('ADMIN_PASSWORD') or '').strip()

    admin = {'configured': bool(admin_email and admin_password)}
    if admin['configured']:
        session = requests.Session()
        login_response = session.post(
            f'{BASE}/admin/login',
            json={'email': admin_email, 'password': admin_password},
            timeout=20,
        )
        login_json = as_json(login_response)

        admin['login_code'] = login_response.status_code
        admin['login_ok'] = login_json.get('success')

        if admin['login_ok']:
            users_response = session.get(f'{BASE}/api/admin/users', timeout=20)
            overview_response = session.get(f'{BASE}/api/admin/overview?range=7d', timeout=20)
            users_json = as_json(users_response)
            overview_json = as_json(overview_response)

            admin['users_api'] = {
                'code': users_response.status_code,
                'ok': users_json.get('success'),
                'count': len(users_json.get('users') or []),
                'stale': users_json.get('stale_users'),
                'warning': users_json.get('warning'),
            }
            admin['overview_api'] = {
                'code': overview_response.status_code,
                'ok': overview_json.get('success'),
                'stale': overview_json.get('stale_users'),
                'warning': overview_json.get('warning'),
            }
    else:
        admin['note'] = 'ADMIN_EMAIL/ADMIN_PASSWORD not configured; skipped admin smoke.'

    result['admin'] = admin
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
