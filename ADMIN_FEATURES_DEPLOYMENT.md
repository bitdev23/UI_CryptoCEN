# Admin Features Deployment Guide

## Overview
This guide walks through deploying 4 critical production-grade admin features:
1. **In-App Notifications** - User communication system
2. **Error Monitoring** - Real-time error tracking with stack traces
3. **Feature Flags** - Gradual feature rollouts with user overrides
4. **Revenue Dashboard** - MRR/ARR/churn metrics with cohort analysis

## Architecture

```
Frontend (admin_dashboard.html)
    ↓
Admin Routes (routes/admin_features.py)
    ↓
Supabase Database (admin_features_migration.sql)
    ↓
Redis Cache (optional: error alert batching)
```

## Deployment Steps

### Step 1: Apply Database Migration

**Option A: Via Supabase Dashboard (Recommended for first-time)**

1. Log into Supabase: https://app.supabase.com
2. Select your project (UI_CryptoCEN)
3. Go to **SQL Editor** > **New Query**
4. Copy entire contents from `database/admin_features_migration.sql`
5. Execute the query
6. Verify all tables created: Check **Database** > **Tables**

**Option B: Via Supabase CLI (Advanced)**

```bash
supabase db push --project-id YOUR_PROJECT_ID < database/admin_features_migration.sql
```

**Option C: Via Python Script**

```bash
python -c "
import sys
sys.path.insert(0, '.')
from app import supabase

with open('database/admin_features_migration.sql', 'r') as f:
    sql = f.read()
    
# Split by semicolon and execute each statement
for stmt in sql.split(';'):
    stmt = stmt.strip()
    if stmt and not stmt.startswith('--'):
        try:
            supabase.query(stmt)
            print(f'✓ Executed: {stmt[:50]}...')
        except Exception as e:
            print(f'✗ Error: {e}')
            print(f'  Statement: {stmt[:100]}')
"
```

### Step 2: Verify Routes Integration

1. Confirm `routes/admin_features.py` exists
2. Check `app.py` contains:
   ```python
   from routes.admin_features import create_admin_features_blueprint as _create_features_bp
   _features_bp = _create_features_bp(auth_supabase=supabase, limiter=limiter)
   app.register_blueprint(_features_bp)
   ```
3. Restart Flask app:
   ```bash
   pkill -f "python.*app.py"
   python app.py
   ```

### Step 3: Verify Frontend Integration

1. Check `templates/admin_dashboard.html` has:
   - Feature tab navigation (🔔 Notifications, ⚠️ Errors, 📊 Revenue, 🚩 Flags)
   - Notification send modal
   - Error detail modal
   - Feature flag editor modal
   - JavaScript functions: `switchFeatureTab()`, `sendNotification()`, `loadErrorLogs()`, etc.

### Step 4: Test Each Feature

#### Test Notifications
```bash
curl -X POST http://localhost:5000/api/admin/features/notifications/send \
  -H "Content-Type: application/json" \
  -H "Cookie: admin_session=your-admin-token" \
  -d '{
    "user_ids": ["user-id-1"],
    "type": "system",
    "title": "Test Notification",
    "message": "Testing notifications system",
    "priority": "normal"
  }'
```

#### Test Error Logging
```bash
curl -X POST http://localhost:5000/api/admin/features/errors/log \
  -H "Content-Type: application/json" \
  -d '{
    "error_type": "TypeError",
    "error_message": "Cannot read property x of undefined",
    "stack_trace": "at Function...",
    "endpoint": "/api/test",
    "status_code": 500
  }'
```

#### Test Feature Flags
```bash
curl http://localhost:5000/api/admin/features/flags/get-notifications \
  -H "Cookie: session=your-user-token"
```

#### Test Revenue Metrics
```bash
curl http://localhost:5000/api/admin/features/revenue/metrics \
  -H "Cookie: admin_session=your-admin-token"
```

## API Endpoints Reference

### Notifications
- `GET /api/admin/features/notifications` - List user notifications (USER)
- `POST /api/admin/features/notifications/<id>` - Mark as read/archived (USER)
- `POST /api/admin/features/notifications/send` - Send notification (ADMIN)

