"""
Freemium quota management module.
Extends the existing quota system to allow admin control of plan limits.
"""
import json
import os
import logging
from functools import wraps
from flask import Blueprint, jsonify, request

logger = logging.getLogger(__name__)

# Constants
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
PLAN_LIMITS_PATH = os.path.join(DATA_DIR, 'plan_limits.json')


def load_plan_limits() -> dict:
    """Load plan limits from JSON file, fallback to defaults if not found."""
    if not os.path.exists(PLAN_LIMITS_PATH):
        return get_default_plan_limits()
    
    try:
        with open(PLAN_LIMITS_PATH, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Failed to load plan limits: {e}")
        return get_default_plan_limits()


def save_plan_limits(limits: dict) -> bool:
    """Save plan limits to JSON file."""
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(PLAN_LIMITS_PATH, 'w') as f:
            json.dump(limits, f, indent=2)
        logger.info("Plan limits saved successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to save plan limits: {e}")
        return False


def get_default_plan_limits() -> dict:
    """Return default plan limits."""
    return {
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


def get_plan_limits(plan: str) -> dict:
    """Get limits for a specific plan."""
    limits = load_plan_limits()
    return limits.get(plan, limits.get('free', {}))


def create_freemium_blueprint():
    """Create and return the freemium Flask blueprint."""
    freemium_bp = Blueprint('freemium', __name__)
    
    @freemium_bp.route('/api/admin/plan-limits', methods=['GET'])
    def get_all_plan_limits():
        """Get all current plan limits (admin endpoint)."""
        try:
            from auth import verify_token
            
            # Verify admin token
            token = request.headers.get('Authorization', '').replace('Bearer ', '')
            if not token:
                return jsonify({'success': False, 'message': 'Unauthorized'}), 401
            
            auth_result = verify_token(token)
            if not auth_result or not auth_result.get('user'):
                return jsonify({'success': False, 'message': 'Invalid token'}), 401
            
            # Check if user is admin (this is a simple check - in production you'd verify via database)
            user_email = auth_result.get('user', {}).get('email', '')
            admin_emails = os.getenv('ADMIN_EMAILS', '').split(',')
            is_admin = any(email.strip().lower() == user_email.lower() for email in admin_emails if email.strip())
            
            if not is_admin:
                return jsonify({'success': False, 'message': 'Admin access required'}), 403
            
            limits = load_plan_limits()
            return jsonify({
                'success': True,
                'plan_limits': limits
            }), 200
            
        except Exception as e:
            logger.error(f"Error fetching plan limits: {e}")
            return jsonify({'success': False, 'message': 'Failed to fetch plan limits'}), 500
    
    @freemium_bp.route('/api/admin/plan-limits', methods=['POST'])
    def update_plan_limits():
        """Update plan limits (admin endpoint)."""
        try:
            from auth import verify_token
            
            # Verify admin token
            token = request.headers.get('Authorization', '').replace('Bearer ', '')
            if not token:
                return jsonify({'success': False, 'message': 'Unauthorized'}), 401
            
            auth_result = verify_token(token)
            if not auth_result or not auth_result.get('user'):
                return jsonify({'success': False, 'message': 'Invalid token'}), 401
            
            # Check admin access
            user_email = auth_result.get('user', {}).get('email', '')
            admin_emails = os.getenv('ADMIN_EMAILS', '').split(',')
            is_admin = any(email.strip().lower() == user_email.lower() for email in admin_emails if email.strip())
            
            if not is_admin:
                return jsonify({'success': False, 'message': 'Admin access required'}), 403
            
            data = request.get_json() or {}
            plan = data.get('plan', '').strip()
            updates = data.get('limits', {})
            
            if not plan:
                return jsonify({'success': False, 'message': 'Plan name required'}), 400
            
            if not isinstance(updates, dict):
                return jsonify({'success': False, 'message': 'Limits must be a dictionary'}), 400
            
            # Load current limits and update
            current_limits = load_plan_limits()
            if plan not in current_limits:
                current_limits[plan] = {}
            
            for key, value in updates.items():
                try:
                    current_limits[plan][key] = int(value)
                except (ValueError, TypeError):
                    return jsonify({
                        'success': False,
                        'message': f'Invalid value for {key}: must be an integer'
                    }), 400
            
            # Save updated limits
            if save_plan_limits(current_limits):
                return jsonify({
                    'success': True,
                    'message': f'Plan limits updated for {plan}',
                    'plan_limits': current_limits
                }), 200
            else:
                return jsonify({
                    'success': False,
                    'message': 'Failed to save plan limits'
                }), 500
                
        except Exception as e:
            logger.error(f"Error updating plan limits: {e}")
            return jsonify({'success': False, 'message': 'Failed to update plan limits'}), 500
    
    @freemium_bp.route('/api/user/quota-status', methods=['GET'])
    def get_quota_status():
        """Get current user's quota status."""
        try:
            from auth import verify_token
            
            token = request.headers.get('Authorization', '').replace('Bearer ', '')
            if not token:
                return jsonify({'success': False, 'message': 'Unauthorized'}), 401
            
            auth_result = verify_token(token)
            if not auth_result or not auth_result.get('user'):
                return jsonify({'success': False, 'message': 'Invalid token'}), 401
            
            # Note: The actual quota checking is done in app.py's _check_generation_guardrail()
            # This endpoint just returns the available plans for display
            limits = load_plan_limits()
            return jsonify({
                'success': True,
                'plan_limits': limits
            }), 200
            
        except Exception as e:
            logger.error(f"Error fetching quota status: {e}")
            return jsonify({'success': False, 'message': 'Failed to fetch quota status'}), 500
    
    return freemium_bp
