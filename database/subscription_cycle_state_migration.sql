-- Add fields required for fair proration and scheduled plan changes.
ALTER TABLE subscriptions
ADD COLUMN IF NOT EXISTS scheduled_plan VARCHAR(50),
ADD COLUMN IF NOT EXISTS current_plan_currency VARCHAR(10),
ADD COLUMN IF NOT EXISTS current_plan_price_minor INTEGER DEFAULT 0;

CREATE INDEX IF NOT EXISTS idx_subscriptions_scheduled_plan
ON subscriptions (scheduled_plan)
WHERE scheduled_plan IS NOT NULL;
