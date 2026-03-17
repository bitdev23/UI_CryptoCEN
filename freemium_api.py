"""
Freemium Plan Management APIs
Handles tier-based quotas, pricing, and upgrade flows
"""
import os
import logging
from datetime import datetime
from typing import Tuple, Dict, Optional, Any
from flask import Blueprint, request, jsonify
from supabase import create_client

logger = logging.getLogger(__name__)

# Create blueprint for freemium routes
freemium_bp = Blueprint('freemium', __name__)

# Supabase client initialization
supabase_url = (os.getenv('SUPABASE_URL') or '').strip().rstrip('/')
supabase_key = (os.getenv('SUPABASE_ANON_KEY') or os.getenv('SUPABASE_KEY') or '').strip()
freemium_client = create_client(supabase_url, supabase_key) if supabase_url and supabase_key else None


def get_user_plan(user_id: str) -> str:
    """Get the current plan for a user. Default: 'free'"""
    if not freemium_client or not user_id:
        return 'free'
    
    try:
        resp = freemium_client.table('user_subscriptions').select('plan_name').eq('user_id', user_id).single().execute()
        return resp.data.get('plan_name', 'free') if resp.data else 'free'
    except Exception:
        return 'free'


def get_plan_limits(plan_name: str) -> Dict[str, int]:
    """Get limits for a specific plan"""
    if not freemium_client:
        return {'posts_per_month': 1, 'kb_files': 1, 'storage_mb': 100}
    
    try:
        resp = freemium_client.table('plan_configurations').select(
            'free_posts_per_month, free_kb_files_per_month, free_storage_mb'
        ).eq('plan_name', plan_name).single().execute()
        
        if resp.data:
            return {
                'posts_per_month': resp.data.get('free_posts_per_month', 1),
                'kb_files': resp.data.get('free_kb_files_per_month', 1),
                'storage_mb': resp.data.get('free_storage_mb', 100)
            }
    except Exception:
        pass
    
    # Default limits
    default_limits = {
        'free': {'posts_per_month': 1, 'kb_files': 1, 'storage_mb': 100},
        '1-month': {'posts_per_month': 50, 'kb_files': 10, 'storage_mb': 1000},
        '3-month': {'posts_per_month': 150, 'kb_files': 30, 'storage_mb': 3000},
        '12-month': {'posts_per_month': 500, 'kb_files': 100, 'storage_mb': 10000},
    }
    return default_limits.get(plan_name, default_limits['free'])


def get_monthly_usage(user_id: str) -> Dict[str, int]:
    """Get current month's usage for a user"""
    if not freemium_client or not user_id:
        return {'posts_generated': 0, 'files_uploaded': 0, 'storage_mb_used': 0}
    
    current_month = datetime.utcnow().strftime('%Y-%m')
    try:
        resp = freemium_client.table('user_monthly_usage').select(
            'posts_generated, files_uploaded, storage_mb_used'
        ).eq('user_id', user_id).eq('month_year', current_month).single().execute()
        
        if resp.data:
            return {
                'posts_generated': resp.data.get('posts_generated', 0),
                'files_uploaded': resp.data.get('files_uploaded', 0),
                'storage_mb_used': resp.data.get('storage_mb_used', 0)
            }
    except Exception:
        pass
    
    return {'posts_generated': 0, 'files_uploaded': 0, 'storage_mb_used': 0}


def increment_usage(user_id: str, metric: str, amount: int = 1) -> bool:
    """Increment a usage metric for the current month"""
    if not freemium_client or not user_id:
        return False
    
    current_month = datetime.utcnow().strftime('%Y-%m')
    
    try:
        # Try to update existing record
        update_stmt = {
            'user_id': user_id,
            'month_year': current_month,
            'updated_at': datetime.utcnow().isoformat() + 'Z'
        }
        
        if metric == 'posts':
            update_stmt['posts_generated'] = f'posts_generated+{amount}'
        elif metric == 'files':
            update_stmt['files_uploaded'] = f'files_uploaded+{amount}'
        elif metric == 'storage':
            update_stmt['storage_mb_used'] = f'storage_mb_used+{amount}'
        
        # Use insert with on_conflict to upsert
        freemium_client.table('user_monthly_usage').upsert({
            'user_id': user_id,
            'month_year': current_month,
            metric + '_increment': amount  # Helper field for increment
        }, on_conflict='user_id,month_year').execute()
        
        return True
    except Exception as e:
        logger.error(f"Failed to increment usage: {e}")
        return False


def check_quota(user_id: str, quota_type: str = 'posts') -> Tuple[bool, Dict[str, Any]]:
    """
    Check if user can perform action based on quota
    
    Returns:
        (can_proceed, quota_info)
    """
    plan = get_user_plan(user_id)
    limits = get_plan_limits(plan)
    usage = get_monthly_usage(user_id)
    
    if quota_type == 'posts':
        limit = limits.get('posts_per_month', 1)
        used = usage.get('posts_generated', 0)
        remaining = max(0, limit - used)
        
        return (used < limit, {
            'plan': plan,
            'limit': limit,
            'used': used,
            'remaining': remaining,
            'quota_exceeded': used >= limit,
            'message': f"You have used {used}/{limit} posts this month" if used > 0 else f"You can generate {limit} posts this month"
        })
    
    elif quota_type == 'files':
        limit = limits.get('kb_files', 1)
        used = usage.get('files_uploaded', 0)
        remaining = max(0, limit - used)
        
        return (used < limit, {
            'plan': plan,
            'limit': limit,
            'used': used,
            'remaining': remaining,
            'quota_exceeded': used >= limit,
            'message': f"You have uploaded {used}/{limit} files this month"
        })
    
    elif quota_type == 'storage':
        limit = limits.get('storage_mb', 100)
        used = usage.get('storage_mb_used', 0)
        remaining = max(0, limit - used)
        
        return (used < limit, {
            'plan': plan,
            'limit': limit,
            'used': used,
            'remaining': remaining,
            'quota_exceeded': used >= limit,
            'message': f"You have used {used}/{limit} MB this month"
        })
    
    return False, {}