### Error Monitoring
- `GET /api/admin/features/errors` - Get error logs (ADMIN)
- `GET /api/admin/features/errors/<id>` - Get error detail (ADMIN)
- `POST /api/admin/features/errors/<id>/resolve` - Mark as resolved (ADMIN)
- `POST /api/admin/features/errors/log` - Log error from client/server (PUBLIC, RATE LIMITED)

### Feature Flags
- `GET /api/admin/features/flags` - List all flags (ADMIN)
- `POST /api/admin/features/flags/<id>` - Update flag settings (ADMIN)
- `POST /api/admin/features/flags/<key>/override` - Set user override (ADMIN)
- `GET /api/admin/features/flags/<key>/check` - Check if enabled for user (USER)

### Revenue
- `GET /api/admin/features/revenue/metrics` - Get aggregated metrics (ADMIN)
- `GET /api/admin/features/revenue/mrr` - Calculate current MRR (ADMIN)
- `GET /api/admin/features/revenue/churn` - Calculate churn rate (ADMIN)

## Database Tables Created

1. **notifications** - User notifications with read/archive status
2. **notification_templates** - Notification templates with {{var}} interpolation
3. **error_logs** - Error entries with stack traces and severity
4. **error_alert_rules** - Rules for auto-alerting on error patterns
5. **feature_flags** - Global feature flag settings
6. **feature_flag_overrides** - Per-user flag overrides
7. **feature_flag_rollout_hash** - Stable rollout tracking using user_id hash
8. **revenue_metrics** - Monthly MRR/ARR/churn tracking by plan
9. **cohort_analytics** - Cohort retention and revenue data

### Key Indexes for Performance
- `notifications(user_id, created_at, is_read)` - Fast notification queries
- `error_logs(error_type, created_at, severity)` - Error dashboard queries
- `feature_flags(key)` - Flag lookup
- `revenue_metrics(month_year, plan_name)` - Monthly aggregates

## Usage Guide for Admins

### Send Notification to Users
1. Go to Admin Dashboard > 🔔 Notifications tab
2. Click "Send Notification"
3. Select user scope (All, Active, Verified, or Custom IDs)
4. Enter title, message, and priority
5. Click "Send"

### Monitor Errors
1. Go to Admin Dashboard > ⚠️ Error Monitoring tab
2. Filter by severity and time window
3. Click "View" on any error to see full stack trace
4. Mark as resolved when fixed

### Manage Feature Flags
1. Go to Admin Dashboard > 🚩 Feature Flags tab
2. Click "Edit" on any flag
3. Toggle global enable/disable
4. Adjust rollout percentage for gradual rollouts
5. Save changes (applies to next request)

### View Revenue Metrics
1. Go to Admin Dashboard > 📊 Revenue Dashboard tab
2. See MRR, churn rate, and active subscription counts
3. Breakdown by plan type shows distribution

## Monitoring & Troubleshooting

### Check if app.py error logging is working
```bash
# Send a test error
curl -X POST http://localhost:5000/api/admin/features/errors/log \
  -H "Content-Type: application/json" \
  -d '{"error_type": "TEST", "error_message": "Test error"}'

# Check if it appears in database
sqlite3 or psql "SELECT * FROM error_logs ORDER BY created_at DESC LIMIT 1;"
```

### Verify permissions for admin endpoints
- All ADMIN endpoints require `session.get('admin_session')`
- Check that admin login is working: `GET /admin/login`
- Verify session is set after login

### Performance tuning
- Error logs grow quickly - consider archival/cleanup script
- For high-volume notifications, consider batch inserts
- Revenue calculations cache results in Redis (optional)

## Next Steps (Optional Enhancements)

1. **Error Alert Rules** - Auto-trigger escalations on error patterns
2. **Notification Templates** - Pre-built templates for common messages
3. **WebSocket Updates** - Real-time error/notification updates
4. **Slack Integration** - Send critical errors to Slack
5. **Retention Policies** - Archive old logs/notifications automatically
6. **Advanced Analytics** - Cohort-based churn predictions

## Support

For issues:
1. Check `VSCODE_TARGET_SESSION_LOG` in DEBUG_LOGS
2. Verify database queries with `supabase.table(...).select().execute()`
3. Test endpoints with curl or Postman
4. Check admin session validity with `session.get('admin_session')`
