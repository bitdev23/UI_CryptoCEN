-- Supabase Schema for ContentAI Pro Multi-Tenant SaaS
-- Run this in Supabase SQL Editor after project creation

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For text search

-- ============================================================================
-- USER PROFILES & SETTINGS
-- ============================================================================

-- User profiles (extends Supabase auth.users)
CREATE TABLE user_profiles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE UNIQUE NOT NULL,
    industry VARCHAR(100),
    role VARCHAR(100),
    timezone VARCHAR(50) DEFAULT 'UTC',
    min_post_length INT DEFAULT 150,
    max_post_length INT DEFAULT 1000,
    default_ai_provider VARCHAR(50) DEFAULT 'google',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- User API keys (encrypted)
CREATE TABLE user_api_keys (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    provider VARCHAR(50) NOT NULL,  -- google, openai, anthropic
    api_key_encrypted TEXT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, provider)
);

-- LinkedIn connections
CREATE TABLE linkedin_connections (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE UNIQUE NOT NULL,
    access_token_encrypted TEXT NOT NULL,
    refresh_token_encrypted TEXT,
    person_id VARCHAR(255) NOT NULL,
    expires_at TIMESTAMPTZ,
    is_connected BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- KNOWLEDGE BASE
-- ============================================================================

-- Knowledge base files
CREATE TABLE kb_files (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    filename VARCHAR(255) NOT NULL,
    file_size_bytes BIGINT NOT NULL,
    file_type VARCHAR(10) NOT NULL,  -- pdf, docx
    storage_path TEXT NOT NULL,  -- Path in Supabase Storage
    upload_status VARCHAR(50) DEFAULT 'uploaded',  -- uploaded, processing, indexed, failed
    chunk_count INT DEFAULT 0,
    tags TEXT[],
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    processed_at TIMESTAMPTZ
);

-- Vector embeddings (THE KEY TABLE)
CREATE TABLE kb_embeddings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    file_id UUID REFERENCES kb_files(id) ON DELETE CASCADE NOT NULL,
    chunk_text TEXT NOT NULL,
    chunk_index INT NOT NULL,
    embedding vector(384) NOT NULL,  -- all-MiniLM-L6-v2 dimensions
    metadata JSONB,  -- Store page number, section, etc.
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- KB usage stats per user
CREATE TABLE kb_usage_stats (
    user_id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    total_files INT DEFAULT 0,
    total_size_bytes BIGINT DEFAULT 0,
    total_chunks INT DEFAULT 0,
    last_updated TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- POSTS & CONTENT
-- ============================================================================

-- Generated posts
CREATE TABLE posts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    topic TEXT,
    industry VARCHAR(100),
    role VARCHAR(100),
    tone VARCHAR(50),  -- professional, casual, authoritative, storytelling
    post_format VARCHAR(50),  -- story, thread, analysis, hook-first
    content TEXT NOT NULL,
    hashtags TEXT[],
    kb_used BOOLEAN DEFAULT FALSE,
    kb_source_files UUID[],  -- Array of file_ids used
    ai_provider VARCHAR(50),
    status VARCHAR(50) DEFAULT 'draft',  -- draft, posted, scheduled, failed
    created_at TIMESTAMPTZ DEFAULT NOW(),
    posted_at TIMESTAMPTZ,
    scheduled_for TIMESTAMPTZ,
    linkedin_post_id VARCHAR(255),
    error_message TEXT
);

-- Scheduled posts
CREATE TABLE scheduled_posts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    post_id UUID REFERENCES posts(id) ON DELETE CASCADE NOT NULL,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    scheduled_for TIMESTAMPTZ NOT NULL,
    timezone VARCHAR(50) NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',  -- pending, published, failed, cancelled
    retry_count INT DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    published_at TIMESTAMPTZ
);

-- Post analytics
CREATE TABLE post_analytics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    post_id UUID REFERENCES posts(id) ON DELETE CASCADE NOT NULL,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    impressions INT DEFAULT 0,
    likes INT DEFAULT 0,
    comments INT DEFAULT 0,
    shares INT DEFAULT 0,
    engagement_rate DECIMAL(5,2),
    fetched_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- TONE TRAINING (DIFFERENTIATION FEATURE)
-- ============================================================================

