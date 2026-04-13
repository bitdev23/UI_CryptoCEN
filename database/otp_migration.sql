-- ============================================================
-- OTP Migration: password_reset_otps table
-- Run once in Supabase SQL Editor
-- ============================================================

CREATE TABLE IF NOT EXISTS password_reset_otps (
    email       TEXT PRIMARY KEY,
    code        TEXT NOT NULL,
    expires_at  TIMESTAMPTZ NOT NULL,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Auto-delete expired rows after 1 hour (cleanup via Supabase cron or manual purge)
-- No RLS needed — only accessed via service-role key from backend

-- Index for fast lookup (already covered by PRIMARY KEY on email, but explicit)
CREATE INDEX IF NOT EXISTS idx_otp_expires ON password_reset_otps(expires_at);
