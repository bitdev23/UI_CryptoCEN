# Freemium Plan Implementation Guide

## Overview
This is a complete freemium tier system that allows users to:
- Sign up for FREE with 1 post/month quota
- Upgrade to paid plans (1-month, 3-month, 12-month)
- Admin control over quotas (easily change from 1 → 5 → 3 posts)
- Automatic upgrade prompts when quota exceeded

---

## 1. DATABASE SETUP

### Run the schema migration:
```bash
# Connect to your Supabase database and execute:
psql \
  --host="your-supabase-host" \
  --port=5432 \
  --username="postgres" \
  --password \
  --dbname="postgres" \
  < database/freemium_schema.sql
```

This creates:
- `pricing_plans` - Plan definitions and pricing
- `user_subscriptions` - User's current plan
- `user_monthly_usage` - Monthly usage tracking
- `plan_configurations` - Admin-editable quotas
- `payment_history` - Payment ledger

---

## 2. BACKEND INTEGRATION

### Add to app.py (imports section):
```python
from freemium_api import (
    freemium_bp, get_user_plan, get_plan_limits, 
    get_monthly_usage, check_quota
)

# Register blueprint
app.register_blueprint(freemium_bp)
```

### Modify POST generation endpoint (app.py ~line 3844):
```python
@app.route('/api/generate-preview', methods=['GET', 'POST'])
def generate_preview():
    """Generate a preview post"""
    from freemium_api import check_quota
    
    # ... existing code ...
    
    user_id = get_current_user_id()
    
    # CHECK QUOTA BEFORE GENERATION
    can_generate, quota_info = check_quota(user_id, 'posts')
    if not can_generate:
        return jsonify({
            'success': False,
            'quota_exceeded': True,
            'quota_info': quota_info,
            'message': f'Monthly limit reached. {quota_info.get("message", "")}'
        }), 403
    
    # ... rest of generation code ...
    
    # After successful generation, increment usage
    from freemium_api import increment_usage
    increment_usage(user_id, 'posts', 1)
    
    return jsonify({...})
```

### Similarly for file upload:
```python
# In your file upload endpoint
from freemium_api import check_quota, increment_usage

can_upload, quota_info = check_quota(user_id, 'files')
if not can_upload:
    return jsonify({
        'success': False,
        'quota_exceeded': True,
        'quota_info': quota_info,
        'message': 'File upload limit reached'
    }), 403

# ... after successful upload ...
increment_usage(user_id, 'files', 1)
```

---

## 3. FRONTEND INTEGRATION

### In dashboard.html, add the upgrade modal:
```html
<!-- At the bottom of body tag, before closing -->
{% include 'upgrade_modal.html' %}
```

### Before calling post generation API:
```javascript
// In your generate post button click handler
async function generatePost() {
    // Check quota first
    if (!await checkQuotaBeforeGenerate()) {
        return; // Modal was shown, user needs to upgrade
    }
    
    // Proceed with generation
    const response = await fetch('/api/generate-preview', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ /* form data */ })
    });
    
    const data = await response.json();
    
    if (!data.success && data.quota_exceeded) {
        showUpgradeModal();
        return;
    }
    
    // Handle successful generation
    // ...
}
```

### In auth.html signup flow:
The plan parameter is automatically captured from URL:
```javascript
// This is already added at line ~1260:
window.SELECTED_PLAN = new URLSearchParams(window.location.search).get('plan') || 'free';

// After successful signup, redirect with plan info
// Before dashboard redirect, store the plan:
localStorage.setItem('selected_plan', window.SELECTED_PLAN);
```

---

## 4. ADMIN PANEL SETUP

### API Endpoint to manage quotas:
```
GET /api/admin/plan-limits
Returns all plan configurations with current quotas

POST /api/admin/plan-limits
{
    "plan_name": "free",
    "free_posts_per_month": 3,      // Change from 1 to 3
    "free_kb_files_per_month": 2,
    "free_storage_mb": 200
}
```

### Example admin page implementation:
```html
<div id="quotaManager">
    <h3>Plan Quota Management</h3>
    <table>
        <tr>
            <th>Plan</th>
            <th>Posts/Month</th>
            <th>Files</th>
            <th>Storage (MB)</th>
            <th>Action</th>
        </tr>
    </table>
    
    <form onsubmit="updateQuota(event)">
        <select id="planName">
            <option>free</option>
            <option>1-month</option>
            <option>3-month</option>
            <option>12-month</option>
        </select>
        
        <input type="number" id="posts" placeholder="Posts per month">
        <input type="number" id="files" placeholder="Files">
        <input type="number" id="storage" placeholder="Storage MB">
        
        <button type="submit">Update Quota</button>
    </form>
</div>

<script>
async function updateQuota(e) {
    e.preventDefault();
    
    const response = await fetch('/api/admin/plan-limits', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            plan_name: document.getElementById('planName').value,
            free_posts_per_month: parseInt(document.getElementById('posts').value),
            free_kb_files_per_month: parseInt(document.getElementById('files').value),
            free_storage_mb: parseInt(document.getElementById('storage').value)
        })
    });
    
    const data = await response.json();
    if (data.success) {
        alert('Quota updated successfully!');
        // Refresh page or update UI
    }
}
</script>
```

---

## 5. PRICING PAGE INTEGRATION

