-- ============================================================================
-- ADMIN PRODUCTION FEATURES SCHEMA
-- Notifications, Error Monitoring, Feature Flags, Revenue Tracking
-- ============================================================================

-- ============================================================================
-- 1. IN-APP NOTIFICATIONS
-- ============================================================================
CREATE TABLE IF NOT EXISTS notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    type VARCHAR(50) NOT NULL, -- 'billing', 'system', 'alert', 'maintenance', 'feature', 'security'
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    data JSONB, -- Extra metadata (links, action_url, etc.)
    is_read BOOLEAN DEFAULT FALSE,
    is_archived BOOLEAN DEFAULT FALSE,
    priority VARCHAR(20) DEFAULT 'normal', -- 'low', 'normal', 'high', 'critical'
    action_url VARCHAR(500), -- Link for CTA
    action_label VARCHAR(100), -- Button text
    dismiss_at TIMESTAMPTZ, -- Auto-dismiss time
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS notification_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) UNIQUE NOT NULL,
    title_template TEXT NOT NULL,
    message_template TEXT NOT NULL, -- Supports {{var}} placeholders
    type VARCHAR(50) NOT NULL,
    priority VARCHAR(20) DEFAULT 'normal',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- 2. ERROR MONITORING & LOGGING
-- ============================================================================
CREATE TABLE IF NOT EXISTS error_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    error_type VARCHAR(100) NOT NULL, -- Exception class name
    error_message TEXT NOT NULL,
    stack_trace TEXT, -- Full stack trace
    endpoint VARCHAR(500), -- API endpoint or page
    request_method VARCHAR(10), -- GET, POST, PUT, DELETE
    status_code INT, -- HTTP status
    context JSONB, -- Request params, headers (sanitized)
    severity VARCHAR(20) DEFAULT 'error', -- 'warning', 'error', 'critical'
    is_resolved BOOLEAN DEFAULT FALSE,
    notes TEXT, -- Admin notes
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS error_alert_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) UNIQUE NOT NULL,
    error_pattern VARCHAR(500), -- Regex or exact match
    severity_threshold VARCHAR(20), -- Alert if >= this severity
    occurrence_threshold INT DEFAULT 5, -- Alert after N errors
    time_window_minutes INT DEFAULT 60, -- In this time window
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- 3. FEATURE FLAGS / TOGGLES
-- ============================================================================
CREATE TABLE IF NOT EXISTS feature_flags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key VARCHAR(100) UNIQUE NOT NULL, -- 'new_dashboard', 'ai_v2', etc.
    name VARCHAR(255),
    description TEXT,
    is_enabled_globally BOOLEAN DEFAULT FALSE,
    rollout_percentage INT DEFAULT 0, -- 0-100 for gradual rollout
    rollout_type VARCHAR(50) DEFAULT 'percentage', -- 'percentage', 'list', 'rule'
    config JSONB, -- Extra config (variants, rules, etc.)
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS feature_flag_overrides (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    flag_id UUID REFERENCES feature_flags(id) ON DELETE CASCADE NOT NULL,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    is_enabled BOOLEAN NOT NULL, -- Explicit override
    reason VARCHAR(255), -- Why this override
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(flag_id, user_id)
);

-- Hash-based rollout tracking (for stable/consistent rollout)
CREATE TABLE IF NOT EXISTS feature_flag_rollout_hash (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    flag_id UUID REFERENCES feature_flags(id) ON DELETE CASCADE NOT NULL,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    hash_value INT, -- Hash of user_id used for rollout decision
    is_in_rollout BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(flag_id, user_id)
);

-- ============================================================================
-- 4. REVENUE METRICS & ANALYTICS
-- ============================================================================
CREATE TABLE IF NOT EXISTS revenue_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    month_year DATE NOT NULL, -- First day of month (YYYY-MM-01)
    metric_type VARCHAR(50) NOT NULL, -- 'mrr', 'arr', 'active_users', 'churn', 'arpu'
    plan_name VARCHAR(50), -- NULL for aggregate
    value NUMERIC(15, 2) NOT NULL,
    detail JSONB, -- Breakdown by region, source, etc.
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(month_year, metric_type, plan_name)
);

CREATE TABLE IF NOT EXISTS cohort_analytics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cohort_month DATE NOT NULL, -- First day of cohort month
    cohort_age_months INT NOT NULL, -- How many months since cohort start
    user_count INT DEFAULT 0,
    active_user_count INT DEFAULT 0,
    revenue NUMERIC(15, 2) DEFAULT 0,
    retention_rate NUMERIC(5, 2) DEFAULT 0, -- Percentage
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- INDEXES FOR PERFORMANCE
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_notifications_user_id ON notifications(user_id);
CREATE INDEX IF NOT EXISTS idx_notifications_created_at ON notifications(created_at);
CREATE INDEX IF NOT EXISTS idx_notifications_is_read ON notifications(is_read);
CREATE INDEX IF NOT EXISTS idx_notifications_user_unread ON notifications(user_id, is_read) WHERE is_read = FALSE;

CREATE INDEX IF NOT EXISTS idx_error_logs_user_id ON error_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_error_logs_error_type ON error_logs(error_type);
CREATE INDEX IF NOT EXISTS idx_error_logs_created_at ON error_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_error_logs_is_resolved ON error_logs(is_resolved);
CREATE INDEX IF NOT EXISTS idx_error_logs_severity ON error_logs(severity);
CREATE INDEX IF NOT EXISTS idx_error_logs_recent ON error_logs(created_at DESC) WHERE is_resolved = FALSE;

