-- Supabase Functions & Stored Procedures
-- Run these AFTER the schema is created

-- ============================================================================
-- VECTOR SEARCH FUNCTIONS
-- ============================================================================

-- Main function: Search KB embeddings using vector similarity
CREATE OR REPLACE FUNCTION match_kb_chunks(
    query_embedding vector(384),
    match_threshold float DEFAULT 0.7,
    match_count int DEFAULT 4,
    filter_user_id uuid DEFAULT NULL
)
RETURNS TABLE (
    id uuid,
    file_id uuid,
    chunk_text text,
    chunk_index int,
    similarity float,
    metadata jsonb
)
LANGUAGE plpgsql
SECURITY DEFINER  -- Run with privileges to bypass RLS for performance
AS $$
BEGIN
    RETURN QUERY
    SELECT
        kb_embeddings.id,
        kb_embeddings.file_id,
        kb_embeddings.chunk_text,
        kb_embeddings.chunk_index,
        1 - (kb_embeddings.embedding <=> query_embedding) AS similarity,
        kb_embeddings.metadata
    FROM kb_embeddings
    WHERE 
        -- User isolation (if filter_user_id provided, else use auth.uid())
        kb_embeddings.user_id = COALESCE(filter_user_id, auth.uid())
        -- Similarity threshold
        AND 1 - (kb_embeddings.embedding <=> query_embedding) > match_threshold
    ORDER BY kb_embeddings.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- Search KB by file IDs (for specific file targeting)
