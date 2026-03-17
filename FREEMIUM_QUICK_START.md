# Freemium System - Quick Start Guide

## What Was Built

A complete **freemium tier system** with:
- ✅ Free plan with 1 post/month quota (configurable)
- ✅ 3 paid plans (1-month, 3-month, 12-month)
- ✅ Admin panel to change quotas in real-time
- ✅ Automatic upgrade prompts when quota exceeded
- ✅ Plan parameter support (`?plan=1-month` in signup URLs)
- ✅ Monthly usage tracking
- ✅ Full payment integration support

---

## 3 Files to Implement

### 1. **freemium_api.py** - Backend Quota Management
Location: `/Users/macbookair/Documents/UI_CryptoCEN/freemium_api.py`

Key functions:
- `check_quota(user_id, 'posts')` - Check if user can generate
- `get_user_plan(user_id)` - Get user's current plan
- `increment_usage(user_id, 'posts', 1)` - Log post generation
- `get_plan_limits(plan_name)` - Get quota limits

**6 API endpoints provided:**
```
GET /api/user/quota-status          → User's usage & limits
GET /api/upgrade-info               → Available plans for upgrade
GET /api/admin/plan-limits          → View all quotas
POST /api/admin/plan-limits         → Update quotas
GET /api/quota-exceeded-modal       → Modal content when limit hit
```

---

### 2. **database/freemium_schema.sql** - Database Tables
Location: `/Users/macbookair/Documents/UI_CryptoCEN/database/freemium_schema.sql`

Creates 5 tables:
- `pricing_plans` - Plan definitions (free, 1-month, 3-month, 12-month)
- `user_subscriptions` - User's current plan
- `user_monthly_usage` - Posts/files generated per month
- `plan_configurations` - Admin-editable quotas
- `payment_history` - Payment ledger

---

### 3. **templates/upgrade_modal.html** - Frontend Modal
Location: `/Users/macbookair/Documents/UI_CryptoCEN/templates/upgrade_modal.html`

Beautiful modal that shows:
- ✅ Current plan & remaining quota
- ✅ Available upgrade plans with pricing
- ✅ "Continue Free" or "Upgrade" buttons

---

## Implementation Steps (30 min)

### Step 1: Database Setup (5 min)
```bash
# Run the SQL migration in your Supabase console:
# Copy content from database/freemium_schema.sql
# Paste into SQL Editor in Supabase Dashboard
# Execute
```

### Step 2: Update app.py (10 min)
Add to top of app.py:
```python
from freemium_api import (
    freemium_bp, get_user_plan, get_plan_limits, 
    get_monthly_usage, check_quota, increment_usage
)

app.register_blueprint(freemium_bp)
```

Find the `/api/generate-preview` endpoint (~line 3822), add:
```python
# After user_id validation
from freemium_api import check_quota

can_generate, quota_info = check_quota(user_id, 'posts')
if not can_generate:
    return jsonify({
        'success': False,
        'quota_exceeded': True,
        'quota_info': quota_info,
        'message': quota_info.get('message')
    }), 403

# ... rest of generation code ...

# After successful generation, before return:
increment_usage(user_id, 'posts', 1)
```

### Step 3: Update Dashboard HTML (5 min)
In your main dashboard template, add before closing `</body>`:
```html
{% include 'upgrade_modal.html' %}
```

Then in the JavaScript for post generation, add:
```javascript
// Before calling /api/generate-preview
if (!await checkQuotaBeforeGenerate()) {
    return;
}
```

### Step 4: Update auth.html (Already Done! ✅)
The plan parameter capture is already added:
```javascript
window.SELECTED_PLAN = new URLSearchParams(window.location.search).get('plan') || 'free';
```

### Step 5: Test (10 min)
1. Sign up as free user
2. Try to generate 2 posts → see upgrade modal on 2nd attempt ✅
3. Click upgrade → shows pricing ✅
4. Test admin endpoint → update free quota from 1 to 3 ✅
5. New free user gets 3 posts ✅

---

## Usage Examples

### For Users:
```
User clicks "Upgrade" on pricing page
  ↓
Lands on: /login?plan=1-month
  ↓
Sign up form shows "Upgrading to 1-Month Plan"
  ↓
After email verification, redirected to payment
  ↓
Payment completes → subscription activated
  ↓
Dashboard now shows: "1-Month Plan: 50 posts/month"
```

### For Admins:
```
Go to Admin Panel → Quota Management
  ↓
Find "Free" plan
  ↓
Change "Posts per month": 1 → 5
  ↓
Click "Update"
  ↓
✅ All new signups get 5 free posts (effective immediately)
✅ Existing users reset to 5 next month
```

