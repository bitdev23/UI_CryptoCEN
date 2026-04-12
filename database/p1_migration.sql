-- P1 Migration: AI cost tracking columns on usage_monthly
-- Run this in Supabase SQL Editor AFTER p0_migration.sql

-- ============================================================================
-- 1. Add AI token/cost tracking columns to usage_monthly
-- ============================================================================
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='usage_monthly' AND column_name='ai_prompt_tokens') THEN
        ALTER TABLE usage_monthly ADD COLUMN ai_prompt_tokens BIGINT DEFAULT 0;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='usage_monthly' AND column_name='ai_completion_tokens') THEN
        ALTER TABLE usage_monthly ADD COLUMN ai_completion_tokens BIGINT DEFAULT 0;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='usage_monthly' AND column_name='ai_total_tokens') THEN
        ALTER TABLE usage_monthly ADD COLUMN ai_total_tokens BIGINT DEFAULT 0;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='usage_monthly' AND column_name='ai_cost_usd_micros') THEN
        ALTER TABLE usage_monthly ADD COLUMN ai_cost_usd_micros BIGINT DEFAULT 0;
    END IF;
END $$;
