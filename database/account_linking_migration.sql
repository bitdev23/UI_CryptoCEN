-- ============================================================================
-- ACCOUNT LINKING SUPPORT
-- Allows users to authenticate with multiple methods (email/password + OAuth)
-- on the same account
-- ============================================================================

-- Track which authentication methods are linked to each user account
CREATE TABLE IF NOT EXISTS auth_linked_identities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    provider VARCHAR(50) NOT NULL, -- 'email', 'google', 'github', 'discord', etc.
    provider_user_id VARCHAR(500), -- OAuth provider's user ID (for google: sub claim)
    email VARCHAR(255), -- Email associated with this identity
    is_primary BOOLEAN DEFAULT FALSE, -- Primary identity for the account
    linked_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, provider) -- Only one instance of each provider per user
);

-- For fast email-based lookups across all identities
CREATE INDEX IF NOT EXISTS idx_auth_linked_identities_email ON auth_linked_identities(email) 
    WHERE email IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_auth_linked_identities_user_id ON auth_linked_identities(user_id);
CREATE INDEX IF NOT EXISTS idx_auth_linked_identities_provider ON auth_linked_identities(provider);
CREATE INDEX IF NOT EXISTS idx_auth_linked_identities_provider_user_id ON auth_linked_identities(provider, provider_user_id) 
    WHERE provider_user_id IS NOT NULL;

-- ============================================================================
-- HELPER FUNCTIONS FOR ACCOUNT LINKING
-- ============================================================================

-- Function: Find user by email across all linked identities
-- Returns the user_id if found, NULL otherwise
CREATE OR REPLACE FUNCTION find_user_by_email(p_email VARCHAR)
RETURNS UUID AS $$
DECLARE
    found_user_id UUID;
BEGIN
    -- First check if email exists directly in auth.users
    SELECT id INTO found_user_id
    FROM auth.users
    WHERE email = LOWER(p_email)
    LIMIT 1;
    
    IF found_user_id IS NOT NULL THEN
        RETURN found_user_id;
    END IF;
    
    -- Then check linked identities table
    SELECT user_id INTO found_user_id
    FROM auth_linked_identities
    WHERE LOWER(email) = LOWER(p_email)
    LIMIT 1;
    
    RETURN found_user_id;
END;
$$ LANGUAGE plpgsql;

-- Function: Check if an identity is already linked
-- Returns true if the provider+provider_user_id is already linked
CREATE OR REPLACE FUNCTION is_identity_linked(p_provider VARCHAR, p_provider_user_id VARCHAR)
RETURNS BOOLEAN AS $$
DECLARE
    exists_flag BOOLEAN;
BEGIN
    SELECT EXISTS(
        SELECT 1 FROM auth_linked_identities
        WHERE provider = p_provider 
            AND provider_user_id = p_provider_user_id
    ) INTO exists_flag;
    
    RETURN exists_flag;
END;
$$ LANGUAGE plpgsql;

-- Function: Link a new identity to existing user account
-- Returns the user_id if successful, NULL if identity already linked elsewhere
CREATE OR REPLACE FUNCTION link_identity_to_user(
    p_user_id UUID,
    p_provider VARCHAR,
    p_provider_user_id VARCHAR,
    p_email VARCHAR
)
RETURNS UUID AS $$
DECLARE
    existing_user_id UUID;
BEGIN
    -- Check if this identity is already linked to a different user
    SELECT user_id INTO existing_user_id
    FROM auth_linked_identities
    WHERE provider = p_provider 
        AND provider_user_id = p_provider_user_id
        AND user_id != p_user_id;
    
    IF existing_user_id IS NOT NULL THEN
        -- Identity already linked to another user
        RAISE EXCEPTION 'Identity already linked to another account';
    END IF;
    
    -- Insert or update the linked identity
    INSERT INTO auth_linked_identities 
        (user_id, provider, provider_user_id, email, is_primary, linked_at)
    VALUES 
        (p_user_id, p_provider, p_provider_user_id, p_email, FALSE, NOW())
    ON CONFLICT (user_id, provider) 
    DO UPDATE SET 
        provider_user_id = EXCLUDED.provider_user_id,
        email = EXCLUDED.email,
        updated_at = NOW();
    
    RETURN p_user_id;
END;
$$ LANGUAGE plpgsql;

-- Function: Get all linked identities for a user
-- Returns a list of providers linked to the user
CREATE OR REPLACE FUNCTION get_user_linked_providers(p_user_id UUID)
RETURNS TABLE(provider VARCHAR, email VARCHAR, is_primary BOOLEAN) AS $$
BEGIN
    RETURN QUERY
    SELECT ali.provider::VARCHAR, ali.email::VARCHAR, ali.is_primary
    FROM auth_linked_identities ali
    WHERE ali.user_id = p_user_id
    ORDER BY ali.is_primary DESC, ali.linked_at DESC;
END;
$$ LANGUAGE plpgsql;