### When user clicks upgrade on pricing page:
```html
<!-- On your pricing page for each plan -->
<a href="/login?plan=1-month" class="btn btn-primary">
    Upgrade Now
</a>

<!-- For 3-month plan -->
<a href="/login?plan=3-month" class="btn btn-primary">
    Choose Plan
</a>

<!-- For annual plan -->
<a href="/login?plan=12-month" class="btn btn-primary">
    Get Annual
</a>
```

The plan parameter is automatically stored during signup.

---

## 6. PAYMENT INTEGRATION (Razorpay)

### Create checkout endpoint:
```python
@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    """Initiate payment"""
    plan = request.args.get('plan') or request.json.get('plan', 'free')
    
    if plan == 'free':
        return redirect('/')
    
    # Get plan pricing
    pricing = {
        '1-month': 99,
        '3-month': 249,
        '12-month': 899
    }
    
    amount = pricing.get(plan, 0)
    if amount <= 0:
        return jsonify({'error': 'Invalid plan'}), 400
    
    user_id = get_current_user_id()
    
    # Create Razorpay order
    # ... (use existing _create_razorpay_order function)
    
    return jsonify({
        'success': True,
        'order_id': order['id'],
        'amount': amount
    })
```

---

## 7. QUOTA DISPLAY IN DASHBOARD

### Show user's remaining quota:
```javascript
async function updateQuotaDisplay() {
    const response = await fetch('/api/user/quota-status');
    const data = await response.json();
    
    if (data.success) {
        const posts = data.quotas.posts;
        document.getElementById('quotaDisplay').innerHTML = `
            <div class="quota-card">
                <h4>${data.plan.toUpperCase()} Plan</h4>
                <div class="quota-bar">
                    <div class="quota-used" style="width: ${(posts.used / posts.limit) * 100}%"></div>
                </div>
                <p>${posts.used}/${posts.limit} posts used this month</p>
                ${posts.remaining === 0 ? `
                    <button onclick="showUpgradeModal()">Upgrade to Generate More</button>
                ` : `
                    <p>${posts.remaining} posts remaining</p>
                `}
            </div>
        `;
    }
}

// Call on dashboard load
document.addEventListener('DOMContentLoaded', updateQuotaDisplay);
```

---

## 8. USER FLOW SUMMARY

### Free Tier User:
1. ✅ Signs up with email (no credit card)
2. ✅ Automatically gets "free" plan
3. ✅ Can generate 1 post/month (configurable)
4. ✅ Can upload 1 KB file (configurable)
5. ❌ On 2nd post attempt → sees upgrade modal
6. ✅ Can click upgrade → redirected to payment

### Paid Tier User:
1. ✅ Sees pricing page
2. ✅ Clicks plan button → goes to `/login?plan=1-month`
3. ✅ Signs up
4. ✅ Completes payment
5. ✅ Subscription activated
6. ✅ Quota limits updated (50, 150, or 500 posts)

---

## 9. ADMIN CHANGES TO QUOTAS

### Change Free Plan from 1 → 5 posts:
```bash
POST /api/admin/plan-limits
{
    "plan_name": "free",
    "free_posts_per_month": 5,
    "free_kb_files_per_month": 1,
    "free_storage_mb": 100
}
```

✅ **Instantly effective** for all existing free users!

### Change Free Plan from 5 → 1 post:
```bash
POST /api/admin/plan-limits
{
    "plan_name": "free",
    "free_posts_per_month": 1,
    ...
}
```

✅ **Next month**, all users reset to new quota

---

## 10. TESTING CHECKLIST

- [ ] Free user: Sign up → see 1 post quota
- [ ] Free user: Generate 1 post → succeeds
- [ ] Free user: Try 2nd post → sees upgrade modal
- [ ] Paid user: Upgrade via modal → payment flow
- [ ] Admin: Update free quota 1→3 → new users get 3 posts
- [ ] Admin: View all plan quotas
- [ ] Dashboard: Shows remaining quota
- [ ] Quota resets: Next month = fresh quota
- [ ] Payment: Razorpay integration (if configured)

---

## 11. ENVIRONMENT VARIABLES (if needed)

```bash
# Added to .env if using separate payment processor
RAZORPAY_KEY_ID=your_key_here
RAZORPAY_KEY_SECRET=your_secret_here
RAZORPAY_WEBHOOK_SECRET=your_webhook_secret
```

---

## 12. DEFAULT PLAN LIMITS

These are set in freemium_schema.sql and can be updated via `/api/admin/plan-limits`:

| Plan | Posts/Month | KB Files | Storage |
|------|-------------|----------|---------|
| Free | **1** | 1 | 100 MB |
| 1-Month | 50 | 10 | 1 GB |
| 3-Month | 150 | 30 | 3 GB |
| 12-Month (Annual) | 500 | 100 | 10 GB |

---

## NEXT STEPS

1. ✅ Run the database schema migration
2. ✅ Add freemium_api.py imports to app.py
3. ✅ Modify /api/generate-preview endpoint with quota checks
4. ✅ Add upgrade_modal.html to dashboard.html
5. ✅ Test signup flow with plan parameter
6. ✅ Create admin panel for quota management
7. ✅ Integrate Razorpay payment (if not already done)
8. ✅ Deploy to production

---

## SUPPORT

For questions or issues: Check function signatures in freemium_api.py
