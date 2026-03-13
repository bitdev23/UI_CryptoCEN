"""
Simple web dashboard for non-technical LinkedIn automation management.
Run: python app.py
Then open: http://localhost:5050
"""
from flask import Flask, render_template, request, jsonify, redirect, url_for, g, session
import os
import json
import logging
import threading
import time
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
from datetime import datetime, timedelta, date
from functools import wraps
from uuid import UUID, uuid4
from pathlib import Path
from dotenv import load_dotenv, dotenv_values

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
from config import PROFILES, DEFAULT_PROFILE, POST_FORMATS
from linkedin_poster import LinkedInPoster
from auth import require_auth, signup_user, login_user, logout_user, verify_token, refresh_access_token, request_password_reset, auth_healthcheck, supabase as auth_supabase
from kb_jobs import enqueue_kb_training_job, get_kb_training_status

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'dev-secret-change-in-production')

app.config['SESSION_COOKIE_SECURE'] = os.getenv('FLASK_ENV') == 'production'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = 86400  # 24 hours

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
PDF_DIR = os.path.join(DATA_DIR, 'pdfs')
FEATURE_STORE_PATH = os.path.join(DATA_DIR, 'user_features.json')
POSTS_PATH = os.path.join(DATA_DIR, 'posts.json')
SCHEDULED_POSTS_PATH = os.path.join(DATA_DIR, 'scheduled_posts.json')
FEATURE_STORE_LOCK = threading.Lock()


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
    if not os.path.exists(FEATURE_STORE_PATH):
        return {}
    try:
        with open(FEATURE_STORE_PATH, 'r') as fh:
            data = json.load(fh)
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _write_feature_store(payload: dict) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(FEATURE_STORE_PATH, 'w') as fh:
        json.dump(payload, fh, indent=2)


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
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    payload = items if isinstance(items, list) else []
    with open(file_path, 'w') as fh:
        json.dump(payload, fh, indent=2)


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
    """Return a user_id from feature store that has LinkedIn credentials configured."""
    try:
        store = _read_feature_store()
        if not isinstance(store, dict):
            return ''
        for candidate_user_id, blob in store.items():
            if not is_valid_uuid(str(candidate_user_id or '')):
                continue
            cfg = blob.get('user_config') if isinstance(blob.get('user_config'), dict) else {}
            access_token = str(cfg.get('LINKEDIN_ACCESS_TOKEN') or '').strip()
            person_id = str(cfg.get('LINKEDIN_PERSON_ID') or '').strip()
            if access_token and person_id:
                return str(candidate_user_id)
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

    sorted_posts = sorted(normalized_posts, key=lambda p: _parse_post_datetime(p.get('created_at')), reverse=True)

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

    posts = _read_json_list(POSTS_PATH)
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
    target_audience = (
        raw.get('target_audience')
        or generation_context.get('target_audience')
        or settings_applied.get('target_audience')
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
        'target_audience': str(target_audience or '').strip(),
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
        store = _read_feature_store()
        blob = store.get(user_id) if isinstance(store.get(user_id), dict) else {}

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
        store[user_id] = blob
        _write_feature_store(store)
        return blob


def _save_user_feature_blob(user_id: str, blob: dict) -> dict:
    with FEATURE_STORE_LOCK:
        store = _read_feature_store()
        blob['updated_at'] = int(time.time())
        store[user_id] = blob
        _write_feature_store(store)
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
ADMIN_USERS_CACHE_TTL_SEC = max(30, int(os.getenv('ADMIN_USERS_CACHE_TTL_SEC', '300') or 300))
ADMIN_USERS_CACHE_LOCK = threading.Lock()
ADMIN_USERS_CACHE = {
    'users': [],
    'updated_at': 0.0,
    'stale': False,
    'warning': ''
}


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
        file_type = 'docx' if filename.lower().endswith('.docx') else 'pdf'

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
            'message': 'Queue unavailable; training started in local background mode'
        }

    return {
        'success': False,
        'already_running': True,
        'message': 'Training is already running in local background mode. Please wait and refresh status.'
    }

# ============= CONFIGURATION HELPERS =============

CONFIG_DEFAULTS = {
    'AI_PROVIDER': 'google',
    'GOOGLE_API_KEY': '',
    'OPENAI_API_KEY': '',
    'ANTHROPIC_API_KEY': '',
    'LINKEDIN_ACCESS_TOKEN': '',
    'LINKEDIN_PERSON_ID': '',
    'LINKEDIN_CLIENT_ID': '',
    'LINKEDIN_CLIENT_SECRET': '',
    'TEST_MODE': 'true',
    'CONTENT_PROFILE': DEFAULT_PROFILE,
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
    'GOOGLE_API_KEY', 'OPENAI_API_KEY', 'ANTHROPIC_API_KEY',
    'LINKEDIN_ACCESS_TOKEN', 'LINKEDIN_PERSON_ID'
}

USER_CONFIG_KEYS = set(CONFIG_DEFAULTS.keys()) - {
    'TEST_MODE', 'LINKEDIN_CLIENT_ID', 'LINKEDIN_CLIENT_SECRET'
}


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
    return dict(overrides)


def _save_user_config_overrides(user_id: str, config: dict) -> None:
    if not _is_user_config_eligible(user_id):
        return
    blob = _ensure_user_feature_blob(user_id)
    existing = blob.get('user_config') if isinstance(blob.get('user_config'), dict) else {}
    updated = dict(existing)
    for key in USER_CONFIG_KEYS:
        if key in config:
            updated[key] = _serialize_config_value(key, config.get(key))
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
            if key in CONFIG_DEFAULTS:
                config[key] = value

    return _normalize_config_types(config)


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
CONTENT_PROFILE={_serialize_config_value('CONTENT_PROFILE', config.get('CONTENT_PROFILE'))}
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
        ai = AIProvider()
        profile_key = config_obj['CONTENT_PROFILE']
        profile = PROFILES.get(profile_key, PROFILES[DEFAULT_PROFILE])
        theme = random.choice(profile.get('content_themes', []))
        fmt = random.choice(POST_FORMATS)
        services = profile.get('company_info', {}).get('services', '')
        
        # Simple prompt for post generation
        prompt = f"""Generate a LinkedIn post about: {theme}

Company context: {services}

Post format: {fmt}

Make it engaging, professional, and include relevant hashtags. Keep it between {config_obj['MIN_POST_LENGTH']} and {config_obj['MAX_POST_LENGTH']} characters."""

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
        
        # Save back
        _write_json_list(POSTS_PATH, posts)
        
        logger.info("Scheduled post completed: %s", "Posted" if post_result.get('status') == 'posted' else "Test mode")
        
    except Exception as e:
        logger.exception("Scheduled post job failed: %s", e)

def start_scheduler():
    """Start the background scheduler - runs even in TEST_MODE but marks posts appropriately"""
    def scheduler_thread():
        config = load_config()
        tz = pytz.timezone(config['TIMEZONE'])
        schedule_time = f"{config['POST_TIME_HOUR']:02d}:{config['POST_TIME_MINUTE']:02d}"
        
        # Always schedule daily jobs - TEST_MODE will be respected in the job itself
        schedule.every().day.at(schedule_time).do(scheduled_post_job)
        logger.info("✓ Daily scheduler started - will post daily at %s %s (TEST_MODE: %s)", schedule_time, config['TIMEZONE'], config['TEST_MODE'])
        
        while True:
            # Always check for UI-scheduled posts
            config = load_config()  # Reload config
            check_scheduled_posts()  # Always check - function respects TEST_MODE
            
            # Run any pending scheduled jobs (daily posts)
            schedule.run_pending()
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
                    _write_json_list(POSTS_PATH, posts)
                    posted_count += 1
                except Exception as post_error:
                    post['last_error'] = str(post_error)
                    post['last_attempt_at'] = datetime.utcnow().isoformat() + 'Z'
                    pending_posts.append(post)
                    logger.exception("Scheduled post failed id=%s: %s", post.get('id'), post_error)

            _write_json_list(SCHEDULED_POSTS_PATH, pending_posts)
            if due_count > 0:
                logger.info("Scheduled posts processed. due=%s posted=%s remaining=%s", due_count, posted_count, len(pending_posts))
                    
        except Exception as e:
            logger.exception("Error processing scheduled posts: %s", e)
    
    thread = threading.Thread(target=scheduler_thread, daemon=True)
    thread.start()
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


