-- P0 Migration: JSON files → Supabase + billing events + admin lockout
-- Run this in Supabase SQL Editor

-- ============================================================================
-- 1. User Features table (replaces user_features.json)
-- ============================================================================
CREATE TABLE IF NOT EXISTS user_features (
    user_id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    features JSONB NOT NULL DEFAULT '{}'::jsonb,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_user_features_updated ON user_features(updated_at DESC);

-- Allow service role full access; RLS policy for user self-access
ALTER TABLE user_features ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can view own features" ON user_features
    FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can update own features" ON user_features
    FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own features" ON user_features
    FOR INSERT WITH CHECK (auth.uid() = user_id);

-- ============================================================================
-- 2. Billing events table (webhook idempotency)
-- ============================================================================
CREATE TABLE IF NOT EXISTS billing_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    payment_id VARCHAR(255) NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    plan VARCHAR(50),
    order_id VARCHAR(255),
    raw_payload JSONB,
    processed_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(payment_id, event_type)
);

CREATE INDEX IF NOT EXISTS idx_billing_events_payment ON billing_events(payment_id);
CREATE INDEX IF NOT EXISTS idx_billing_events_user ON billing_events(user_id);

-- ============================================================================
-- 3. Admin login attempts table (lockout tracking)
-- ============================================================================
CREATE TABLE IF NOT EXISTS admin_login_attempts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ip_address VARCHAR(45) NOT NULL,
    email VARCHAR(255),
    success BOOLEAN NOT NULL DEFAULT FALSE,
    attempted_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_admin_login_ip ON admin_login_attempts(ip_address, attempted_at DESC);

-- ============================================================================
-- 4. Add metadata JSONB column to posts table if missing
--    (the existing schema has a posts table but may lack some columns
--     used by the JSON-file format)
-- ============================================================================
DO $$
BEGIN
    -- Add columns that the JSON post format uses but the DB schema may lack
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='posts' AND column_name='metadata') THEN
        ALTER TABLE posts ADD COLUMN metadata JSONB DEFAULT '{}'::jsonb;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='posts' AND column_name='posted') THEN
        ALTER TABLE posts ADD COLUMN posted BOOLEAN DEFAULT FALSE;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='posts' AND column_name='test_mode') THEN
        ALTER TABLE posts ADD COLUMN test_mode BOOLEAN DEFAULT FALSE;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='posts' AND column_name='linkedin_urn') THEN
        ALTER TABLE posts ADD COLUMN linkedin_urn VARCHAR(255);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='posts' AND column_name='analytics') THEN
        ALTER TABLE posts ADD COLUMN analytics JSONB DEFAULT '{}'::jsonb;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='posts' AND column_name='provider') THEN
        ALTER TABLE posts ADD COLUMN provider VARCHAR(50);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='posts' AND column_name='kb_mode') THEN
        ALTER TABLE posts ADD COLUMN kb_mode VARCHAR(50);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='posts' AND column_name='workspace_id') THEN
        ALTER TABLE posts ADD COLUMN workspace_id VARCHAR(255);
    END IF;
END $$;

-- ============================================================================
-- 5. scheduled_posts_v2 table (flat scheduled posts, no FK to posts)
--    Used instead of the existing scheduled_posts table which requires FK.
-- ============================================================================
CREATE TABLE IF NOT EXISTS scheduled_posts_v2 (
    id VARCHAR(50) PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    content TEXT NOT NULL DEFAULT '',
    hashtags TEXT[] DEFAULT '{}',
    schedule_time TEXT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    error_message TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sp_v2_user ON scheduled_posts_v2(user_id, status);
CREATE INDEX IF NOT EXISTS idx_sp_v2_due ON scheduled_posts_v2(status, schedule_time)
    WHERE status = 'pending';

ALTER TABLE scheduled_posts_v2 ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can view own scheduled posts" ON scheduled_posts_v2
    FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own scheduled posts" ON scheduled_posts_v2
    FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update own scheduled posts" ON scheduled_posts_v2
    FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "Users can delete own scheduled posts" ON scheduled_posts_v2
    FOR DELETE USING (auth.uid() = user_id);