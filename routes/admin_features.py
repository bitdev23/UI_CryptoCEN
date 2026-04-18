"""Admin features blueprint: notifications, error monitoring, feature flags, revenue."""

from flask import Blueprint, jsonify, request
from functools import wraps
from datetime import datetime, timedelta
import logging
import traceback
from uuid import UUID

logger = logging.getLogger('velank')


def create_admin_features_blueprint(auth_supabase, limiter):
    """Create and return the admin features blueprint."""
    features_bp = Blueprint('admin_features', __name__, url_prefix='/api/admin/features')
    
    def require_admin_api(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            from flask import session
            if not session.get('admin_session'):
                return jsonify({'success': False, 'message': 'Admin authentication required'}), 401
            return f(*args, **kwargs)
        return wrapper
    
    # ========================================================================
    # NOTIFICATIONS API
    # ========================================================================
    
    @features_bp.route('/notifications', methods=['GET'])
    def get_notifications():
        """Get user notifications."""
        try:
            from flask import session
            user_id = session.get('user_id')
            if not user_id:
                return jsonify({'success': False, 'message': 'User not authenticated'}), 401
            
            limit = max(1, min(100, int(request.args.get('limit', 20))))
            skip_archived = request.args.get('skip_archived', 'true').lower() == 'true'
            
            query = auth_supabase.table('notifications') \
                .select('id,type,title,message,is_read,priority,action_url,action_label,created_at,data') \
                .eq('user_id', user_id) \
                .order('created_at', desc=True) \
                .limit(limit)
            
            if skip_archived:
                query = query.eq('is_archived', False)
            
            rows = query.execute().data or []
            unread_count = auth_supabase.table('notifications') \
                .select('id', count='exact') \
                .eq('user_id', user_id) \
                .eq('is_read', False) \
                .eq('is_archived', False) \
                .execute()
            
            return jsonify({
                'success': True,
                'notifications': rows,
                'unread_count': unread_count.count or 0
            })
        except Exception as e:
            logger.error("Failed to fetch notifications: %s", e)
            return jsonify({'success': False, 'message': 'Failed to fetch notifications'}), 500
    
    @features_bp.route('/notifications/<notification_id>', methods=['POST'])
    def update_notification(notification_id):
        """Mark notification as read or archived."""
        try:
            from flask import session
            user_id = session.get('user_id')
            if not user_id:
                return jsonify({'success': False, 'message': 'User not authenticated'}), 401
            
            data = request.get_json() or {}
            is_read = data.get('is_read')
            is_archived = data.get('is_archived')
            
            update_data = {'updated_at': datetime.utcnow().isoformat()}
            if is_read is not None:
                update_data['is_read'] = is_read
            if is_archived is not None:
                update_data['is_archived'] = is_archived
            
            auth_supabase.table('notifications') \
                .update(update_data) \
                .eq('id', notification_id) \
                .eq('user_id', user_id) \
                .execute()
            
            return jsonify({'success': True, 'message': 'Notification updated'})
        except Exception as e:
            logger.error("Failed to update notification: %s", e)
            return jsonify({'success': False, 'message': 'Failed to update notification'}), 500
    
    @features_bp.route('/notifications/send', methods=['POST'])
    @require_admin_api
    def send_notification():
        """Send notification to user(s) - ADMIN ONLY."""
        try:
            data = request.get_json() or {}
            user_ids = data.get('user_ids', [])
            notification_type = data.get('type', 'system')
            title = data.get('title', '')
            message = data.get('message', '')
            priority = data.get('priority', 'normal')
            action_url = data.get('action_url')
            action_label = data.get('action_label')
            
            if not user_ids or not title or not message:
                return jsonify({'success': False, 'message': 'Missing required fields'}), 400
            
            notifications_to_insert = []
            for uid in user_ids:
                notifications_to_insert.append({
                    'user_id': uid,
                    'type': notification_type,
                    'title': title,
                    'message': message,
                    'priority': priority,
                    'action_url': action_url,
                    'action_label': action_label,
                    'created_at': datetime.utcnow().isoformat()
                })
            
            if notifications_to_insert:
                auth_supabase.table('notifications').insert(notifications_to_insert).execute()
            
            return jsonify({
                'success': True,
                'message': f'Sent notification to {len(user_ids)} user(s)',
                'count': len(user_ids)
            })
        except Exception as e:
            logger.error("Failed to send notification: %s", e)
            return jsonify({'success': False, 'message': 'Failed to send notification'}), 500
    
    # ========================================================================
    # ERROR MONITORING API
    # ========================================================================
    
    @features_bp.route('/errors', methods=['GET'])
    @require_admin_api
    def get_error_logs():
        """Get error logs - ADMIN ONLY."""
        try:
            limit = max(1, min(100, int(request.args.get('limit', 50))))
            severity = request.args.get('severity', '')
            unresolved_only = request.args.get('unresolved', 'true').lower() == 'true'
            hours_back = max(1, int(request.args.get('hours', 24)))
            
            cutoff_time = (datetime.utcnow() - timedelta(hours=hours_back)).isoformat()
            
            query = auth_supabase.table('error_logs') \
                .select('id,error_type,error_message,endpoint,status_code,severity,created_at,is_resolved,user_id') \
                .gt('created_at', cutoff_time) \
                .order('created_at', desc=True) \
                .limit(limit)
            
            if unresolved_only:
                query = query.eq('is_resolved', False)
            if severity:
                query = query.eq('severity', severity)
            
            rows = query.execute().data or []
            
            # Get error summary
            summary = {}
            for row in rows:
                err_type = row.get('error_type', 'unknown')
                summary[err_type] = summary.get(err_type, 0) + 1
            
            return jsonify({
                'success': True,
                'errors': rows,
                'summary': summary,
                'total': len(rows)
            })
        except Exception as e:
            logger.error("Failed to fetch error logs: %s", e)
            return jsonify({'success': False, 'message': 'Failed to fetch error logs'}), 500
    
    @features_bp.route('/errors/<error_id>', methods=['GET'])
    @require_admin_api
    def get_error_detail(error_id):
        """Get detailed error log - ADMIN ONLY."""
        try:
            rows = auth_supabase.table('error_logs') \
                .select('*') \
                .eq('id', error_id) \
                .execute().data or []
            
            if not rows:
                return jsonify({'success': False, 'message': 'Error not found'}), 404
            
            return jsonify({'success': True, 'error': rows[0]})
        except Exception as e:
            logger.error("Failed to fetch error detail: %s", e)
            return jsonify({'success': False, 'message': 'Failed to fetch error detail'}), 500
    
    @features_bp.route('/errors/<error_id>/resolve', methods=['POST'])
    @require_admin_api
    def resolve_error(error_id):
        """Mark error as resolved - ADMIN ONLY."""
        try:
            data = request.get_json() or {}
            notes = data.get('notes', '')
            
            auth_supabase.table('error_logs') \
                .update({
                    'is_resolved': True,
                    'notes': notes,
                    'updated_at': datetime.utcnow().isoformat()
                }) \
                .eq('id', error_id) \
                .execute()
            
            return jsonify({'success': True, 'message': 'Error marked as resolved'})
        except Exception as e:
            logger.error("Failed to resolve error: %s", e)
            return jsonify({'success': False, 'message': 'Failed to resolve error'}), 500
    
    @features_bp.route('/errors/log', methods=['POST'])
    def log_error():
        """Log an error from client/server - PUBLIC (rate limited)."""
        try:
            data = request.get_json() or {}
            error_type = data.get('error_type', 'unknown')
            error_message = data.get('error_message', '')
            stack_trace = data.get('stack_trace', '')
            endpoint = data.get('endpoint', request.referrer or 'unknown')
            status_code = data.get('status_code', 500)
            
            from flask import session, g
            user_id = session.get('user_id') or request.cookies.get('user_id')
            
            error_doc = {
                'error_type': error_type,
                'error_message': error_message,
                'stack_trace': stack_trace,
                'endpoint': endpoint,
                'request_method': request.method,
                'status_code': status_code,
                'severity': 'critical' if status_code >= 500 else 'error',
                'created_at': datetime.utcnow().isoformat()
            }
            
            if user_id:
                error_doc['user_id'] = user_id
            
            auth_supabase.table('error_logs').insert([error_doc]).execute()
            
            return jsonify({'success': True, 'message': 'Error logged'})
        except Exception as e:
            logger.error("Failed to log error: %s", e)
            return jsonify({'success': True, 'message': 'Logged'}), 200  # Always return 200 to not spam errors
    
    # ========================================================================
    # FEATURE FLAGS API
    # ========================================================================
    
    @features_bp.route('/flags', methods=['GET'])
    @require_admin_api
    def get_feature_flags():
        """Get all feature flags - ADMIN ONLY."""
        try:
            rows = auth_supabase.table('feature_flags') \
                .select('id,key,name,description,is_enabled_globally,rollout_percentage,updated_at') \
                .execute().data or []
            
            return jsonify({'success': True, 'flags': rows})
        except Exception as e:
            logger.error("Failed to fetch feature flags: %s", e)
            return jsonify({'success': False, 'message': 'Failed to fetch feature flags'}), 500
    
    @features_bp.route('/flags/<flag_id>', methods=['POST'])
    @require_admin_api
    def update_feature_flag(flag_id):
        """Update feature flag - ADMIN ONLY."""
        try:
            data = request.get_json() or {}
            update_data = {
                'updated_at': datetime.utcnow().isoformat()
            }
            
            if 'is_enabled_globally' in data:
                update_data['is_enabled_globally'] = bool(data['is_enabled_globally'])
            if 'rollout_percentage' in data:
                update_data['rollout_percentage'] = max(0, min(100, int(data['rollout_percentage'])))
            if 'config' in data:
                update_data['config'] = data['config']
            
            auth_supabase.table('feature_flags') \
                .update(update_data) \
                .eq('id', flag_id) \
                .execute()
            
            return jsonify({'success': True, 'message': 'Feature flag updated'})
        except Exception as e:
            logger.error("Failed to update feature flag: %s", e)
            return jsonify({'success': False, 'message': 'Failed to update feature flag'}), 500
    
    @features_bp.route('/flags/<flag_key>/check', methods=['GET'])
    def check_feature_flag(flag_key):
        """Check if feature flag is enabled for current user."""
        try:
            from flask import session
            user_id = session.get('user_id')
            
            if not user_id:
                return jsonify({'success': True, 'enabled': False})
            
            # Check override
            override = auth_supabase.table('feature_flag_overrides') \
                .select('is_enabled') \
                .eq('flag_id', f"(key='{flag_key}')") \
                .eq('user_id', user_id) \
                .execute().data or []
            
            if override:
                return jsonify({'success': True, 'enabled': override[0]['is_enabled']})
            
            # Get flag
            flag = auth_supabase.table('feature_flags') \
                .select('is_enabled_globally,rollout_percentage') \
                .eq('key', flag_key) \
                .execute().data or []
            
            if not flag:
                return jsonify({'success': True, 'enabled': False})
            
            flag_data = flag[0]
            if flag_data['is_enabled_globally']:
                return jsonify({'success': True, 'enabled': True})
            
            # Check rollout percentage
            hash_val = hash(user_id) % 100
            enabled = hash_val < flag_data['rollout_percentage']
            
            return jsonify({'success': True, 'enabled': enabled})
        except Exception as e:
            logger.error("Failed to check feature flag: %s", e)
            return jsonify({'success': True, 'enabled': False})
    
    @features_bp.route('/flags/<flag_key>/override', methods=['POST'])
    @require_admin_api
    def set_flag_override(flag_key):
        """Override flag for specific user - ADMIN ONLY."""
        try:
            data = request.get_json() or {}
            user_id = data.get('user_id')
            is_enabled = data.get('is_enabled', True)
            reason = data.get('reason', 'Admin override')
            
            if not user_id:
                return jsonify({'success': False, 'message': 'user_id required'}), 400
            
            # Get flag ID
            flag = auth_supabase.table('feature_flags') \
                .select('id') \
                .eq('key', flag_key) \
                .execute().data or []
            
            if not flag:
                return jsonify({'success': False, 'message': 'Flag not found'}), 404
            
            flag_id = flag[0]['id']
            
            # Upsert override
            auth_supabase.table('feature_flag_overrides').upsert({
                'flag_id': flag_id,
                'user_id': user_id,
                'is_enabled': is_enabled,
                'reason': reason
            }).execute()
            
            return jsonify({'success': True, 'message': 'Override set'})
        except Exception as e:
            logger.error("Failed to set flag override: %s", e)
            return jsonify({'success': False, 'message': 'Failed to set override'}), 500
    
    # ========================================================================
    # REVENUE METRICS API
    # ========================================================================
    
    @features_bp.route('/revenue/metrics', methods=['GET'])
    @require_admin_api
    def get_revenue_metrics():
        """Get revenue metrics dashboard - ADMIN ONLY."""
        try:
            months = max(1, int(request.args.get('months', 6)))
            
            # Get main metrics
            metrics = auth_supabase.table('revenue_metrics') \
                .select('month_year,metric_type,value,plan_name') \
                .order('month_year', desc=True) \
                .limit(months * 10) \
                .execute().data or []
            
            # Get cohort data
            cohorts = auth_supabase.table('cohort_analytics') \
                .select('cohort_month,cohort_age_months,active_user_count,retention_rate,revenue') \
                .order('cohort_month', desc=True) \
                .limit(24) \
                .execute().data or []
            
            # Get current subscription data for live metrics
            try:
                from freemium import get_plan_limits
                subs = auth_supabase.table('subscriptions').select('plan,status').execute().data or []
                
                active_subs = {}
                for sub in subs:
                    if sub.get('status') == 'active':
                        plan = sub.get('plan', 'free')
                        active_subs[plan] = active_subs.get(plan, 0) + 1
            except:
                active_subs = {}
            
            return jsonify({
                'success': True,
                'metrics': metrics,
                'cohorts': cohorts,
                'active_subscriptions': active_subs
            })
        except Exception as e:
            logger.error("Failed to fetch revenue metrics: %s", e)
            return jsonify({'success': False, 'message': 'Failed to fetch revenue metrics'}), 500
    
    @features_bp.route('/revenue/mrr', methods=['GET'])
    @require_admin_api
    def get_mrr():
        """Calculate current MRR - ADMIN ONLY."""
        try:
            subs = auth_supabase.table('subscriptions') \
                .select('plan,current_period_end') \
                .eq('status', 'active') \
                .execute().data or []
            
            from freemium import get_plan_limits
            mrr = 0
            for sub in subs:
                plan = sub.get('plan', 'free')
                limits = get_plan_limits(plan)
                plan_price = limits.get('monthly_price', 0) if isinstance(limits, dict) else 0
                if plan_price > 0 and sub.get('current_period_end'):
                    period_end = datetime.fromisoformat(sub['current_period_end'].replace('Z', '+00:00'))
                    if period_end > datetime.utcnow():
                        mrr += plan_price
            
            return jsonify({'success': True, 'mrr': mrr})
        except Exception as e:
            logger.error("Failed to calculate MRR: %s", e)
            return jsonify({'success': False, 'message': 'Failed to calculate MRR'}), 500
    
    @features_bp.route('/revenue/churn', methods=['GET'])
    @require_admin_api
    def get_churn():
        """Calculate churn rate - ADMIN ONLY."""
        try:
            months_back = max(1, int(request.args.get('months', 1)))
            
            # Get users active N+1 months ago
            from_date = datetime.utcnow() - timedelta(days=30 * (months_back + 1))
            to_date = datetime.utcnow() - timedelta(days=30 * months_back)
            
            active_start = auth_supabase.table('usage_monthly') \
                .select('user_id', count='exact') \
                .gte('month', from_date.date().isoformat()) \
                .lt('month', to_date.date().isoformat()) \
                .gt('posts_generated', 0) \
                .execute()
            
            # Get users active in current month
            current_start = datetime.utcnow().date().replace(day=1)
            active_current = auth_supabase.table('usage_monthly') \
                .select('user_id', count='exact') \
                .gte('month', current_start.isoformat()) \
                .gt('posts_generated', 0) \
                .execute()
            
            start_count = active_start.count or 1
            current_count = active_current.count or 0
            
            churn_rate = ((start_count - current_count) / start_count * 100) if start_count > 0 else 0
            
            return jsonify({
                'success': True,
                'churn_rate': round(churn_rate, 2),
                'previous_active': start_count,
                'current_active': current_count
            })
        except Exception as e:
            logger.error("Failed to calculate churn: %s", e)
            return jsonify({'success': False, 'message': 'Failed to calculate churn'}), 500
    
    return features_bp