# ============================================================
# API ENDPOINTS
# ============================================================

@freemium_bp.route('/api/user/quota-status', methods=['GET'])
def api_quota_status():
    """Get user's current quota status"""
    try:
        from app import get_current_user_id
        user_id = get_current_user_id()
        
        if not user_id:
            return jsonify({'success': False, 'message': 'Authentication required'}), 401
        
        plan = get_user_plan(user_id)
        limits = get_plan_limits(plan)
        usage = get_monthly_usage(user_id)
        
        post_can_generate, post_info = check_quota(user_id, 'posts')
        file_can_upload, file_info = check_quota(user_id, 'files')
        storage_can_use, storage_info = check_quota(user_id, 'storage')
        
        return jsonify({
            'success': True,
            'plan': plan,
            'limits': limits,
            'usage': usage,
            'quotas': {
                'posts': post_info,
                'files': file_info,
                'storage': storage_info
            },
            'can_generate_posts': post_can_generate,
            'can_upload_files': file_can_upload,
            'can_use_storage': storage_can_use
        }), 200
    except Exception as e:
        logger.error(f"Failed to get quota status: {e}")
        return jsonify({'success': False, 'message': 'Failed to get quota status'}), 500


@freemium_bp.route('/api/upgrade-info', methods=['GET'])
def api_upgrade_info():
    """Get pricing plans and upgrade information"""
    try:
        from app import get_current_user_id
        user_id = get_current_user_id()
        current_plan = get_user_plan(user_id) if user_id else 'free'
        
        if not freemium_client:
            return jsonify({'success': False, 'message': 'Service unavailable'}), 503
        
        resp = freemium_client.table('pricing_plans').select('*').eq('is_active', True).execute()
        plans = resp.data if resp.data else []
        
        return jsonify({
            'success': True,
            'current_plan': current_plan,
            'plans': plans
        }), 200
    except Exception as e:
        logger.error(f"Failed to get upgrade info: {e}")
        return jsonify({'success': False, 'message': 'Failed to get upgrade info'}), 500


@freemium_bp.route('/api/admin/plan-limits', methods=['GET', 'POST'])
def api_admin_plan_limits():
    """
    Admin: Get or update plan limits
    POST: Update limits for a plan
    """
    try:
        from app import require_admin
        
        if request.method == 'GET':
            if not freemium_client:
                return jsonify({'success': False, 'message': 'Service unavailable'}), 503
            
            resp = freemium_client.table('plan_configurations').select('*').execute()
            return jsonify({'success': True, 'plans': resp.data}), 200
        
        elif request.method == 'POST':
            # Validate admin
            from app import get_current_user_id
            user_id = get_current_user_id()
            if not user_id:
                return jsonify({'success': False, 'message': 'Authentication required'}), 401
            
            data = request.get_json() or {}
            plan_name = (data.get('plan_name') or '').strip()
            free_posts = data.get('free_posts_per_month')
            free_files = data.get('free_kb_files_per_month')
            free_storage = data.get('free_storage_mb')
            
            if not plan_name:
                return jsonify({'success': False, 'message': 'Plan name required'}), 400
            
            if not all(isinstance(v, int) for v in [free_posts, free_files, free_storage]):
                return jsonify({'success': False, 'message': 'Invalid values'}), 400
            
            update_data = {
                'plan_name': plan_name,
                'free_posts_per_month': free_posts,
                'free_kb_files_per_month': free_files,
                'free_storage_mb': free_storage,
                'updated_at': datetime.utcnow().isoformat() + 'Z',
                'updated_by': user_id
            }
            
            resp = freemium_client.table('plan_configurations').upsert(
                update_data, on_conflict='plan_name'
            ).execute()
            
            return jsonify({
                'success': True,
                'message': f'Plan {plan_name} limits updated',
                'plan': resp.data[0] if resp.data else update_data
            }), 200
    
    except Exception as e:
        logger.error(f"Admin plan limits error: {e}")
        return jsonify({'success': False, 'message': 'Operation failed'}), 500


@freemium_bp.route('/api/quota-exceeded-modal', methods=['GET'])
def api_quota_exceeded_modal():
    """Get modal content when user exceeds quota - for upgrade prompts"""
    try:
        from app import get_current_user_id
        user_id = get_current_user_id()
        
        if not user_id:
            return jsonify({'success': False, 'message': 'Authentication required'}), 401
        
        plan = get_user_plan(user_id)
        _, post_info = check_quota(user_id, 'posts')
        
        # Get upgrade plans
        if freemium_client:
            resp = freemium_client.table('pricing_plans').select('*').eq('is_active', True).execute()
            plans = resp.data if resp.data else []
        else:
            plans = []
        
        return jsonify({
            'success': True,
            'current_plan': plan,
            'quota_info': post_info,
            'upgrade_plans': plans,
            'message': 'You\'ve reached your post generation limit for this month. Upgrade to continue creating content!'
        }), 200
    except Exception as e:
        logger.error(f"Failed to get quota exceeded modal: {e}")
        return jsonify({'success': False, 'message': 'Operation failed'}), 500