def get_admin_credentials():
    env_email = os.getenv('ADMIN_EMAIL', '').strip().lower()
    env_password = os.getenv('ADMIN_PASSWORD', '').strip()

    if env_email and env_password:
        return {
            'email': env_email,
            'password': env_password
        }

    try:
        file_values = dotenv_values(Path(BASE_DIR) / '.env')
    except Exception:
        file_values = {}

    file_email = str(file_values.get('ADMIN_EMAIL') or '').strip().lower()
    file_password = str(file_values.get('ADMIN_PASSWORD') or '').strip()

    return {
        'email': env_email or file_email,
        'password': env_password or file_password
    }


def is_valid_uuid(value: str) -> bool:
    try:
        UUID(str(value))
        return True
    except Exception:
        return False


def require_admin_session(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get('is_admin'):
            return redirect(url_for('admin_login_page'))
        return f(*args, **kwargs)
    return wrapper


def require_admin_api(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get('is_admin'):
            return jsonify({'success': False, 'message': 'Admin authentication required'}), 401
        return f(*args, **kwargs)
    return wrapper


def _set_admin_users_cache(users: list, stale: bool = False, warning: str = '') -> None:
    with ADMIN_USERS_CACHE_LOCK:
        ADMIN_USERS_CACHE['users'] = users if isinstance(users, list) else []
        ADMIN_USERS_CACHE['updated_at'] = time.time()
        ADMIN_USERS_CACHE['stale'] = bool(stale)
        ADMIN_USERS_CACHE['warning'] = str(warning or '').strip()


def _get_admin_users_cache_meta() -> dict:
    with ADMIN_USERS_CACHE_LOCK:
        return {
            'users': list(ADMIN_USERS_CACHE.get('users') or []),
            'updated_at': float(ADMIN_USERS_CACHE.get('updated_at') or 0.0),
            'stale': bool(ADMIN_USERS_CACHE.get('stale')),
            'warning': str(ADMIN_USERS_CACHE.get('warning') or '')
        }


def list_auth_users(page: int = 1, per_page: int = 1000):
    if not auth_supabase:
        cache_meta = _get_admin_users_cache_meta()
        if cache_meta['users']:
            _set_admin_users_cache(cache_meta['users'], stale=True, warning='Supabase auth unavailable. Showing cached user list.')
            return cache_meta['users']
        _set_admin_users_cache([], stale=True, warning='Supabase authentication is not configured.')
        return []
    try:
        response = auth_supabase.auth.admin.list_users(page=page, per_page=per_page)
        if isinstance(response, list):
            _set_admin_users_cache(response, stale=False, warning='')
            return response
        users = getattr(response, 'users', None)
        if users is None and isinstance(response, dict):
            users = response.get('users', [])
        users = users or []
        _set_admin_users_cache(users, stale=False, warning='')
        return users
    except Exception as e:
        logger.error("Admin list users failed: %s", e)
        cache_meta = _get_admin_users_cache_meta()
        if cache_meta['users']:
            age_sec = int(max(0, time.time() - cache_meta['updated_at']))
            warning = f'Live user list fetch failed. Showing cached results ({age_sec}s old).'
            _set_admin_users_cache(cache_meta['users'], stale=True, warning=warning)
            return cache_meta['users']
        _set_admin_users_cache([], stale=True, warning='Unable to load users from authentication provider.')
        return []


def user_to_admin_row(user_obj, subscription_map=None):
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
        'id': user_id,
        'email': email,
        'first_name': metadata.get('first_name', ''),
        'last_name': metadata.get('last_name', ''),
        'country': metadata.get('country', ''),
        'signup_date': created_at,
        'verified': is_verified,
        'active': is_active,
        'status': 'Active' if is_active else 'Inactive',
        'last_sign_in_at': last_sign_in_at,
        'plan': plan,
        'subscription_status': subscription_status,
        'subscription_period_start': period_start,
        'subscription_period_end': period_end,
        'cancel_at_period_end': cancel_at_period_end
    }


def _admin_log_action(action: str, target_user_id: str = '', details: dict = None):
    details = details or {}
    try:
        logger.info("ADMIN_ACTION action=%s admin=%s target=%s details=%s", action, session.get('admin_email', ''), target_user_id, details)
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
                'details': details
            }
        }).execute()
    except Exception as e:
        logger.debug("Admin system log insert skipped/failed: %s", e)


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
        '1m': ('1_month', 1),
        '1_month': ('1_month', 1),
        'monthly': ('1_month', 1),
        'pro': ('1_month', 1),
        '3m': ('3_month', 3),
        '3_month': ('3_month', 3),
        'quarterly': ('3_month', 3),
        '12m': ('12_month', 12),
        '12_month': ('12_month', 12),
        'yearly': ('12_month', 12),
        'annual': ('12_month', 12),
        'agency': ('12_month', 12)
    }
    return plan_map.get(value)


PLAN_LIMITS = {
    'free': {
        'posts_generated': 3,
        'scheduled_posts': 0,
        'kb_documents': 1,
        'kb_storage_mb': 5,
    },
    '1_month': {
        'posts_generated': 100,
        'scheduled_posts': 30,
        'kb_documents': 100,
        'kb_storage_mb': 500,
    },
    '3_month': {
        'posts_generated': 100,
        'scheduled_posts': 30,
        'kb_documents': 100,
        'kb_storage_mb': 500,
    },
    '12_month': {
        'posts_generated': 100,
        'scheduled_posts': 30,
        'kb_documents': 100,
        'kb_storage_mb': 500,
    }
}


def _plan_price_inr(plan: str) -> int:
    normalized = _normalize_subscription_plan(plan)
    key = normalized[0] if normalized else '1_month'
    env_map = {
        '1_month': 'PLAN_PRICE_1_MONTH_INR',
        '3_month': 'PLAN_PRICE_3_MONTH_INR',
        '12_month': 'PLAN_PRICE_12_MONTH_INR'
    }
    default_map = {
        '1_month': 999,
        '3_month': 2499,
        '12_month': 8999
    }
    env_key = env_map.get(key)
    if not env_key:
        return 0
    try:
        value = int(str(os.getenv(env_key, default_map[key])).strip())
        return max(0, value)
    except Exception:
        return default_map[key]


def _get_plan_limits(plan: str) -> dict:
    normalized = _normalize_subscription_plan(plan)
    key = normalized[0] if normalized else 'free'
    return PLAN_LIMITS.get(key, PLAN_LIMITS['free'])


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
            return parsed.astimezone().replace(tzinfo=None)
        return parsed
    except Exception:
        return None


def _get_subscription_row(user_id: str) -> dict:
    if not auth_supabase or not is_valid_uuid(user_id):
        return {'plan': 'free', 'status': 'active'}
    try:
        rows = auth_supabase.table('subscriptions').select('*').eq('user_id', user_id).limit(1).execute().data or []
        return rows[0] if rows else {'plan': 'free', 'status': 'active'}
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

    allowed_fields = {'posts_generated', 'posts_published', 'kb_files_uploaded', 'kb_storage_bytes', 'api_calls'}
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
    except Exception as e:
        logger.warning("Usage increment failed for user %s: %s", user_id, e)


def _get_user_scheduled_count(user_id: str) -> int:
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


def _activate_subscription_from_payment(user_id: str, plan: str, payment_id: str = '', order_id: str = ''):
    normalized = _normalize_subscription_plan(plan)
    if not normalized or normalized[0] == 'free':
        return None
    if not auth_supabase or not is_valid_uuid(user_id):
        return None

    normalized_plan, months = normalized
    now = datetime.utcnow()
    period_end = _add_months_utc(now, months)
    payload = {
        'user_id': user_id,
        'plan': normalized_plan,
        'status': 'active',
        'current_period_start': now.isoformat() + 'Z',
        'current_period_end': period_end.isoformat() + 'Z',
        'cancel_at_period_end': False,
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
            'current_period_end': period_end.isoformat() + 'Z',
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
        'current_period_end': payload['current_period_end']
    }


def _razorpay_keys():
    key_id = str(os.getenv('RAZORPAY_KEY_ID') or '').strip()
    key_secret = str(os.getenv('RAZORPAY_KEY_SECRET') or '').strip()
    return key_id, key_secret


def _razorpay_webhook_secret() -> str:
    return str(os.getenv('RAZORPAY_WEBHOOK_SECRET') or '').strip()