### For Developers:
```python
# Check if user can generate
can_generate, info = check_quota(user_id, 'posts')
if not can_generate:
    # Show upgrade modal or return error

# After generation
increment_usage(user_id, 'posts', 1)

# Get user's plan
plan = get_user_plan(user_id)  # Returns: 'free', '1-month', etc

# Get quota limits
limits = get_plan_limits('free')  # Returns: {'posts_per_month': 1, ...}
```

---

## File Changes Summary

| File | Changes | Status |
|------|---------|--------|
| app.py | Register blueprint, add quota checks to /api/generate-preview | 🟡 TODO |
| dashboard.html | Include upgrade_modal.html | 🟡 TODO |
| auth.html | Plan parameter capture | ✅ DONE |
| database/freemium_schema.sql | New tables created | ✅ CREATED |
| freemium_api.py | All APIs implemented | ✅ CREATED |
| templates/upgrade_modal.html | Modal UI + JS | ✅ CREATED |

---

## Default Quotas (Easily Changeable)

### Free Plan: 
- Posts: **1/month** (change to 3, 5, or any number)
- KB Files: 1
- Storage: 100 MB

### 1-Month Plan (₹99):
- Posts: 50/month
- KB Files: 10
- Storage: 1 GB

### 3-Month Plan (₹249):
- Posts: 150/month
- KB Files: 30
- Storage: 3 GB

### 12-Month Plan (₹899):
- Posts: 500/month
- KB Files: 100
- Storage: 10 GB

**Change anytime via:** `POST /api/admin/plan-limits`

---

## Key Features Included

### ✅ Automatic Quota Reset
- Resets monthly on the 1st
- Uses `month_year` tracking (YYYY-MM format)

### ✅ Real-time Admin Control
- No code changes needed
- Update quotas in seconds
- Effective immediately for new users

### ✅ Smooth UX
- Beautiful upgrade modal with plan comparison
- Shows current usage and remaining quota
- "Continue Free" option (no forced upgrades)

### ✅ Payment Ready
- Integrates with existing Razorpay setup
- Payment history tracking
- Subscription status management

### ✅ Extensible
- Easy to add storage tracking
- API call tracking supported
- Custom metrics can be added

---

## Error Handling

When user exceeds quota:

**API Response:**
```json
{
  "success": false,
  "quota_exceeded": true,
  "quota_info": {
    "plan": "free",
    "limit": 1,
    "used": 1,
    "remaining": 0,
    "message": "Monthly post generation limit reached (1/1)"
  }
}
```

**Frontend:**
- Modal appears automatically
- Shows plan options
- User can upgrade or continue free plan

---

## Database Queries (if you need to check manually)

```sql
-- Check user's current plan
SELECT plan_name FROM user_subscriptions WHERE user_id = 'user_id_here';

-- Check current month's usage
SELECT * FROM user_monthly_usage 
WHERE user_id = 'user_id_here' AND month_year = '2026-03';

-- Get all plan quotas
SELECT * FROM plan_configurations;

-- Update free plan quota
UPDATE plan_configurations 
SET free_posts_per_month = 5 
WHERE plan_name = 'free';
```

---

## Deploy Checklist

- [ ] Run freemium_schema.sql in Supabase
- [ ] Add freemium_api blueprint import to app.py
- [ ] Add quota checks to /api/generate-preview
- [ ] Call increment_usage after post generation
- [ ] Include upgrade_modal.html in dashboard
- [ ] Add checkQuotaBeforeGenerate() call
- [ ] Test free user flow (sign up → 2 posts → modal)
- [ ] Test admin quota update
- [ ] Test paid plan upgrade
- [ ] Deploy to production
- [ ] Monitor quota metrics in Supabase

---

## Support Scripts

View user quotas:
```sql
SELECT u.email, pc.free_posts_per_month, umu.posts_generated, umu.month_year
FROM auth.users u
LEFT JOIN user_subscriptions us ON u.id = us.user_id
LEFT JOIN plan_configurations pc ON us.plan_name = pc.plan_name
LEFT JOIN user_monthly_usage umu ON u.id = umu.user_id
LIMIT 10;
```

Reset a user's monthly quota (if needed):
```sql
DELETE FROM user_monthly_usage 
WHERE user_id = 'user_id_here' AND month_year = '2026-03';
```

---

**Ready to implement? Start with Step 1 (Database Setup) above!**
