-- Razorpay billing migration for existing installations
-- Run this once on an existing Supabase database

ALTER TABLE subscriptions
ADD COLUMN IF NOT EXISTS billing_provider VARCHAR(50),
ADD COLUMN IF NOT EXISTS provider_subscription_id VARCHAR(255),
ADD COLUMN IF NOT EXISTS provider_customer_id VARCHAR(255),
ADD COLUMN IF NOT EXISTS provider_order_id VARCHAR(255),
ADD COLUMN IF NOT EXISTS provider_payment_id VARCHAR(255);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes
        WHERE schemaname = 'public' AND indexname = 'subscriptions_provider_subscription_id_key'
    ) THEN
        CREATE UNIQUE INDEX subscriptions_provider_subscription_id_key
        ON subscriptions(provider_subscription_id)
        WHERE provider_subscription_id IS NOT NULL;
    END IF;
END $$;