def _create_razorpay_order(amount_inr: int, receipt: str, user_id: str, plan: str) -> dict:
    key_id, key_secret = _razorpay_keys()
    if not key_id or not key_secret:
        raise RuntimeError('Razorpay keys are not configured')

    payload = {
        'amount': int(amount_inr * 100),
        'currency': 'INR',
        'receipt': receipt,
        'notes': {
            'user_id': user_id,
            'plan': plan
        }
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


def _find_auth_user_by_id(user_id: str):
    users = list_auth_users()
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

# ============= AUTHENTICATION ROUTES =============

@app.route('/api/auth/signup', methods=['POST'])
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

        metadata = {
            'email': email,
            'first_name': first_name,
            'last_name': last_name,
            'country': country
        }

        success, message, user_data = signup_user(email, password, metadata)
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
        return jsonify({'success': False, 'message': f'Signup failed: {str(e)}'}), 500


@app.route('/api/auth/login', methods=['POST'])
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
            if 'temporarily unavailable' in lowered or 'timeout' in lowered:
                status_code = 503
            return jsonify({'success': False, 'message': message}), status_code
            
    except Exception as e:
        logger.exception("Login failed")
        return jsonify({'success': False, 'message': f'Login failed: {str(e)}'}), 500


@app.route('/api/auth/google/start', methods=['GET', 'POST'])
def auth_google_start():
    """Start Google OAuth sign-in via Supabase hosted auth."""
    try:
        supabase_url = (os.getenv('SUPABASE_URL') or '').strip().rstrip('/')
        anon_key = (os.getenv('SUPABASE_ANON_KEY') or os.getenv('SUPABASE_KEY') or '').strip()
        if not supabase_url or not anon_key:
            return jsonify({'success': False, 'message': 'Google sign-in is not configured on server'}), 500

        payload = request.get_json(silent=True) or {}
        requested_redirect = (payload.get('redirect_to') or request.args.get('redirect_to') or '').strip()
        if requested_redirect:
            redirect_to = requested_redirect
        else:
            base_url = (os.getenv('APP_BASE_URL') or 'http://127.0.0.1:5050').strip().rstrip('/')
            redirect_to = f"{base_url}/auth/callback"

        query = urlencode({
            'provider': 'google',
            'redirect_to': redirect_to,
            'scopes': 'openid email profile',
            'flow_type': 'implicit',
            'response_type': 'token',
            'prompt': 'consent'
        })
        auth_url = f"{supabase_url}/auth/v1/authorize?{query}"
        return jsonify({'success': True, 'auth_url': auth_url})
    except Exception as e:
        logger.exception("Failed to start Google OAuth")
        return jsonify({'success': False, 'message': f'Failed to start Google sign-in: {str(e)}'}), 500


@app.route('/api/auth/logout', methods=['POST'])
@require_auth
def auth_logout():
    """User logout"""
    try:
        success, message = logout_user(None)
        return jsonify({'success': success, 'message': message}), 200 if success else 500
    except Exception as e:
        logger.exception("Logout failed")
        return jsonify({'success': False, 'message': f'Logout failed: {str(e)}'}), 500


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
        return jsonify({'success': False, 'message': str(e)}), 500


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
        return jsonify({'success': False, 'message': str(e)}), 500


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
        return jsonify({'success': False, 'message': f'Token refresh failed: {str(e)}'}), 500


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
        return jsonify({'success': False, 'message': f'Failed to update account: {str(e)}'}), 400


@app.route('/api/auth/password/reset-request', methods=['POST'])
@require_auth
def auth_password_reset_request():
    """Send password reset email to current signed-in user."""
    try:
        success, message = request_password_reset(g.user_email)
        return jsonify({'success': success, 'message': message}), 200 if success else 400
    except Exception as e:
        logger.exception("Password reset email failed")
        return jsonify({'success': False, 'message': str(e)}), 500


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
        return jsonify({'success': False, 'message': f'Failed to update password: {str(e)}'}), 400


@app.route('/login')
def login_page():
    """Serve login/signup page"""
    return render_template('auth.html')


@app.route('/auth/callback')
def auth_callback_page():
    """Supabase email verification callback handler page."""
    return render_template('auth_callback.html')


@app.route('/auth/logout')
def logout_page():
    """Logout page (clears token and redirects)"""
    # Token is stored on client-side, just redirect to login
    return redirect(url_for('login_page'))


@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login_page():
    """Admin login page."""
    if request.method == 'GET':
        return render_template('admin_login.html')

    data = request.get_json(silent=True) or request.form or {}
    email = (data.get('email') or '').strip().lower()
    password = (data.get('password') or '').strip()

    creds = get_admin_credentials()
    if not creds['email'] or not creds['password']:
        return jsonify({'success': False, 'message': 'Admin credentials are not configured'}), 500

    if email == creds['email'] and password == creds['password']:
        session['is_admin'] = True
        session['admin_email'] = email
        return jsonify({'success': True, 'redirect': '/admin/dashboard'})

    return jsonify({'success': False, 'message': 'Invalid admin credentials'}), 401


@app.route('/admin/logout')
def admin_logout_page():
    session.pop('is_admin', None)
    session.pop('admin_email', None)
    return redirect(url_for('admin_login_page'))


@app.route('/admin/dashboard')
@require_admin_session
def admin_dashboard_page():
    return render_template('admin_dashboard.html', admin_email=session.get('admin_email', ''))


@app.route('/api/admin/overview', methods=['GET'])
@require_admin_api
def admin_overview():
    users = list_auth_users()
    cache_meta = _get_admin_users_cache_meta()
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
            'total_users': total_users,
            'verified_users': verified_users,
            'active_users': active_users,
            'total_posts': total_posts,
            'posts_today': posts_today,
            'failed_posts': failed_posts
        },
        'charts': {
            'weekly_labels': chart_labels,
            'weekly_posts': chart_values,
            'user_breakdown': [total_users, verified_users, active_users],
            'selected_range': range_raw
        }
    })


@app.route('/api/admin/users', methods=['GET'])
@require_admin_api
def admin_users():
    users = list_auth_users()
    cache_meta = _get_admin_users_cache_meta()
    auth_configured = bool(auth_supabase)

    subscription_map = {}
    try:
        if auth_supabase:
            subs = auth_supabase.table('subscriptions').select('user_id,plan,status,current_period_start,current_period_end,cancel_at_period_end').execute().data or []
            subscription_map = {str(row.get('user_id')): row for row in subs}
    except Exception as e:
        logger.error("Admin users subscription lookup failed: %s", e)

    rows = [user_to_admin_row(user, subscription_map) for user in users]
    rows.sort(key=lambda item: item.get('signup_date') or '', reverse=True)
    return jsonify({
        'success': True,
        'users': rows,
        'auth_configured': auth_configured,
        'stale_users': bool(cache_meta.get('stale')),
        'warning': cache_meta.get('warning', ''),
        'message': '' if auth_configured else 'Supabase authentication is not configured. Add SUPABASE_URL and SUPABASE_ANON_KEY (or SUPABASE_SERVICE_ROLE_KEY) in .env and restart the server.'
    })


@app.route('/api/admin/users/create', methods=['POST'])
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
            'email': email,
            'password': password,
            'email_confirm': True,
            'user_metadata': {
                'first_name': first_name,
                'last_name': last_name,
                'country': country
            }
        })
        user_obj = getattr(response, 'user', None)
        if user_obj is None and isinstance(response, dict):
            user_obj = response.get('user')

        user_id = str(getattr(user_obj, 'id', '') or (user_obj.get('id') if isinstance(user_obj, dict) else ''))
        _admin_log_action('create_user', user_id, {'email': email})
        return jsonify({'success': True, 'message': 'User created successfully', 'user_id': user_id, 'email': email})
    except Exception as e:
        logger.error("Admin create user failed: %s", e)
        return jsonify({'success': False, 'message': f'Failed to create user: {str(e)}'}), 500


@app.route('/api/admin/users/<user_id>', methods=['GET'])
@require_admin_api
def admin_user_details(user_id):
    selected = _find_auth_user_by_id(user_id)

    if not selected:
        return jsonify({'success': False, 'message': 'User not found'}), 404

    subscription_map = {}
    try:
        if auth_supabase:
            sub_row = auth_supabase.table('subscriptions').select('user_id,plan,status,current_period_start,current_period_end,cancel_at_period_end').eq('user_id', user_id).limit(1).execute().data or []
            if sub_row:
                subscription_map = {str(user_id): sub_row[0]}
    except Exception as e:
        logger.error("Admin user details subscription lookup failed: %s", e)

    details = user_to_admin_row(selected, subscription_map)
    posts = []
    try:
        if auth_supabase:
            posts = auth_supabase.table('posts').select('id,content,status,created_at,scheduled_for,posted_at,error_message').eq('user_id', user_id).order('created_at', desc=True).limit(50).execute().data or []
    except Exception as e:
        logger.error("Admin user details posts lookup failed: %s", e)

    for post in posts:
        post['content_preview'] = (post.get('content') or '')[:180]

    return jsonify({'success': True, 'user': details, 'posts': posts})