CREATE INDEX IF NOT EXISTS idx_feature_flags_key ON feature_flags(key);

CREATE INDEX IF NOT EXISTS idx_revenue_metrics_month_year ON revenue_metrics(month_year);
CREATE INDEX IF NOT EXISTS idx_revenue_metrics_metric_type ON revenue_metrics(metric_type);

CREATE INDEX IF NOT EXISTS idx_cohort_analytics_cohort_month ON cohort_analytics(cohort_month);
CREATE INDEX IF NOT EXISTS idx_cohort_analytics_cohort_age ON cohort_analytics(cohort_age_months);

-- ============================================================================
-- FUNCTIONS FOR COMMON OPERATIONS
-- ============================================================================

-- Function to calculate MRR for current month
CREATE OR REPLACE FUNCTION calculate_current_mrr()
RETURNS NUMERIC AS $$
DECLARE
    current_mrr NUMERIC;
BEGIN
    SELECT COALESCE(SUM(CAST(plan_limits->>'monthly_price_inr' AS NUMERIC)), 0)
    INTO current_mrr
    FROM subscriptions
    WHERE status = 'active' 
        AND current_period_end > NOW();
    
    RETURN current_mrr;
END;
$$ LANGUAGE plpgsql;

-- Function to mark notifications as read
CREATE OR REPLACE FUNCTION mark_notifications_read(p_user_id UUID, p_notification_ids UUID[])
RETURNS INT AS $$
DECLARE
    affected_rows INT;
BEGIN
    UPDATE notifications
    SET is_read = TRUE, updated_at = NOW()
    WHERE user_id = p_user_id AND id = ANY(p_notification_ids);
    
    GET DIAGNOSTICS affected_rows = ROW_COUNT;
    RETURN affected_rows;
END;
$$ LANGUAGE plpgsql;

-- Function to check feature flag for user
CREATE OR REPLACE FUNCTION check_feature_flag(p_flag_key VARCHAR, p_user_id UUID)
RETURNS BOOLEAN AS $$
DECLARE
    flag_enabled BOOLEAN;
    override_exists BOOLEAN;
    override_value BOOLEAN;
    rollout_pct INT;
    hash_val INT;
BEGIN
    -- Check for explicit override first
    SELECT is_enabled INTO override_value
    FROM feature_flag_overrides
    WHERE flag_id = (SELECT id FROM feature_flags WHERE key = p_flag_key)
        AND user_id = p_user_id
    LIMIT 1;
    
    IF FOUND THEN
        RETURN override_value;
    END IF;
    
    -- Get flag config
    SELECT is_enabled_globally, rollout_percentage
    INTO flag_enabled, rollout_pct
    FROM feature_flags
    WHERE key = p_flag_key;
    
    IF NOT FOUND THEN
        RETURN FALSE;
    END IF;
    
    -- If globally enabled, return true
    IF flag_enabled THEN
        RETURN TRUE;
    END IF;
    
    -- Check rollout percentage using hash
    hash_val := (hashtext(p_user_id::TEXT) % 100);
    RETURN hash_val < rollout_pct;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- SAMPLE DATA
-- ============================================================================

-- Insert default templates
INSERT INTO notification_templates (name, title_template, message_template, type, priority) VALUES
    ('payment_success', 'Payment Successful', 'Your payment of {{amount}} INR for {{plan}} plan has been processed.', 'billing', 'normal'),
    ('payment_failed', 'Payment Failed', 'Your payment of {{amount}} INR failed. Reason: {{reason}}. {{action_url}}', 'billing', 'high'),
    ('plan_upgraded', 'Plan Upgraded', 'Congratulations! You''ve upgraded to {{new_plan}}.', 'feature', 'normal'),
    ('quota_warning', 'Approaching Quota Limit', 'You''ve used {{percent}}% of your {{quota_name}} limit this month.', 'alert', 'high'),
    ('maintenance_scheduled', 'Scheduled Maintenance', 'We''ll have maintenance on {{date}} at {{time}}. Expected downtime: {{duration}} minutes.', 'maintenance', 'normal'),
    ('new_feature', 'New Feature Available', 'Check out {{feature_name}}: {{description}}', 'feature', 'normal'),
    ('suspicious_activity', 'Suspicious Activity Detected', 'We detected unusual activity on your account. {{action_url}}', 'security', 'critical')
ON CONFLICT (name) DO NOTHING;

-- Insert default feature flags
INSERT INTO feature_flags (key, name, description, is_enabled_globally, rollout_percentage) VALUES
    ('new_admin_dashboard', 'New Admin Dashboard UI', 'Redesigned admin dashboard with better UX', FALSE, 0),
    ('ai_v2_posts', 'AI v2 Post Generation', 'Improved post generation with new AI model', FALSE, 10),
    ('advanced_scheduling', 'Advanced Post Scheduling', 'Multi-day scheduling with auto-optimization', FALSE, 25),
    ('user_analytics', 'User Analytics Tab', 'Per-user analytics and insights', FALSE, 50),
    ('api_webhooks', 'Custom Webhooks', 'Send webhooks for user actions', FALSE, 0)
ON CONFLICT (key) DO NOTHING;
