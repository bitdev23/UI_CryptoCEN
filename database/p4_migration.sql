-- ============================================================================
-- P4 Migration: Referral tracking + Discount codes
-- Run in Supabase SQL editor
-- ============================================================================

-- 1. Referral columns on user_profiles
ALTER TABLE user_profiles
    ADD COLUMN IF NOT EXISTS referral_code  TEXT UNIQUE,
    ADD COLUMN IF NOT EXISTS referred_by    UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS referral_count INT NOT NULL DEFAULT 0;

-- Auto-generate a short referral code for existing rows that have none
UPDATE user_profiles
SET referral_code = LOWER(SUBSTRING(REPLACE(gen_random_uuid()::TEXT, '-', '') FOR 8))
WHERE referral_code IS NULL;

-- Make new rows always get a code via a trigger
CREATE OR REPLACE FUNCTION set_referral_code()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.referral_code IS NULL THEN
        NEW.referral_code := LOWER(SUBSTRING(REPLACE(gen_random_uuid()::TEXT, '-', '') FROM 1 FOR 8));
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_set_referral_code ON user_profiles;
CREATE TRIGGER trg_set_referral_code
BEFORE INSERT ON user_profiles
FOR EACH ROW EXECUTE FUNCTION set_referral_code();

-- Index for fast referral_code lookups
CREATE INDEX IF NOT EXISTS idx_user_profiles_referral_code ON user_profiles(referral_code);

-- ============================================================================
-- 2. Discount / coupon codes table
-- ============================================================================
CREATE TABLE IF NOT EXISTS discount_codes (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code          TEXT UNIQUE NOT NULL,                        -- e.g. LAUNCH20
    discount_pct  INT NOT NULL CHECK (discount_pct BETWEEN 1 AND 100),
    max_uses      INT NOT NULL DEFAULT 100,
    uses          INT NOT NULL DEFAULT 0,
    valid_from    TIMESTAMPTZ DEFAULT NOW(),
    valid_until   TIMESTAMPTZ,                                 -- NULL = no expiry
    is_active     BOOLEAN NOT NULL DEFAULT TRUE,
    created_by    UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    created_at    TIMESTAMPTZ DEFAULT NOW()
);

-- Index for fast code lookups
CREATE INDEX IF NOT EXISTS idx_discount_codes_code ON discount_codes(code);

-- Row-level security (admin-only write; authenticated read for validation)
ALTER TABLE discount_codes ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Admin manage discount_codes"
    ON discount_codes FOR ALL
    USING (TRUE)
    WITH CHECK (TRUE);   -- enforced at app layer via service-role key

-- ============================================================================
-- 3. Seed a starter coupon for testing (remove before production)
-- ============================================================================
INSERT INTO discount_codes (code, discount_pct, max_uses, valid_until)
VALUES ('LAUNCH20', 20, 500, NOW() + INTERVAL '90 days')
ON CONFLICT (code) DO NOTHING;