@app.route('/api/admin/users/<user_id>/status', methods=['POST'])
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

        attributes = {
            'user_metadata': current_metadata,
            'ban_duration': 'none' if active else '876000h'
        }
        auth_supabase.auth.admin.update_user_by_id(user_id, attributes)
        _admin_log_action('toggle_user_status', user_id, {'active': active})

        return jsonify({'success': True, 'message': 'User activated' if active else 'User deactivated'})
    except Exception as e:
        logger.error("Admin status update failed: %s", e)
        return jsonify({'success': False, 'message': f'Failed to update user status: {str(e)}'}), 500


@app.route('/api/admin/users/<user_id>', methods=['DELETE'])
@require_admin_api
def admin_delete_user(user_id):
    if not auth_supabase:
        return jsonify({'success': False, 'message': 'Supabase not configured'}), 500

    try:
        auth_supabase.auth.admin.delete_user(user_id)
        _admin_log_action('delete_user', user_id, {})
        return jsonify({'success': True, 'message': 'User deleted successfully'})
    except Exception as e:
        logger.error("Admin delete user failed: %s", e)
        return jsonify({'success': False, 'message': f'Failed to delete user: {str(e)}'}), 500


@app.route('/api/admin/users/<user_id>/posts', methods=['GET'])
@require_admin_api
def admin_user_posts(user_id):
    try:
        if not auth_supabase:
            return jsonify({'success': False, 'message': 'Supabase not configured'}), 500

        posts = auth_supabase.table('posts').select('id,content,status,created_at,scheduled_for,posted_at,error_message').eq('user_id', user_id).order('created_at', desc=True).limit(100).execute().data or []
        for post in posts:
            post['content_preview'] = (post.get('content') or '')[:180]
        return jsonify({'success': True, 'posts': posts})
    except Exception as e:
        logger.error("Admin fetch user posts failed: %s", e)
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/admin/migrate-legacy-content-owner', methods=['POST'])
@require_admin_api
def admin_migrate_legacy_content_owner():
    data = request.get_json(silent=True) or {}
    target_user_id = str(data.get('target_user_id') or '').strip()
    dry_run = bool(data.get('dry_run', False))

    if not is_valid_uuid(target_user_id):
        return jsonify({'success': False, 'message': 'Valid target_user_id is required'}), 400

    try:
        posts = _read_json_list(POSTS_PATH)
        scheduled_posts = _read_json_list(SCHEDULED_POSTS_PATH)

        posts_migrated = 0
        for row in posts:
            owner = str(row.get('user_id') or '').strip()
            if not owner:
                row['user_id'] = target_user_id
                posts_migrated += 1

        scheduled_migrated = 0
        for row in scheduled_posts:
            owner = str(row.get('user_id') or '').strip()
            if not owner:
                row['user_id'] = target_user_id
                scheduled_migrated += 1

        if not dry_run:
            _write_json_list(POSTS_PATH, posts)
            _write_json_list(SCHEDULED_POSTS_PATH, scheduled_posts)

        _admin_log_action(
            'migrate_legacy_content_owner',
            target_user_id,
            {
                'dry_run': dry_run,
                'posts_migrated': posts_migrated,
                'scheduled_migrated': scheduled_migrated
            }
        )

        return jsonify({
            'success': True,
            'dry_run': dry_run,
            'target_user_id': target_user_id,
            'posts_migrated': posts_migrated,
            'scheduled_migrated': scheduled_migrated,
            'message': 'Dry run complete' if dry_run else 'Legacy ownership migration completed'
        })
    except Exception as e:
        logger.error('Admin legacy ownership migration failed: %s', e)
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/admin/users/<user_id>/subscription/set-plan', methods=['POST'])
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
            'user_id': user_id,
            'plan': plan,
            'status': 'active',
            'current_period_start': now.isoformat() + 'Z',
            'current_period_end': period_end.isoformat() + 'Z',
            'cancel_at_period_end': False,
            'updated_at': now.isoformat() + 'Z'
        }, on_conflict='user_id').execute()
        _admin_log_action('set_subscription_plan', user_id, {'plan': plan, 'months': months})
        return jsonify({
            'success': True,
            'message': f'Subscription updated to {plan.replace("_", " ")}',
            'plan': plan,
            'subscription_period_end': period_end.isoformat() + 'Z'
        })
    except Exception as e:
        logger.error("Admin set subscription failed: %s", e)
        return jsonify({'success': False, 'message': f'Failed to update subscription: {str(e)}'}), 500


@app.route('/api/admin/users/<user_id>/subscription/cancel', methods=['POST'])
@require_admin_api
def admin_cancel_subscription(user_id):
    if not auth_supabase:
        return jsonify({'success': False, 'message': 'Supabase not configured'}), 500

    try:
        now = datetime.utcnow().isoformat() + 'Z'
        auth_supabase.table('subscriptions').upsert({
            'user_id': user_id,
            'status': 'cancelled',
            'cancel_at_period_end': True,
            'updated_at': now
        }, on_conflict='user_id').execute()
        _admin_log_action('cancel_subscription', user_id, {'cancel_at_period_end': True})
        return jsonify({'success': True, 'message': 'Subscription marked to cancel'})
    except Exception as e:
        logger.error("Admin cancel subscription failed: %s", e)
        return jsonify({'success': False, 'message': f'Failed to cancel subscription: {str(e)}'}), 500