CREATE OR REPLACE FUNCTION match_kb_chunks_by_files(
    query_embedding vector(384),
    file_ids uuid[],
    match_threshold float DEFAULT 0.7,
    match_count int DEFAULT 4
)
RETURNS TABLE (
    id uuid,
    file_id uuid,
    chunk_text text,
    similarity float,
    metadata jsonb
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    RETURN QUERY
    SELECT
        kb_embeddings.id,
        kb_embeddings.file_id,
        kb_embeddings.chunk_text,
        1 - (kb_embeddings.embedding <=> query_embedding) AS similarity,
        kb_embeddings.metadata
    FROM kb_embeddings
    WHERE 
        kb_embeddings.user_id = auth.uid()
        AND kb_embeddings.file_id = ANY(file_ids)
        AND 1 - (kb_embeddings.embedding <=> query_embedding) > match_threshold
    ORDER BY kb_embeddings.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- ============================================================================
-- USAGE & QUOTA FUNCTIONS
-- ============================================================================

-- Check if user can generate more posts this month
CREATE OR REPLACE FUNCTION can_generate_post()
RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    user_plan VARCHAR(50);
    plan_post_limit INT;
    current_usage INT;
    current_month DATE;
BEGIN
    -- Get user's plan
    SELECT plan INTO user_plan
    FROM subscriptions
    WHERE user_id = auth.uid() AND status = 'active'
    LIMIT 1;
    
    -- Default to free if no subscription
    user_plan := COALESCE(user_plan, 'free');
    
    -- Get plan limit
    SELECT posts_per_month INTO plan_post_limit
    FROM plan_limits
    WHERE plan = user_plan;
    
    -- -1 means unlimited
    IF plan_post_limit = -1 THEN
        RETURN TRUE;
    END IF;
    
    -- Get current month usage
    current_month := DATE_TRUNC('month', NOW())::DATE;
    
    SELECT COALESCE(posts_generated, 0) INTO current_usage
    FROM usage_monthly
    WHERE user_id = auth.uid() AND month = current_month;
    
    -- Check if under limit
    RETURN COALESCE(current_usage, 0) < plan_post_limit;
END;
$$;

-- Check if user can upload more KB files
CREATE OR REPLACE FUNCTION can_upload_kb_file(file_size_bytes BIGINT)
RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    user_plan VARCHAR(50);
    plan_file_limit INT;
    plan_storage_limit BIGINT;
    current_file_count INT;
    current_storage_bytes BIGINT;
BEGIN
    -- Get user's plan
    SELECT plan INTO user_plan
    FROM subscriptions
    WHERE user_id = auth.uid() AND status = 'active'
    LIMIT 1;
    
    user_plan := COALESCE(user_plan, 'free');
    
    -- Get plan limits
    SELECT kb_files_max, kb_storage_mb * 1024 * 1024 
    INTO plan_file_limit, plan_storage_limit
    FROM plan_limits
    WHERE plan = user_plan;
    
    -- -1 means unlimited
    IF plan_file_limit = -1 THEN
        RETURN TRUE;
    END IF;
    
    -- Get current usage
    SELECT COALESCE(total_files, 0), COALESCE(total_size_bytes, 0)
    INTO current_file_count, current_storage_bytes
    FROM kb_usage_stats
    WHERE user_id = auth.uid();
    
    -- Check both file count and storage limits
    RETURN (current_file_count < plan_file_limit) 
        AND ((current_storage_bytes + file_size_bytes) <= plan_storage_limit);
END;
$$;

-- Increment usage counter (called after successful action)
CREATE OR REPLACE FUNCTION increment_usage(
    action_type VARCHAR(50),  -- 'post_generated', 'post_published', 'kb_file_uploaded'
    increment_value INT DEFAULT 1
)
RETURNS VOID
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    current_month DATE;
BEGIN
    current_month := DATE_TRUNC('month', NOW())::DATE;
    
    IF action_type = 'post_generated' THEN
        INSERT INTO usage_monthly (user_id, month, posts_generated)
        VALUES (auth.uid(), current_month, increment_value)
        ON CONFLICT (user_id, month) DO UPDATE SET
            posts_generated = usage_monthly.posts_generated + increment_value;
            
    ELSIF action_type = 'post_published' THEN
        INSERT INTO usage_monthly (user_id, month, posts_published)
        VALUES (auth.uid(), current_month, increment_value)
        ON CONFLICT (user_id, month) DO UPDATE SET
            posts_published = usage_monthly.posts_published + increment_value;
            
    ELSIF action_type = 'kb_file_uploaded' THEN
        INSERT INTO usage_monthly (user_id, month, kb_files_uploaded)
        VALUES (auth.uid(), current_month, increment_value)
        ON CONFLICT (user_id, month) DO UPDATE SET
            kb_files_uploaded = usage_monthly.kb_files_uploaded + increment_value;
    END IF;
END;
$$;

-- ============================================================================
-- ANALYTICS & STATS FUNCTIONS
-- ============================================================================

-- Get user dashboard stats
CREATE OR REPLACE FUNCTION get_dashboard_stats(target_user_id UUID DEFAULT NULL)
RETURNS JSON
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    user_uuid UUID;
    result JSON;
BEGIN
    user_uuid := COALESCE(target_user_id, auth.uid());
    
    SELECT json_build_object(
        'total_posts', (SELECT COUNT(*) FROM posts WHERE user_id = user_uuid AND status = 'posted'),
        'total_drafts', (SELECT COUNT(*) FROM posts WHERE user_id = user_uuid AND status = 'draft'),
        'scheduled_posts', (SELECT COUNT(*) FROM scheduled_posts WHERE user_id = user_uuid AND status = 'pending'),
        'kb_files', (SELECT COALESCE(total_files, 0) FROM kb_usage_stats WHERE user_id = user_uuid),
        'kb_chunks', (SELECT COALESCE(total_chunks, 0) FROM kb_usage_stats WHERE user_id = user_uuid),
        'kb_storage_mb', (SELECT COALESCE(total_size_bytes / 1024.0 / 1024.0, 0) FROM kb_usage_stats WHERE user_id = user_uuid),
        'current_streak', calculate_posting_streak(user_uuid),
        'this_month_posts', (
            SELECT COALESCE(posts_generated, 0) 
            FROM usage_monthly 
            WHERE user_id = user_uuid 
                AND month = DATE_TRUNC('month', NOW())::DATE
        )
    ) INTO result;
    
    RETURN result;
END;
$$;

-- Calculate posting streak (consecutive days with at least 1 post)
CREATE OR REPLACE FUNCTION calculate_posting_streak(target_user_id UUID)
RETURNS INT
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    streak INT := 0;
    check_date DATE;
    has_post BOOLEAN;
BEGIN
    check_date := CURRENT_DATE;
    
    LOOP
        -- Check if there's a post on this date
        SELECT EXISTS(
            SELECT 1 FROM posts
            WHERE user_id = target_user_id
                AND status = 'posted'
                AND DATE(posted_at) = check_date
        ) INTO has_post;
        
        IF has_post THEN
            streak := streak + 1;
            check_date := check_date - INTERVAL '1 day';
        ELSE
            -- If today has no post but yesterday does, don't break streak yet
            IF check_date = CURRENT_DATE THEN
                check_date := check_date - INTERVAL '1 day';
            ELSE
                EXIT;
            END IF;
        END IF;
        
        -- Safety: Don't go back more than 365 days
        IF streak > 365 THEN
            EXIT;
        END IF;
    END LOOP;
    
    RETURN streak;
END;
$$;

-- Get next scheduled post
CREATE OR REPLACE FUNCTION get_next_scheduled_post()
RETURNS JSON
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    result JSON;
BEGIN
    SELECT json_build_object(
        'id', sp.id,
        'post_id', sp.post_id,
        'scheduled_for', sp.scheduled_for,
        'timezone', sp.timezone,
        'content', p.content,
        'hashtags', p.hashtags
    ) INTO result
    FROM scheduled_posts sp
    JOIN posts p ON p.id = sp.post_id
    WHERE sp.user_id = auth.uid()
        AND sp.status = 'pending'
        AND sp.scheduled_for > NOW()
    ORDER BY sp.scheduled_for ASC
    LIMIT 1;
    
    RETURN result;
END;
$$;

-- ============================================================================
-- ADMIN FUNCTIONS
-- ============================================================================

-- Get system-wide stats (admin only)
CREATE OR REPLACE FUNCTION get_admin_stats()
RETURNS JSON
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    result JSON;
    is_admin BOOLEAN;
BEGIN
    -- Check if user is admin (you'll need to add admin role to auth.users metadata)
    SELECT (auth.jwt()->>'email' = 'admin@yourdomain.com') INTO is_admin;
    
    IF NOT is_admin THEN
        RAISE EXCEPTION 'Unauthorized: Admin access required';
    END IF;
    
    SELECT json_build_object(
        'total_users', (SELECT COUNT(*) FROM auth.users),
        'active_subscriptions', (SELECT COUNT(*) FROM subscriptions WHERE status = 'active'),
        'total_posts', (SELECT COUNT(*) FROM posts),
        'total_kb_files', (SELECT COUNT(*) FROM kb_files),
        'total_embeddings', (SELECT COUNT(*) FROM kb_embeddings),
        'failed_jobs_24h', (
            SELECT COUNT(*) FROM background_jobs 
            WHERE status = 'failed' 
                AND created_at > NOW() - INTERVAL '24 hours'
        ),
        'revenue_mrr', (
            SELECT SUM(
                CASE 
                    WHEN plan = 'pro' THEN 29
                    WHEN plan = 'agency' THEN 99
                    ELSE 0
                END
            )
            FROM subscriptions
            WHERE status = 'active'
        )
    ) INTO result;
    
    RETURN result;
END;
$$;

-- ============================================================================
-- CLEANUP FUNCTIONS
-- ============================================================================

-- Delete old system logs (run daily via cron)
CREATE OR REPLACE FUNCTION cleanup_old_logs(days_to_keep INT DEFAULT 30)
RETURNS INT
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    deleted_count INT;
BEGIN
    DELETE FROM system_logs
    WHERE created_at < NOW() - (days_to_keep || ' days')::INTERVAL;
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$;

-- Delete failed background jobs older than 7 days
CREATE OR REPLACE FUNCTION cleanup_old_background_jobs(days_to_keep INT DEFAULT 7)
RETURNS INT
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    deleted_count INT;
BEGIN
    DELETE FROM background_jobs
    WHERE status IN ('completed', 'failed')
        AND created_at < NOW() - (days_to_keep || ' days')::INTERVAL;
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$;

-- ============================================================================
-- HELPER FUNCTIONS
-- ============================================================================

-- Check if user has active subscription
CREATE OR REPLACE FUNCTION has_active_subscription()
RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    RETURN EXISTS(
        SELECT 1 FROM subscriptions
        WHERE user_id = auth.uid()
            AND status = 'active'
            AND (current_period_end IS NULL OR current_period_end > NOW())
    );
END;
$$;

-- Get user's current plan
CREATE OR REPLACE FUNCTION get_user_plan()
RETURNS VARCHAR(50)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    user_plan VARCHAR(50);
BEGIN
    SELECT plan INTO user_plan
    FROM subscriptions
    WHERE user_id = auth.uid() AND status = 'active'
    LIMIT 1;
    
    RETURN COALESCE(user_plan, 'free');
END;
$$;

-- ============================================================================
-- GRANT PERMISSIONS
-- ============================================================================

-- Grant execute permission to authenticated users
GRANT EXECUTE ON FUNCTION match_kb_chunks TO authenticated;
GRANT EXECUTE ON FUNCTION match_kb_chunks_by_files TO authenticated;
GRANT EXECUTE ON FUNCTION can_generate_post TO authenticated;
GRANT EXECUTE ON FUNCTION can_upload_kb_file TO authenticated;
GRANT EXECUTE ON FUNCTION increment_usage TO authenticated;
GRANT EXECUTE ON FUNCTION get_dashboard_stats TO authenticated;
GRANT EXECUTE ON FUNCTION calculate_posting_streak TO authenticated;
GRANT EXECUTE ON FUNCTION get_next_scheduled_post TO authenticated;
GRANT EXECUTE ON FUNCTION has_active_subscription TO authenticated;
GRANT EXECUTE ON FUNCTION get_user_plan TO authenticated;

-- Admin functions (restrict as needed)
GRANT EXECUTE ON FUNCTION get_admin_stats TO authenticated;
GRANT EXECUTE ON FUNCTION cleanup_old_logs TO authenticated;
GRANT EXECUTE ON FUNCTION cleanup_old_background_jobs TO authenticated;

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON FUNCTION match_kb_chunks IS 'Search user KB using vector similarity with pgvector';
COMMENT ON FUNCTION can_generate_post IS 'Check if user is within monthly post quota';
COMMENT ON FUNCTION can_upload_kb_file IS 'Check if user can upload file (quota + storage limits)';
COMMENT ON FUNCTION get_dashboard_stats IS 'Get all dashboard statistics in one call';
COMMENT ON FUNCTION calculate_posting_streak IS 'Calculate consecutive days of posting';