-- Tone samples (user's past posts for style analysis)
CREATE TABLE tone_samples (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    sample_text TEXT NOT NULL,
    source VARCHAR(50),  -- 'uploaded', 'linkedin_import', 'generated'
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Tone profiles (LLM-generated writing style analysis)
CREATE TABLE tone_profiles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE UNIQUE NOT NULL,
    profile_summary TEXT,
    vocabulary_preferences TEXT[],
    sentence_structure_notes TEXT,
    emoji_usage VARCHAR(50),  -- 'frequent', 'occasional', 'never'
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- SUBSCRIPTIONS & BILLING
-- ============================================================================

-- Subscriptions
CREATE TABLE subscriptions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE UNIQUE NOT NULL,
    plan VARCHAR(50) NOT NULL DEFAULT 'free',  -- free, pro, agency
    status VARCHAR(50) DEFAULT 'active',  -- active, cancelled, expired, past_due
    stripe_subscription_id VARCHAR(255) UNIQUE,
    stripe_customer_id VARCHAR(255),
    billing_provider VARCHAR(50), -- razorpay, stripe, manual
    provider_subscription_id VARCHAR(255) UNIQUE,
    provider_customer_id VARCHAR(255),
    provider_order_id VARCHAR(255),
    provider_payment_id VARCHAR(255),
    current_period_start TIMESTAMPTZ,
    current_period_end TIMESTAMPTZ,
    cancel_at_period_end BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Usage tracking (monthly)
CREATE TABLE usage_monthly (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    month DATE NOT NULL,  -- First day of month
    posts_generated INT DEFAULT 0,
    posts_published INT DEFAULT 0,
    kb_files_uploaded INT DEFAULT 0,
    kb_storage_bytes BIGINT DEFAULT 0,
    api_calls INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, month)
);

-- ============================================================================
-- ADMIN & OPERATIONS
-- ============================================================================

-- Background jobs tracking
CREATE TABLE background_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_type VARCHAR(100) NOT NULL,  -- kb_rebuild, post_publish, email_send
    user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    status VARCHAR(50) DEFAULT 'pending',  -- pending, running, completed, failed
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    error_message TEXT,
    retry_count INT DEFAULT 0,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- System logs
CREATE TABLE system_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    level VARCHAR(20) NOT NULL,  -- info, warning, error, critical
    message TEXT NOT NULL,
    user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    request_path TEXT,
    request_method VARCHAR(10),
    ip_address INET,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- INDEXES FOR PERFORMANCE
-- ============================================================================

-- User profiles
CREATE INDEX idx_user_profiles_user_id ON user_profiles(user_id);

-- KB files
CREATE INDEX idx_kb_files_user_id ON kb_files(user_id);
CREATE INDEX idx_kb_files_status ON kb_files(upload_status);
CREATE INDEX idx_kb_files_created ON kb_files(created_at DESC);

-- KB embeddings - MOST IMPORTANT INDEX
CREATE INDEX idx_kb_embeddings_user_id ON kb_embeddings(user_id);
CREATE INDEX idx_kb_embeddings_file_id ON kb_embeddings(file_id);
-- HNSW index for fast vector similarity search
CREATE INDEX idx_kb_embeddings_vector ON kb_embeddings 
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- Posts
CREATE INDEX idx_posts_user_id ON posts(user_id);
CREATE INDEX idx_posts_status ON posts(status);
CREATE INDEX idx_posts_created ON posts(created_at DESC);
CREATE INDEX idx_posts_scheduled ON posts(scheduled_for) WHERE scheduled_for IS NOT NULL;

-- Scheduled posts
CREATE INDEX idx_scheduled_posts_user_id ON scheduled_posts(user_id);
CREATE INDEX idx_scheduled_posts_status ON scheduled_posts(status);
CREATE INDEX idx_scheduled_posts_time ON scheduled_posts(scheduled_for);

-- Background jobs
CREATE INDEX idx_background_jobs_status ON background_jobs(status);
CREATE INDEX idx_background_jobs_type ON background_jobs(job_type);
CREATE INDEX idx_background_jobs_user ON background_jobs(user_id);

-- System logs
CREATE INDEX idx_system_logs_level ON system_logs(level);
CREATE INDEX idx_system_logs_created ON system_logs(created_at DESC);
CREATE INDEX idx_system_logs_user ON system_logs(user_id);

-- ============================================================================
-- ROW LEVEL SECURITY (RLS) - MULTI-TENANT ISOLATION
-- ============================================================================

-- Enable RLS on all user-scoped tables
ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_api_keys ENABLE ROW LEVEL SECURITY;
ALTER TABLE linkedin_connections ENABLE ROW LEVEL SECURITY;
ALTER TABLE kb_files ENABLE ROW LEVEL SECURITY;
ALTER TABLE kb_embeddings ENABLE ROW LEVEL SECURITY;
ALTER TABLE kb_usage_stats ENABLE ROW LEVEL SECURITY;
ALTER TABLE posts ENABLE ROW LEVEL SECURITY;
ALTER TABLE scheduled_posts ENABLE ROW LEVEL SECURITY;
ALTER TABLE post_analytics ENABLE ROW LEVEL SECURITY;
ALTER TABLE tone_samples ENABLE ROW LEVEL SECURITY;
ALTER TABLE tone_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE usage_monthly ENABLE ROW LEVEL SECURITY;

-- User profiles policies
CREATE POLICY "Users can view own profile" ON user_profiles
    FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can update own profile" ON user_profiles
    FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own profile" ON user_profiles
    FOR INSERT WITH CHECK (auth.uid() = user_id);

-- User API keys policies
CREATE POLICY "Users can manage own API keys" ON user_api_keys
    FOR ALL USING (auth.uid() = user_id);

-- LinkedIn connections policies
CREATE POLICY "Users can manage own LinkedIn connection" ON linkedin_connections
    FOR ALL USING (auth.uid() = user_id);

-- KB files policies
CREATE POLICY "Users can view own KB files" ON kb_files
    FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own KB files" ON kb_files
    FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update own KB files" ON kb_files
    FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "Users can delete own KB files" ON kb_files
    FOR DELETE USING (auth.uid() = user_id);

-- KB embeddings policies
CREATE POLICY "Users can view own embeddings" ON kb_embeddings
    FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own embeddings" ON kb_embeddings
    FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can delete own embeddings" ON kb_embeddings
    FOR DELETE USING (auth.uid() = user_id);

-- KB usage stats policies
CREATE POLICY "Users can view own KB stats" ON kb_usage_stats
    FOR ALL USING (auth.uid() = user_id);

-- Posts policies
CREATE POLICY "Users can manage own posts" ON posts
    FOR ALL USING (auth.uid() = user_id);

-- Scheduled posts policies
CREATE POLICY "Users can manage own scheduled posts" ON scheduled_posts
    FOR ALL USING (auth.uid() = user_id);

-- Post analytics policies
CREATE POLICY "Users can view own analytics" ON post_analytics
    FOR ALL USING (auth.uid() = user_id);

-- Tone samples policies
CREATE POLICY "Users can manage own tone samples" ON tone_samples
    FOR ALL USING (auth.uid() = user_id);

-- Tone profiles policies
CREATE POLICY "Users can manage own tone profile" ON tone_profiles
    FOR ALL USING (auth.uid() = user_id);

-- Subscriptions policies
CREATE POLICY "Users can view own subscription" ON subscriptions
    FOR SELECT USING (auth.uid() = user_id);

-- Usage monthly policies
CREATE POLICY "Users can view own usage" ON usage_monthly
    FOR SELECT USING (auth.uid() = user_id);

-- ============================================================================
-- TRIGGERS FOR AUTOMATIC UPDATES
-- ============================================================================

-- Update updated_at timestamp automatically
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply to all tables with updated_at
CREATE TRIGGER update_user_profiles_updated_at BEFORE UPDATE ON user_profiles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    
CREATE TRIGGER update_user_api_keys_updated_at BEFORE UPDATE ON user_api_keys
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    
CREATE TRIGGER update_linkedin_connections_updated_at BEFORE UPDATE ON linkedin_connections
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    
CREATE TRIGGER update_tone_profiles_updated_at BEFORE UPDATE ON tone_profiles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    
CREATE TRIGGER update_subscriptions_updated_at BEFORE UPDATE ON subscriptions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Update KB usage stats when files are added/removed
CREATE OR REPLACE FUNCTION update_kb_usage_stats()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO kb_usage_stats (user_id, total_files, total_size_bytes, total_chunks)
        VALUES (NEW.user_id, 1, NEW.file_size_bytes, NEW.chunk_count)
        ON CONFLICT (user_id) DO UPDATE SET
            total_files = kb_usage_stats.total_files + 1,
            total_size_bytes = kb_usage_stats.total_size_bytes + EXCLUDED.total_size_bytes,
            total_chunks = kb_usage_stats.total_chunks + EXCLUDED.total_chunks,
            last_updated = NOW();
    ELSIF TG_OP = 'DELETE' THEN
        UPDATE kb_usage_stats SET
            total_files = GREATEST(total_files - 1, 0),
            total_size_bytes = GREATEST(total_size_bytes - OLD.file_size_bytes, 0),
            total_chunks = GREATEST(total_chunks - OLD.chunk_count, 0),
            last_updated = NOW()
        WHERE user_id = OLD.user_id;
    ELSIF TG_OP = 'UPDATE' AND (NEW.chunk_count != OLD.chunk_count) THEN
        UPDATE kb_usage_stats SET
            total_chunks = total_chunks - OLD.chunk_count + NEW.chunk_count,
            last_updated = NOW()
        WHERE user_id = NEW.user_id;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER kb_files_update_stats
    AFTER INSERT OR UPDATE OR DELETE ON kb_files
    FOR EACH ROW EXECUTE FUNCTION update_kb_usage_stats();

-- ============================================================================
-- STORAGE BUCKET SETUP (Run in Supabase Dashboard > Storage)
-- ============================================================================

-- Create storage bucket for KB files
-- Run this in the Supabase Dashboard after enabling Storage:
-- INSERT INTO storage.buckets (id, name, public) VALUES ('kb-files', 'kb-files', false);

-- Storage policies (allow users to upload/view their own files)
-- CREATE POLICY "Users can upload own KB files" ON storage.objects
--     FOR INSERT WITH CHECK (bucket_id = 'kb-files' AND auth.uid()::text = (storage.foldername(name))[1]);
-- CREATE POLICY "Users can view own KB files" ON storage.objects
--     FOR SELECT USING (bucket_id = 'kb-files' AND auth.uid()::text = (storage.foldername(name))[1]);
-- CREATE POLICY "Users can delete own KB files" ON storage.objects
--     FOR DELETE USING (bucket_id = 'kb-files' AND auth.uid()::text = (storage.foldername(name))[1]);

-- ============================================================================
-- INITIAL DATA (Optional)
-- ============================================================================

-- Create default subscription plans metadata (for reference)
CREATE TABLE IF NOT EXISTS plan_limits (
    plan VARCHAR(50) PRIMARY KEY,
    posts_per_month INT NOT NULL,
    kb_files_max INT NOT NULL,
    kb_storage_mb INT NOT NULL,
    industries_max INT NOT NULL,
    tone_training BOOLEAN DEFAULT FALSE,
    analytics_advanced BOOLEAN DEFAULT FALSE,
    api_access BOOLEAN DEFAULT FALSE,
    priority_support BOOLEAN DEFAULT FALSE
);

INSERT INTO plan_limits (plan, posts_per_month, kb_files_max, kb_storage_mb, industries_max, tone_training, analytics_advanced, api_access, priority_support) VALUES
('free', 10, 5, 50, 1, FALSE, FALSE, FALSE, FALSE),
('pro', 100, 100, 500, 5, TRUE, TRUE, FALSE, TRUE),
('agency', -1, -1, -1, -1, TRUE, TRUE, TRUE, TRUE);  -- -1 = unlimited

-- ============================================================================
-- COMMENTS FOR DOCUMENTATION
-- ============================================================================

COMMENT ON TABLE kb_embeddings IS 'Stores vector embeddings for semantic search using pgvector';
COMMENT ON COLUMN kb_embeddings.embedding IS 'Vector embedding (384 dimensions from all-MiniLM-L6-v2)';
COMMENT ON INDEX idx_kb_embeddings_vector IS 'HNSW index for fast cosine similarity search';
COMMENT ON TABLE user_profiles IS 'Extended user settings beyond Supabase auth.users';
COMMENT ON TABLE subscriptions IS 'User subscription plans and billing provider metadata';
COMMENT ON TABLE usage_monthly IS 'Track monthly usage for quota enforcement';