@app.route('/api/billing/plans', methods=['GET'])
@require_auth
def billing_plans():
    plans = []
    for plan_code in ('1_month', '3_month', '12_month'):
        normalized = _normalize_subscription_plan(plan_code)
        plans.append({
            'plan': plan_code,
            'duration_months': normalized[1] if normalized else 0,
            'amount_inr': _plan_price_inr(plan_code),
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

    return jsonify({
        'success': True,
        'billing': {
            'effective_plan': effective_plan,
            'subscription': {
                'plan': subscription.get('plan') or 'free',
                'status': subscription.get('status') or 'inactive',
                'current_period_start': subscription.get('current_period_start'),
                'current_period_end': subscription.get('current_period_end'),
                'cancel_at_period_end': bool(subscription.get('cancel_at_period_end'))
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


@app.route('/api/billing/create-order', methods=['POST'])
@require_auth
def billing_create_order():
    try:
        user_id = get_current_user_id()
        data = request.get_json(silent=True) or {}
        normalized = _normalize_subscription_plan(data.get('plan'))
        if not normalized or normalized[0] == 'free':
            return jsonify({'success': False, 'message': 'Invalid plan. Use 1_month, 3_month, or 12_month.'}), 400

        plan = normalized[0]
        amount_inr = _plan_price_inr(plan)
        if amount_inr <= 0:
            return jsonify({'success': False, 'message': 'Invalid plan price configuration'}), 500

        key_id, key_secret = _razorpay_keys()
        if not key_id or not key_secret:
            return jsonify({'success': False, 'message': 'Razorpay is not configured on server'}), 503

        receipt = f"sub_{plan}_{user_id[:8]}_{int(time.time())}"
        order = _create_razorpay_order(amount_inr=amount_inr, receipt=receipt, user_id=user_id, plan=plan)
        return jsonify({
            'success': True,
            'order': order,
            'plan': plan,
            'amount_inr': amount_inr,
            'razorpay_key_id': key_id
        })
    except Exception as e:
        logger.exception("Billing create order failed")
        return jsonify({'success': False, 'message': str(e)}), 500


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

        if not order_id or not payment_id or not signature or not plan:
            return jsonify({'success': False, 'message': 'order_id, payment_id, signature, and plan are required'}), 400

        normalized = _normalize_subscription_plan(plan)
        if not normalized or normalized[0] == 'free':
            return jsonify({'success': False, 'message': 'Invalid plan'}), 400

        if not _verify_razorpay_payment_signature(order_id, payment_id, signature):
            return jsonify({'success': False, 'message': 'Invalid Razorpay payment signature'}), 400

        activated = _activate_subscription_from_payment(user_id, normalized[0], payment_id=payment_id, order_id=order_id)
        if not activated:
            return jsonify({'success': False, 'message': 'Failed to activate subscription'}), 500

        return jsonify({
            'success': True,
            'message': 'Subscription activated successfully',
            'subscription': activated
        })
    except Exception as e:
        logger.exception("Billing verify payment failed")
        return jsonify({'success': False, 'message': str(e)}), 500


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

        if event in {'payment.captured', 'order.paid'} and is_valid_uuid(user_id):
            _activate_subscription_from_payment(user_id, plan, payment_id=payment_id, order_id=order_id)

        return jsonify({'success': True})
    except Exception as e:
        logger.exception("Billing webhook failed")
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/admin/users/<user_id>/password/send-reset', methods=['POST'])
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
        _admin_log_action('send_password_reset', user_id, {'email': email})
        return jsonify({'success': True, 'message': message, 'email': email})
    return jsonify({'success': False, 'message': message}), 400


@app.route('/api/admin/users/<user_id>/password/set-temp', methods=['POST'])
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
        _admin_log_action('set_temp_password', user_id, {'password_length': len(temporary_password)})
        return jsonify({'success': True, 'message': 'Temporary password has been set'})
    except Exception as e:
        logger.error("Admin set temp password failed: %s", e)
        return jsonify({'success': False, 'message': f'Failed to set temporary password: {str(e)}'}), 500


@app.route('/api/admin/users/<user_id>/email/update', methods=['POST'])
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
        _admin_log_action('update_user_email', user_id, {'new_email': new_email})
        return jsonify({'success': True, 'message': 'User email updated successfully', 'email': new_email})
    except Exception as e:
        logger.error("Admin update user email failed: %s", e)
        return jsonify({'success': False, 'message': f'Failed to update user email: {str(e)}'}), 500


@app.route('/api/admin/audit-logs', methods=['GET'])
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
        return jsonify({'success': False, 'message': f'Failed to fetch audit logs: {str(e)}'}), 500

# ============= ROUTES =============

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
            # Skip masked values (don't overwrite with ***) but allow False, 0, empty strings
            if isinstance(value, str) and value.startswith('***'):
                continue
            config[key] = value
        
        save_config(config, user_id=user_id)
        logger.info(f"Configuration saved. TEST_MODE={config.get('TEST_MODE')}")
        return jsonify({'success': True, 'message': 'Configuration saved!'})
    except Exception as e:
        logger.exception("Failed to save config")
        return jsonify({'success': False, 'message': str(e)}), 400

@app.route('/api/test-api', methods=['POST'])
@require_auth
def test_api():
    """Test AI API configuration"""
    try:
        from ai_provider import AIProvider
        user_id = get_current_user_id()
        config_obj = load_config(user_id)
        ai = AIProvider(
            config_obj.get('AI_PROVIDER', 'google'),
            api_keys={
                'GOOGLE_API_KEY': config_obj.get('GOOGLE_API_KEY', ''),
                'OPENAI_API_KEY': config_obj.get('OPENAI_API_KEY', ''),
                'ANTHROPIC_API_KEY': config_obj.get('ANTHROPIC_API_KEY', '')
            }
        )
        result = ai.generate("Say 'API is working' in 5 words", max_tokens=50)
        return jsonify({'success': True, 'message': f"API Working! Response: {result['text'][:100]}"})
    except Exception as e:
        return jsonify({'success': False, 'message': f"API Error: {str(e)}"})

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
        return jsonify({'success': False, 'message': f"LinkedIn Error: {str(e)}"})


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
    words = WORD_RE.findall(text or '')
    if len(words) <= max_words:
        return (text or '').strip()
    trimmed = ' '.join(words[:max_words]).strip()
    if trimmed and trimmed[-1] not in '.!?':
        trimmed += '.'
    return trimmed


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


def derive_hashtag_candidates(theme: str, industry: str, role: str, topics: list) -> list:
    tokens = []
    for raw in [theme, industry, role, *topics, 'LinkedIn', 'Professional', 'Business', 'Leadership']:
        if not raw:
            continue
        pieces = re.split(r'[^A-Za-z0-9_]+', str(raw))
        for piece in pieces:
            if len(piece) >= 3:
                tokens.append(piece)
    return normalize_hashtags(tokens)


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

    body = re.sub(r'\*{1,3}', '', body)
    body = re.sub(r'`+', '', body)
    body = re.sub(r'^\s*[-•]\s+', '', body, flags=re.MULTILINE)
    body = re.sub(r'\n{3,}', '\n\n', body)

    lines = [ln.strip() for ln in body.split('\n') if ln.strip()]
    flattened = ' '.join(lines)
    flattened = re.sub(r'\s{2,}', ' ', flattened).strip()
    if not flattened:
        return ''

    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', flattened) if s.strip()]
    if not sentences:
        return flattened

    paragraphs = []
    current = []
    for sentence in sentences:
        candidate = (' '.join(current + [sentence])).strip()
        if current and (len(candidate) > 260 or len(current) >= 2):
            paragraphs.append(' '.join(current).strip())
            current = [sentence]
        else:
            current.append(sentence)
    if current:
        paragraphs.append(' '.join(current).strip())

    return '\n\n'.join([p for p in paragraphs if p]).strip()


def ensure_engagement_hook(body: str, industry: str, role: str, topic: str) -> str:
    text = (body or '').strip()
    if not text:
        return text

    lines = text.split('\n')
    first_line = lines[0].strip() if lines else ''
    has_hook = bool(re.search(r'\?|\d', first_line)) or len(first_line) <= 90
    if has_hook:
        return text

    context = ', '.join([part for part in [industry, role] if part]).strip(', ')
    if context:
        hook = f"What separates high-performing {context} teams from everyone else?"
    elif topic:
        hook = f"What is the practical edge most teams miss about {topic}?"
    else:
        hook = "What are most teams missing when they try to scale results?"
    return f"{hook}\n\n{text}".strip()


def ensure_engagement_cta(body: str, target_audience: str, role: str) -> str:
    text = (body or '').strip()
    if not text:
        return text

    lower = text.lower()
    cta_markers = [
        'what do you think', 'what has worked', 'share your', 'drop a comment', 'comment below',
        'dm me', 'let me know', 'how are you', 'your take', 'agree or disagree'
    ]
    has_cta = any(marker in lower for marker in cta_markers) or text.endswith('?')
    if has_cta:
        return text

    audience_hint = target_audience or role or 'your team'
    cta_line = f"What has worked best for {audience_hint} in your experience?"
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


def enforce_linkedin_quality(body: str, industry: str, role: str, topic: str, target_audience: str, emoji_level: str) -> str:
    content = clean_linkedin_body(body)
    content = apply_emoji_policy(content, emoji_level)
    content = ensure_engagement_hook(content, industry, role, topic)
    content = ensure_engagement_cta(content, target_audience, role)
    content = wrap_linkedin_lines(content, width=170)
    return content.strip()


def _is_crypto_requested(industry: str, role: str, topic: str, topics: list, target_audience: str, post_goal: str) -> bool:
    combined = ' '.join([
        str(industry or ''),
        str(role or ''),
        str(topic or ''),
        str(target_audience or ''),
        str(post_goal or ''),
        ' '.join([str(item or '') for item in (topics or [])])
    ]).lower()
    crypto_terms = ['crypto', 'cryptocurrency', 'web3', 'blockchain', 'defi', 'token', 'nft', 'bitcoin', 'ethereum', 'exchange']
    return any(term in combined for term in crypto_terms)


def _forbidden_terms_for_context(industry: str, role: str, topic: str, topics: list, target_audience: str, post_goal: str) -> list:
    if _is_crypto_requested(industry, role, topic, topics, target_audience, post_goal):
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

@app.route('/api/generate-preview', methods=['GET', 'POST'])
def generate_preview():
    """Generate a preview post"""
    try:
        from ai_provider import AIProvider
        import random
        import config as cfg
        from rag_system_pgvector import RAGStore
        
        logger.info("Generate preview request received")
        
        req_data = request.get_json(silent=True) or {}

        user_id = get_current_user_id()
        if not is_valid_uuid(user_id):
            return jsonify({'success': False, 'message': 'Authentication required to generate content'}), 401

        can_generate, quota_meta = _check_generation_guardrail(user_id)
        if not can_generate:
            return jsonify({'success': False, **quota_meta}), 403
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
            req_data.pop('target_audience', None)
            req_data.pop('post_goal', None)
            req_data.pop('business_goal', None)
            req_data.pop('audience_type', None)
            req_data.pop('tone', None)

        config_obj = load_config(user_id)
        ai = AIProvider(
            config_obj.get('AI_PROVIDER', 'google'),
            api_keys={
                'GOOGLE_API_KEY': config_obj.get('GOOGLE_API_KEY', ''),
                'OPENAI_API_KEY': config_obj.get('OPENAI_API_KEY', ''),
                'ANTHROPIC_API_KEY': config_obj.get('ANTHROPIC_API_KEY', '')
            }
        )
        profile_key = (config_obj.get('CONTENT_PROFILE') or cfg.DEFAULT_PROFILE)
        profile = cfg.PROFILES.get(profile_key, cfg.PROFILES.get(cfg.DEFAULT_PROFILE, {}))

        user_topic = (req_data.get('topic') or '').strip()
        user_industry = _single_value(req_data.get('industry') or config_obj.get('CONTENT_INDUSTRY', ''))
        user_role = _single_value(req_data.get('role') or config_obj.get('USER_ROLE', ''))
        target_audience = (req_data.get('target_audience') or config_obj.get('AUDIENCE_KEYWORDS', '') or '').strip()
        post_tone = (req_data.get('tone') or config_obj.get('TONE', 'professional') or 'professional').strip().lower()
        audience_type = (req_data.get('audience_type') or 'individual').strip().lower()
        post_goal = (req_data.get('post_goal') or req_data.get('business_goal') or '').strip()
        business_goal = post_goal
        hashtag_count = clamp_int(req_data.get('hashtags', config_obj.get('HASHTAG_COUNT', 3)), 0, 10, 3)
        emoji_level = (req_data.get('emojis') or config_obj.get('EMOJI_USAGE', 'moderate') or 'moderate').strip().lower()
        topics = parse_content_topics(req_data, config_obj)

        kb_mode_raw = (req_data.get('kb_mode') or 'use_kb').strip().lower()
        if kb_mode_raw in {'no_kb', 'dont_use_kb', 'off'}:
            kb_mode = 'no_kb'
        elif kb_mode_raw in {'specific_files', 'specific', 'use_specific_files'}:
            kb_mode = 'specific_files'
        else:
            kb_mode = 'use_kb'

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
        
        content_themes = profile.get('content_themes', ['AI', 'Technology', 'Business'])
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
        
        post_formats = getattr(cfg, 'POST_FORMATS', ['article', 'opinion', 'announcement'])
        fmt = random.choice(post_formats) if post_formats else 'article'
        
        services = profile.get('company_info', {}).get('services', '')
        if user_industry or user_role or target_audience or topics:
            services = f"Professional insights for {user_industry or 'business and technology'} audiences, with focus on {user_role or 'strategy and execution'}."
        elif kb_mode == 'no_kb':
            services = f"Professional insights for {user_industry or 'business and technology'} audiences, with focus on {user_role or 'leadership and execution'}."

        forbidden_terms = _forbidden_terms_for_context(
            user_industry, user_role, user_topic, topics, target_audience, post_goal
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

        emoji_rule_map = {
            'none': 'Do not use emojis.',
            'minimal': 'Use at most 1-2 relevant emojis.',
            'moderate': 'Use 2-4 relevant emojis for readability.',
            'high': 'Use up to 5-7 relevant emojis without overstuffing.',
        }
        emoji_rule = emoji_rule_map.get(emoji_level, emoji_rule_map['moderate'])

        topic_hint = ', '.join(topics) if topics else 'industry trends and practical insights'
        audience_hint = 'B2B agency/company page' if audience_type in {'agency', 'b2b', 'company'} else 'Individual professional profile'
        target_audience_hint = target_audience or audience_hint

        if word_count_mode == 'ai_random':
            random_target = random.randint(110, 230)
            word_rule = f"Choose an optimal LinkedIn length naturally, around {random_target} words."
        else:
            word_rule = f"Keep the post between {min_words} and {max_words} words."

        kb_used = False
        kb_sources = []
        kb_context = ""
        kb_selected_file_count = 0
        kb_selected_file_ids = []
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

            if kb_mode != 'no_kb' and rag.is_built():
                user_files = rag.db.list_kb_files(user_id)
                user_file_ids = [str(row.get('id')) for row in user_files if row.get('id')]
                selected_file_ids = list(user_file_ids)

                if kb_mode == 'specific_files':
                    selected_file_ids = [file_id for file_id in specific_file_ids if file_id in user_file_ids]
                elif workspace_id:
                    blob = _ensure_user_feature_blob(user_id)
                    ws = _get_workspace(blob, workspace_id)
                    if ws:
                        if ws.get('use_all_files'):
                            selected_file_ids = list(user_file_ids)
                        else:
                            ws_file_ids = [str(file_id) for file_id in (ws.get('file_ids') or [])]
                            selected_file_ids = [file_id for file_id in ws_file_ids if file_id in user_file_ids]

                kb_selected_file_ids = selected_file_ids
                kb_selected_file_count = len(selected_file_ids)

                if selected_file_ids:
                    search_query = " | ".join(part for part in [theme, user_industry, user_role, services, topic_hint] if part)
                    filtered = len(selected_file_ids) < len(user_file_ids)
                    kb_hits = rag.similarity_search(search_query, k=4, file_ids=selected_file_ids if filtered else None)
                    if kb_hits:
                        kb_used = True
                        snippets = []
                        for idx, hit in enumerate(kb_hits[:3], start=1):
                            src = os.path.basename((hit.get('metadata') or {}).get('source', 'knowledge_base'))
                            kb_sources.append(src)
                            doc_text = (hit.get('document') or '').strip()
                            if doc_text:
                                snippets.append(f"[{idx}] Source: {src}\n{doc_text[:900]}")
                        kb_context = "\n\n".join(snippets)
        except Exception as kb_error:
            logger.warning("KB retrieval unavailable, falling back to LLM context: %s", kb_error)
        
        # Improved prompt for better human-like content
        if kb_used and kb_context:
            prompt = f"""Generate a professional LinkedIn post about: {theme}

    Company Context: {services}
    Audience Context: Industry={user_industry}, Role={user_role}
    Target Audience: {target_audience_hint}
    Publishing Context: {audience_hint}
    Content Topics: {topic_hint}
    Business Goal: {business_goal or 'Maximize relevance and engagement'}
    Desired Tone: {post_tone}

    Knowledge Base Excerpts:
    {kb_context}

    Requirements:
    - Use the knowledge-base excerpts above as the factual basis
    - If a fact is not in the excerpts, keep wording general and do not invent specifics
    - {domain_guardrail}
    - If knowledge-base excerpts include off-domain details, ignore those details
    - Write in a natural, human-like tone (not generic AI)
    - Keep the writing tone aligned with: {post_tone}
    - Reflect the selected audience context (industry and role) explicitly
    - Focus on these content topics: {topic_hint}
    - Avoid placeholder text like [Company Name], [Exchange Name], or [Exchange]
    - Include 1-2 actionable insights or takeaways
    - {word_rule}
    - {emoji_rule}
    - Do NOT include hashtags in the post body; place hashtags only at the end
    - End with exactly {hashtag_count} relevant hashtags

    Format: {fmt}

    Write ONLY the post content, nothing else."""
        else:
            prompt = f"""Generate a professional LinkedIn post about: {theme}

    Context: {services}
    Audience Context: Industry={user_industry}, Role={user_role}
    Target Audience: {target_audience_hint}
    Publishing Context: {audience_hint}
    Content Topics: {topic_hint}
    Business Goal: {business_goal or 'Maximize relevance and engagement'}
    Desired Tone: {post_tone}

    Requirements:
    - {domain_guardrail}
    - Write in a natural, human-like tone (not generic AI)
    - Keep the writing tone aligned with: {post_tone}
    - Reflect the selected audience context (industry and role) explicitly
    - Focus on these content topics: {topic_hint}
    - Avoid placeholder text like [Company Name], [Exchange Name], or [Exchange]
    - Be specific and authentic
    - Include 1-2 actionable insights or takeaways
    - {word_rule}
    - {emoji_rule}
    - Do NOT include hashtags in the post body; place hashtags only at the end
    - End with exactly {hashtag_count} relevant hashtags

    Format: {fmt}

    Write ONLY the post content, nothing else."""

        logger.info(f"Generating preview with prompt: {prompt[:100]}...")
        
        # Add timeout for AI generation
        import time
        start_time = time.time()
        try:
            result = ai.generate(prompt, max_tokens=500)
        except Exception as e:
            logger.error(f"AI generation failed after {time.time() - start_time:.2f}s: {e}")
            return jsonify({'success': False, 'message': f"AI generation failed: {str(e)}"}), 500
            
        if not result or 'text' not in result:
            logger.error(f"Invalid AI response: {result}")
            return jsonify({'success': False, 'message': "AI returned invalid response"}), 400
            
        content = (result['text'] or '').strip()
        
        if not content:
            return jsonify({'success': False, 'message': "Generated content is empty"}), 400
        
        generated_tags = normalize_hashtags(HASHTAG_RE.findall(content))
        body = enforce_linkedin_quality(
            remove_hashtags_from_body(content),
            user_industry,
            user_role,
            theme,
            target_audience_hint,
            emoji_level,
        )

        if word_count_mode == 'custom_range':
            word_total = words_count(body)
            if word_total < min_words or word_total > max_words:
                rewrite_prompt = f"""Rewrite the following LinkedIn post to be between {min_words} and {max_words} words.
Preserve meaning, tone, and practical value.
Do not include hashtags in the body.
\nPost:\n{body}\n"""
                try:
                    rewrite = ai.generate(rewrite_prompt, max_tokens=500)
                    rewritten_text = (rewrite.get('text') or '').strip()
                    if rewritten_text:
                        body = enforce_linkedin_quality(
                            remove_hashtags_from_body(rewritten_text),
                            user_industry,
                            user_role,
                            theme,
                            target_audience_hint,
                            emoji_level,
                        )
                except Exception as rewrite_error:
                    logger.warning("Word-range rewrite fallback failed: %s", rewrite_error)

            body = enforce_word_ceiling(body, max_words)

        forbidden_hits = _find_forbidden_terms(body, forbidden_terms)
        if forbidden_hits:
            rewrite_prompt = f"""Rewrite the LinkedIn post below while keeping the same intent, tone, and structure.
Hard rule: remove any references to these forbidden terms: {', '.join(forbidden_hits)}.
Keep the post focused strictly on: {selected_domain} and role: {user_role or 'professional'}.
Do not add markdown symbols (no ** or bullets) and keep readable short paragraphs.

Post:
{body}
"""
            try:
                rewrite = ai.generate(rewrite_prompt, max_tokens=500)
                rewritten_text = (rewrite.get('text') or '').strip()
                if rewritten_text:
                    body = enforce_linkedin_quality(
                        remove_hashtags_from_body(rewritten_text),
                        user_industry,
                        user_role,
                        theme,
                        target_audience_hint,
                        emoji_level,
                    )
            except Exception as rewrite_error:
                logger.warning("Domain guardrail rewrite failed: %s", rewrite_error)

        candidate_tags = derive_hashtag_candidates(theme, user_industry, user_role, topics)
        merged_tags = normalize_hashtags(generated_tags + candidate_tags)
        final_hashtags = merged_tags[:hashtag_count] if hashtag_count > 0 else []

        if final_hashtags:
            content = f"{body}\n\n{' '.join(final_hashtags)}".strip()
        else:
            content = body
        
        logger.info(f"Successfully generated preview: {content[:100]}...")
        
        _increment_monthly_usage(user_id, posts_generated=1, api_calls=1)

        return jsonify({
            'success': True,
            'content': content,
            'text': content,
            'post': content,
            'hashtags': final_hashtags,
            'theme': theme,
            'kb_used': kb_used,
            'kb_sources': sorted(list(set(kb_sources))),
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
                'business_goal': business_goal,
                'post_goal': post_goal,
                'target_audience': target_audience,
                'tone': post_tone
            }
        })
    except Exception as e:
        logger.exception("Generate preview failed")
        return jsonify({'success': False, 'message': f"Generation Error: {str(e)}"}), 500

@app.route('/api/posts', methods=['GET'])
@require_auth
def get_posts():
    """Get recently generated posts"""
    try:
        user_id = get_current_user_id()
        posts = [
            row for row in _read_json_list(POSTS_PATH)
            if str(row.get('user_id') or '').strip() == str(user_id)
        ]
        return jsonify({'success': True, 'posts': posts[-10:][::-1]})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/clear-post-history', methods=['POST'])
@require_auth
def clear_post_history():
    """Clear post history for current user (or all legacy entries without user_id)."""
    try:
        user_id = get_current_user_id()
        posts = _read_json_list(POSTS_PATH)

        has_user_scoped_rows = any(str(row.get('user_id') or '').strip() for row in posts)
        if has_user_scoped_rows:
            remaining = [
                row for row in posts
                if str(row.get('user_id') or '').strip() != str(user_id)
            ]
        else:
            remaining = []

        cleared_count = len(posts) - len(remaining)
        _write_json_list(POSTS_PATH, remaining)

        return jsonify({
            'success': True,
            'cleared': cleared_count,
            'message': f'Cleared {cleared_count} post(s) from history.'
        })
    except Exception as e:
        logger.exception("Failed to clear post history")
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/analytics', methods=['GET'])
@require_auth
def get_analytics():
    """Return real analytics calculated from persisted post data (no simulated metrics)."""
    try:
        user_id = get_current_user_id()
        posts = [
            row for row in _read_json_list(POSTS_PATH)
            if str(row.get('user_id') or '').strip() == str(user_id)
        ]
        scheduled_posts = [
            row for row in _read_json_list(SCHEDULED_POSTS_PATH)
            if str(row.get('user_id') or '').strip() == str(user_id)
        ]
        analytics = _calculate_real_analytics(posts, scheduled_posts)
        return jsonify({'success': True, 'analytics': analytics})
    except Exception as e:
        logger.exception("Failed to compute analytics")
        return jsonify({'success': False, 'message': str(e)}), 500


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
        return jsonify({'success': False, 'message': str(e)}), 500

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
        
        # Load existing scheduled posts
        scheduled_posts = _read_json_list(SCHEDULED_POSTS_PATH)

        effective_plan = _get_effective_plan(user_id)
        plan_limits = _get_plan_limits(effective_plan)
        scheduled_limit = _plan_limit_int(plan_limits, 'scheduled_posts', 10)

        if scheduled_limit <= 0:
            return jsonify({
                'success': False,
                'message': 'Scheduling automation is available on paid plans. Please upgrade to schedule posts on LinkedIn.'
            }), 403

        # Server-side protection: cap scheduled posts based on plan limits.
        user_scheduled_count = sum(1 for row in scheduled_posts if str(row.get('user_id') or '') == str(user_id))
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
        
        scheduled_posts.append(scheduled_post)
        
        # Save back
        _write_json_list(SCHEDULED_POSTS_PATH, scheduled_posts)
        
        return jsonify({'success': True, 'message': f'Post scheduled for {schedule_time}'})
    except Exception as e:
        logger.exception("Failed to schedule post")
        return jsonify({'success': False, 'message': f"Scheduling failed: {str(e)}"})

@app.route('/api/scheduled-posts', methods=['GET'])
@require_auth
def get_scheduled_posts():
    """Return scheduled posts ordered by schedule time"""
    try:
        user_id = get_current_user_id()
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
        return jsonify({'success': False, 'message': str(e)}), 500

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

        return jsonify({'success': True, 'message': 'Post rescheduled successfully'})
    except Exception as e:
        logger.exception("Failed to reschedule post")
        return jsonify({'success': False, 'message': str(e)}), 500

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

        return jsonify({'success': True, 'message': 'Scheduled post canceled'})
    except Exception as e:
        logger.exception("Failed to cancel scheduled post")
        return jsonify({'success': False, 'message': str(e)}), 500

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
            ai = AIProvider(
                config_obj.get('AI_PROVIDER', 'google'),
                api_keys={
                    'GOOGLE_API_KEY': config_obj.get('GOOGLE_API_KEY', ''),
                    'OPENAI_API_KEY': config_obj.get('OPENAI_API_KEY', ''),
                    'ANTHROPIC_API_KEY': config_obj.get('ANTHROPIC_API_KEY', '')
                }
            )
            profile_key = config_obj.get('CONTENT_PROFILE') or cfg.DEFAULT_PROFILE
            profile = cfg.PROFILES.get(profile_key, cfg.PROFILES[cfg.DEFAULT_PROFILE])
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
            fmt = random.choice(cfg.POST_FORMATS)
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
            
            result = ai.generate(prompt, max_tokens=500)
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
        
        # Save back
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
        return jsonify({'success': False, 'message': f"Posting failed: {str(e)}"})

# ============= KNOWLEDGE BASE & MODEL TRAINING ENDPOINTS =============

@app.route('/api/upload-knowledge-base', methods=['POST'])
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
        allowed_extensions = ('.pdf', '.docx')
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
                logger.warning("Skipping non-PDF/DOCX file: %s", filename)
                skipped_reasons.append(f"{filename}: Not a PDF or DOCX file")
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
            'training_queued': bool(training_result.get('via_queue')),
            'training_mode': 'queue' if training_result.get('via_queue') else 'local_background'
        })
    except Exception as e:
        logger.exception("Knowledge base upload failed")
        return jsonify({'success': False, 'message': f'Upload failed: {str(e)}'}), 500

@app.route('/api/personas', methods=['GET', 'POST'])
def manage_personas():
    """Get or update AI personas and writing styles"""
    try:
        personas_file = 'data/personas.json'
        
        # Default personas if none exist
        default_personas = {
            'professional': {
                'name': 'Professional Advisor',
                'description': 'Formal, authoritative, industry expert tone',
                'tone': 'professional',
                'language': 'English',
                'style': 'formal',
                'keywords': ['industry', 'expertise', 'strategic', 'insight'],
                'emoji_usage': 'minimal',
                'hashtag_count': 3
            },
            'casual_friendly': {
                'name': 'Friendly Innovator',
                'description': 'Casual, approachable, conversational tone',
                'tone': 'casual',
                'language': 'English',
                'style': 'conversational',
                'keywords': ['innovation', 'growth', 'community', 'value'],
                'emoji_usage': 'moderate',
                'hashtag_count': 5
            },
            'thought_leader': {
                'name': 'Thought Leader',
                'description': 'Insightful, visionary, trend-focused',
                'tone': 'inspirational',
                'language': 'English',
                'style': 'narrative',
                'keywords': ['future', 'vision', 'transformation', 'impact'],
                'emoji_usage': 'strategic',
                'hashtag_count': 4
            },
            'storyteller': {
                'name': 'Storyteller',
                'description': 'Narrative-driven, emotional connection',
                'tone': 'narrative',
                'language': 'English',
                'style': 'story-based',
                'keywords': ['experience', 'journey', 'learning', 'growth'],
                'emoji_usage': 'adaptive',
                'hashtag_count': 3
            }
        }
        
        if request.method == 'GET':
            # Return personas
            personas = default_personas
            if os.path.exists(personas_file):
                try:
                    with open(personas_file, 'r') as f:
                        personas = json.load(f)
                except:
                    pass
            return jsonify({'success': True, 'personas': personas})
        
        else:  # POST
            # Update personas
            data = request.get_json()
            if not data or 'personas' not in data:
                return jsonify({'success': False, 'message': 'Invalid persona data'}), 400
            
            os.makedirs('data', exist_ok=True)
            with open(personas_file, 'w') as f:
                json.dump(data['personas'], f, indent=2)
            
            return jsonify({
                'success': True,
                'message': 'Personas updated successfully'
            })
    except Exception as e:
        logger.exception("Persona management failed")
        return jsonify({'success': False, 'message': f'Failed: {str(e)}'}), 500

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
        return jsonify({'success': False, 'message': f'Training failed: {str(e)}'}), 500


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
        return jsonify({'success': False, 'message': f'Failed to index latest file: {str(e)}'}), 500

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
        return jsonify({
            'success': False,
            'message': f'Status check failed: {str(e)}'
        }), 500

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
        return jsonify({
            'success': False,
            'message': f'Failed to list files: {str(e)}'
        }), 500


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
        return jsonify({'success': False, 'message': str(e)}), 500


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
        return jsonify({'success': False, 'message': str(e)}), 500


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
        return jsonify({'success': False, 'message': str(e)}), 500


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
        return jsonify({'success': False, 'message': str(e)}), 500


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
        return jsonify({'success': False, 'message': str(e)}), 500


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
        return jsonify({'success': False, 'message': str(e)}), 500


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
        return jsonify({'success': False, 'message': str(e)}), 500

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
        return jsonify({
            'success': False,
            'message': f'Delete failed: {str(e)}'
        }), 500

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
    """Enhanced content generation with industry/role personalization"""
    try:
        data = request.get_json() or {}
        industry = data.get('industry', 'tech')
        role = data.get('role', 'cto')
        topic = data.get('topic', '')
        hashtags_count = int(data.get('hashtags', 3))
        emoji_level = data.get('emojis', 'moderate')
        custom_topics = data.get('topics', [])
        
        user_id = get_current_user_id()
        config_obj = load_config(user_id)
        ai_provider = config_obj.get('AI_PROVIDER', 'google')
        
        # Build enhanced prompt based on industry and role
        industry_context = {
            'tech': 'Software engineering, cloud computing, and digital innovation',
            'finance': 'Financial systems, blockchain, and modern banking',
            'healthcare': 'Healthcare technology, patient care, and medical innovation',
            'crypto': 'Cryptocurrency, blockchain, DeFi, and web3 technologies',
            'saas': 'Software as a service, product-market fit, and scaling startups',
            'ecommerce': 'E-commerce, customer experience, and digital commerce trends'
        }
        
        role_perspective = {
            'ceo': 'strategic business decisions and company vision',
            'cto': 'technical architecture and technology decisions',
            'dev': 'hands-on coding, best practices, and technical tools',
            'pm': 'user experience, product strategy, and metrics',
            'hr': 'company culture, hiring, and employee engagement',
            'finance': 'financial optimization and business metrics',
            'ops': 'operational efficiency and process improvement',
            'marketing': 'growth strategies and audience engagement',
            'sales': 'customer relationships and business development'
        }
        
        emoji_prompt = {
            'none': 'Do not use any emojis.',
            'minimal': 'Use 1-2 emojis strategically.',
            'moderate': 'Use 2-4 emojis to enhance readability. (Recommended)',
            'high': 'Use 5-8 emojis to maximize engagement.'
        }
        
        topic_str = ', '.join(custom_topics) if custom_topics else 'industry trends, insights, or announcements'
        
        prompt = f"""Generate a LinkedIn post from the perspective of a {role_perspective.get(role, 'professional')}.

**Industry Context**: {industry_context.get(industry, industry)}
**Your Role**: {role}
**Topics**: {topic_str}
**Specific Topic**: {topic if topic else 'Choose something relevant'}
**Hashtags**: Create exactly {hashtags_count} relevant hashtags for maximum reach
**Emoji Style**: {emoji_prompt.get(emoji_level, 'Use 2-4 strategic emojis')}

Guidelines:
- Write in a professional yet approachable tone
- Include a hook in the first line to grab attention
- Target audience: {role} professionals in {industry}
- Post should be 150-300 words for optimal LinkedIn engagement
- Include a clear CTA (Call to Action)
- End with {hashtags_count} relevant hashtags
- Keep paragraphs short (2-3 sentences max)
- Make it shareable and valuable

Format: 
[Hook/Opening Line]

[2-3 body paragraphs with insights]

[CTA]

[Hashtags]"""

        ai = AIProvider(
            ai_provider,
            api_keys={
                'GOOGLE_API_KEY': config_obj.get('GOOGLE_API_KEY', ''),
                'OPENAI_API_KEY': config_obj.get('OPENAI_API_KEY', ''),
                'ANTHROPIC_API_KEY': config_obj.get('ANTHROPIC_API_KEY', '')
            }
        )
        result = ai.generate(prompt, max_tokens=800)
        content = result.get('text', result.get('content', '')).strip()
        content = clean_linkedin_body(remove_hashtags_from_body(content))
        
        return jsonify({
            'success': True,
            'content': content,
            'industry': industry,
            'role': role,
            'hashtags_count': hashtags_count,
            'emoji_level': emoji_level
        })
    except Exception as e:
        logger.exception(f"Premium preview generation failed: {e}")
        return jsonify({'success': False, 'message': str(e)}), 400

@app.route('/api/enterprise-stats', methods=['GET'])
@require_auth
def get_enterprise_stats():
    """Get enhanced analytics for premium users"""
    try:
        user_id = get_current_user_id()
        posts = [
            row for row in _read_json_list(POSTS_PATH)
            if str(row.get('user_id') or '').strip() == str(user_id)
        ]

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
        return jsonify({'error': str(e)}), 400

if __name__ == '__main__':
    missing_auth = []
    if not (os.getenv('SUPABASE_URL') or '').strip():
        missing_auth.append('SUPABASE_URL')
    if not ((os.getenv('SUPABASE_ANON_KEY') or '').strip() or (os.getenv('SUPABASE_KEY') or '').strip() or (os.getenv('SUPABASE_SERVICE_ROLE_KEY') or '').strip()):
        missing_auth.append('SUPABASE_ANON_KEY|SUPABASE_KEY|SUPABASE_SERVICE_ROLE_KEY')
    if missing_auth:
        logger.error("Auth misconfigured. Missing: %s", ', '.join(missing_auth))

    # Start the scheduler in background
    start_scheduler()
    start_auth_keepalive()
    
    # Disable debug mode in production
    debug_mode = os.getenv('FLASK_ENV') != 'production'
    app.run(
        debug=debug_mode,
        use_reloader=False,
        port=int(os.getenv('PORT', 5050)),
        host='0.0.0.0'
    )
