"""
EXACT CODE TO ADD TO app.py
Copy and paste these sections into app.py
"""

# ============================================================
# SECTION 1: Add to imports at the top of app.py (line ~20)
# ============================================================

from freemium_api import (
    freemium_bp, 
    get_user_plan, 
    get_plan_limits, 
    get_monthly_usage, 
    check_quota, 
    increment_usage
)


# ============================================================
# SECTION 2: Register blueprint after creating Flask app (line ~100)
# ============================================================

# After: app = Flask(__name__)
# Add this line:
app.register_blueprint(freemium_bp)


# ============================================================
# SECTION 3: Modify /api/generate-preview endpoint (line ~3844)
# ============================================================

# FIND THIS:
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

        # ===== ADD THIS QUOTA CHECK HERE =====
        can_generate, quota_info = check_quota(user_id, 'posts')
        if not can_generate:
            return jsonify({
                'success': False,
                'quota_exceeded': True,
                'quota_info': quota_info,
                'message': quota_info.get('message', 'Post generation limit reached')
            }), 403
        # ===== END QUOTA CHECK =====

        # ... rest of existing code continues ...
        can_generate, quota_meta = _check_generation_guardrail(user_id)
        if not can_generate:
            return jsonify({'success': False, **quota_meta}), 403
        
        # ... rest of function ...
        
        # FIND THE RETURN STATEMENT AT THE END where it returns generated post
        # Before the return statement, ADD THIS:
        
        # ===== INCREMENT USAGE =====
        increment_usage(user_id, 'posts', 1)
        logger.info(f"Post generation usage recorded for user {user_id}")
        # ===== END INCREMENT =====
        
        # Then return the post as normal:
        return jsonify({...})


# ============================================================
# SECTION 4: Modify file upload endpoint (if you have one)
# ============================================================

# In whatever endpoint handles KB file uploads, add similar quota check:

# Before upload:
can_upload, quota_info = check_quota(user_id, 'files')
if not can_upload:
    return jsonify({
        'success': False,
        'quota_exceeded': True,
        'quota_info': quota_info,
        'message': 'File upload limit reached this month'
    }), 403

# After successful upload:
increment_usage(user_id, 'files', 1)


# ============================================================
# EXAMPLE: Complete modified endpoint
# ============================================================

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
            return jsonify({'success': False, 'message': 'Authentication required'}), 401

        # ===== NEW: QUOTA CHECK =====
        can_generate, quota_info = check_quota(user_id, 'posts')
        if not can_generate:
            return jsonify({
                'success': False,
                'quota_exceeded': True,
                'quota_info': quota_info,
                'message': quota_info.get('message')
            }), 403
        # ===== END QUOTA CHECK =====

        # ... all existing code stays the same ...
        can_generate, quota_meta = _check_generation_guardrail(user_id)
        if not can_generate:
            return jsonify({'success': False, **quota_meta}), 403

        # ... generation logic ...
        
        # Build response
        response_data = {
            'success': True,
            'post': generated_post,
            'insights': insights,
            # ... other fields ...
        }
        
        # ===== NEW: INCREMENT USAGE =====
        increment_usage(user_id, 'posts', 1)
        logger.info(f"Post generation usage incremented for user {user_id}")
        # ===== END INCREMENT =====
        
        return jsonify(response_data), 200

    except Exception as e:
        logger.exception("Generation failed")
        return jsonify({'success': False, 'message': str(e)}), 500


# ============================================================
# OPTIONAL: New admin endpoint for forcing quota reset
# ============================================================

@app.route('/api/admin/reset-user-quota', methods=['POST'])
@require_auth
def admin_reset_user_quota():
    """Admin: Reset a user's monthly quota (development/testing only)"""
    try:
        from freemium_api import freemium_client
        
        data = request.get_json() or {}
        target_user_id = data.get('user_id')
        month = data.get('month') or datetime.utcnow().strftime('%Y-%m')
        
        if not target_user_id:
            return jsonify({'success': False, 'message': 'User ID required'}), 400
        
        if not freemium_client:
            return jsonify({'success': False, 'message': 'Service unavailable'}), 503
        
        # Delete the usage record for that month
        freemium_client.table('user_monthly_usage').delete().eq(
            'user_id', target_user_id
        ).eq('month_year', month).execute()
        
        return jsonify({
            'success': True,
            'message': f'Quota reset for user {target_user_id} for month {month}'
        }), 200
    except Exception as e:
        logger.error(f"Quota reset failed: {e}")
        return jsonify({'success': False, 'message': 'Operation failed'}), 500


# ============================================================
# TESTING ENDPOINTS (remove in production)
# ============================================================

@app.route('/api/debug/user-quota', methods=['GET'])
@require_auth
def debug_user_quota():
    """Debug endpoint: View your current quota (remove in production)"""
    if os.getenv('FLASK_ENV') == 'production':
        return jsonify({'error': 'Not available in production'}), 403
    
    try:
        from freemium_api import get_user_plan, get_plan_limits, get_monthly_usage, check_quota
        
        user_id = get_current_user_id()
        plan = get_user_plan(user_id)
        limits = get_plan_limits(plan)
        usage = get_monthly_usage(user_id)
        can_gen, quota = check_quota(user_id, 'posts')
        
        return jsonify({
            'user_id': user_id,
            'plan': plan,
            'limits': limits,
            'usage': usage,
            'quota_info': quota,
            'can_generate': can_gen
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================
# That's it! Upload app.py and test with:
# 1. Create free account
# 2. Generate 1 post (succeeds)
# 3. Try 2nd post (fails with quota_exceeded)
# 4. See upgrade modal
# ============================================================
