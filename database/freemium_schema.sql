-- ============================================================
-- FREEMIUM & PLAN MANAGEMENT SCHEMA
-- ============================================================

-- Pricing plans configuration (admin-controlled)
CREATE TABLE IF NOT EXISTS pricing_plans (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    plan_name TEXT UNIQUE NOT NULL,
    display_name TEXT NOT NULL,
    description TEXT,
    monthly_price_inr INTEGER DEFAULT 0,
    yearly_price_inr INTEGER DEFAULT 0,
    features JSONB DEFAULT '{}',
    limits JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- User subscription tracking
CREATE TABLE IF NOT EXISTS user_subscriptions (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    plan_name TEXT NOT NULL,
    status TEXT DEFAULT 'active', -- active, canceled, expired
    current_period_start TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    current_period_end TIMESTAMP WITH TIME ZONE,
    auto_renew BOOLEAN DEFAULT true,
    payment_method TEXT, -- razorpay, stripe, etc
    provider_order_id TEXT,
    provider_payment_id TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id)
);

-- Monthly usage tracking
CREATE TABLE IF NOT EXISTS user_monthly_usage (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    month_year TEXT NOT NULL, -- YYYY-MM format
    posts_generated INTEGER DEFAULT 0,
    files_uploaded INTEGER DEFAULT 0,
    api_calls INTEGER DEFAULT 0,
    storage_mb_used FLOAT DEFAULT 0,
    last_reset TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, month_year)
);

-- Admin configuration for plan limits
CREATE TABLE IF NOT EXISTS plan_configurations (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    plan_name TEXT UNIQUE NOT NULL,
    free_posts_per_month INTEGER DEFAULT 1,
    free_kb_files_per_month INTEGER DEFAULT 1,
    free_storage_mb INTEGER DEFAULT 100,
    is_editable_by_admin BOOLEAN DEFAULT true,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_by UUID REFERENCES auth.users(id)
);

-- Payment history & invoices
CREATE TABLE IF NOT EXISTS payment_history (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    plan_name TEXT NOT NULL,
    amount_inr INTEGER NOT NULL,
    status TEXT DEFAULT 'pending', -- pending, completed, failed, refunded
    payment_method TEXT, -- razorpay, stripe
    provider_order_id TEXT,
    provider_payment_id TEXT,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_user_subscriptions_user_id ON user_subscriptions(user_id);
CREATE INDEX IF NOT EXISTS idx_user_subscriptions_plan ON user_subscriptions(plan_name);
CREATE INDEX IF NOT EXISTS idx_user_monthly_usage_user_id ON user_monthly_usage(user_id);
CREATE INDEX IF NOT EXISTS idx_user_monthly_usage_month ON user_monthly_usage(month_year);
CREATE INDEX IF NOT EXISTS idx_payment_history_user_id ON payment_history(user_id);
CREATE INDEX IF NOT EXISTS idx_payment_history_status ON payment_history(status);

-- Insert default plans
INSERT INTO pricing_plans (plan_name, display_name, description, monthly_price_inr, yearly_price_inr, limits) VALUES
    ('free', 'Free', 'Perfect to get started', 0, 0, '{"posts_per_month": 1, "kb_files": 1, "storage_mb": 100}'),
    ('1-month', '1 Month', 'Monthly subscription', 99, NULL, '{"posts_per_month": 50, "kb_files": 10, "storage_mb": 1000}'),
    ('3-month', '3 Months', '3 months subscription', 249, NULL, '{"posts_per_month": 150, "kb_files": 30, "storage_mb": 3000}'),
    ('12-month', '12 Months', 'Annual plan - Save 20%', 899, 999, '{"posts_per_month": 500, "kb_files": 100, "storage_mb": 10000}')
ON CONFLICT (plan_name) DO UPDATE SET
    monthly_price_inr = EXCLUDED.monthly_price_inr,
    limits = EXCLUDED.limits;

-- Insert default plan configurations
INSERT INTO plan_configurations (plan_name, free_posts_per_month, free_kb_files_per_month, free_storage_mb) VALUES
    ('free', 1, 1, 100),
    ('1-month', 50, 10, 1000),
    ('3-month', 150, 30, 3000),
    ('12-month', 500, 100, 10000)
ON CONFLICT (plan_name) DO UPDATE SET
    free_posts_per_month = EXCLUDED.free_posts_per_month,
    free_kb_files_per_month = EXCLUDED.free_kb_files_per_month,
    free_storage_mb = EXCLUDED.free_storage_mb;
