# Account Linking Implementation

## Overview

This implementation allows users to authenticate with **multiple authentication methods** on the same account:
- Sign up with email/password, then log in with Google OAuth
- Sign up with Google OAuth, then log in with email/password
- Link multiple OAuth providers (Google, GitHub, Discord, etc.)

All authentication methods are linked to a single user account with seamless switching.

---

## What Changed

### 1. Database Schema (New)
**File:** `database/account_linking_migration.sql`

- **Table:** `auth_linked_identities`
  - Tracks which authentication methods are linked to each user
  - Supports email/password, Google, GitHub, Discord, etc.
  - Maintains email and provider-specific user IDs
  - Marks which method is "primary"

- **Indexes:** 5 performance indexes for fast lookups by email, user_id, provider

- **Functions:**
  - `find_user_by_email()` - Find user across all linked identities
  - `is_identity_linked()` - Check if OAuth identity is already linked
  - `link_identity_to_user()` - Link new provider to existing account
  - `get_user_linked_providers()` - Get all linked methods for a user

### 2. Backend Functions (New)
**File:** `auth.py` - Added account linking functions

```python
# Find existing user by email
find_existing_user_by_email(email)

# Check if OAuth identity is already linked
check_if_identity_linked(provider, provider_user_id)

# Link OAuth to existing account
link_oauth_to_account(user_id, provider, provider_user_id, email)

# Get all linked providers for user
get_user_linked_providers(user_id)

# Handle OAuth flow with linking
handle_oauth_account_linking(oauth_user, provider)
```

### 3. API Endpoints (New)
**File:** `app.py` - Added 4 new endpoints

```
GET  /api/auth/linked-providers
     Returns all auth methods linked to current user

POST /api/auth/link-oauth
     Link a new OAuth identity to current user
     Body: { provider, provider_user_id, email }

GET  /api/auth/account-linking-status
     Check what auth methods are available to link

GET  /api/auth/user/profile
     Get user profile with auth method information
```

### 4. OAuth Flow (Updated)
**File:** `templates/auth_callback.html` - Simplified OAuth handling

- **Old behavior:** Rejected login if user signed up with different method
- **New behavior:** Seamlessly accepts login with any auth method
- Automatically handles linking in the backend
- Users are kept logged in on first authentication attempt

---

## Deployment Steps

### Step 1: Apply Database Migration

Go to Supabase SQL Editor and run:
```sql
-- Copy the full contents of database/account_linking_migration.sql
```

This creates:
- `auth_linked_identities` table
- 5 performance indexes
- 4 helper functions

**Time required:** < 1 second
**Breaking changes:** None - existing data is unaffected

### Step 2: Deploy Updated Code

```bash
git add auth.py app.py templates/auth_callback.html
git commit -m "feat: add account linking for multiple auth methods"
git push origin main
gcloud app deploy
```

### Step 3: Verify Account Linking

#### Test Email → OAuth (most common)
1. Sign up with email/password: `test@example.com`
2. Log out
3. Click "Sign in with Google"
4. Use same email: `test@example.com`
5. ✅ Should log in successfully (same account)

#### Test OAuth → Email
1. Sign up with Google using `test@example.com`
2. Log out
3. Sign in with email/password: `test@example.com`
4. ✅ Should log in successfully

#### Check Linked Methods
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  https://app.velank.io/api/auth/linked-providers
```

Response:
```json
{
  "success": true,
  "providers": [
    {"provider": "email", "email": "user@example.com", "is_primary": false},
    {"provider": "google", "email": "user@example.com", "is_primary": true}
  ]
}
```

---

## How It Works

### User Flow

#### Scenario 1: Email/Password → OAuth
```
1. User signs up with email/password
   └─ auth_provider set to 'email'
   └─ Entry created in auth_linked_identities (provider: 'email')

2. User later tries to log in with Google
   └─ OAuth callback receives Google user data
   └─ Checks if email already exists in system
   └─ FOUND: Email matches existing user from step 1
   └─ Automatically links Google identity:
      └─ INSERT into auth_linked_identities (provider: 'google', ...)
   └─ User is logged in successfully

3. Next time user logs in:
   └─ Can use either email/password OR Google OAuth
   └─ Both lead to the same account ✅
```

#### Scenario 2: OAuth → Email
```
1. User signs up with Google
   └─ auth_provider set to 'google'
   └─ Entry created in auth_linked_identities (provider: 'google')

2. User wants to set password for email login
   └─ User goes to settings/profile
   └─ Sets a password on their email
   └─ Backend automatically links email method
   └─ INSERT into auth_linked_identities (provider: 'email', ...)

3. User can now log in with either method ✅
```

### Technical Details

**Database Flow:**
```
User attempts login with Provider A
    ↓
verify_token() → get token from Supabase
    ↓
Extract user.id and user.email
    ↓
Check: Is this identity already linked?
    ↓
    YES → Return existing account ✅
    NO → Link new identity via link_oauth_to_account()
    ↓
User is authenticated with their main account
```

**Account Linking Rules:**
- ✅ Can have email + google
- ✅ Can have email + github  
- ✅ Can have google + github
- ✅ Can have email + google + github
- ❌ Cannot have 2 different "email" entries (email is unique per user)
- ❌ Cannot link same OAuth identity to 2 different accounts

---

## API Reference

### GET /api/auth/linked-providers
Get all authentication methods linked to current user.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response (200):**
```json
{
  "success": true,
  "providers": [
    {
      "provider": "email",
      "email": "user@example.com",
      "is_primary": true
    },
    {
      "provider": "google",
      "email": "user@example.com",
      "is_primary": false
    }
  ],
  "message": "Found 2 linked authentication method(s)"
}
```

---

### POST /api/auth/link-oauth
Manually link an OAuth provider to current account.

**Headers:**
```
Authorization: Bearer <access_token>
Content-Type: application/json
```

**Body:**
```json
{
  "provider": "google",
  "provider_user_id": "118365127234567890123",
  "email": "user@example.com"
}
```

**Response (200):**
```json
{
  "success": true,
  "message": "Linked google account successfully",
  "provider": "google"
}
```

**Response (400 - Already linked elsewhere):**
```json
{
  "success": false,
  "message": "This OAuth account is already linked to another user account",
  "provider": "google"
}
```

---

### GET /api/auth/account-linking-status
Check what auth methods can be linked to current account.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response (200):**
```json
{
  "success": true,
  "current_providers": ["email", "google"],
  "available_methods": {
    "email": false,
    "google": false,
    "github": true,
    "discord": true
  },
  "can_link": true,
  "message": "Account linking available"
}
```

---

### GET /api/auth/user/profile
Get authenticated user's profile with auth methods info.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response (200):**
```json
{
  "success": true,
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "auth_provider": "email",
    "email_confirmed_at": "2024-01-15T10:30:00Z",
    "created_at": "2024-01-15T10:30:00Z"
  },
  "linked_providers": [
    {"provider": "email", "email": "user@example.com", "is_primary": true},
    {"provider": "google", "email": "user@example.com", "is_primary": false}
  ],
  "auth_method": "email"
}
```

---

## Migration from Old System

If you had existing users that were blocked from logging in with different methods:

### Current Behavior (Before Account Linking)
```
User signed up with: email/password
User tries to login with: Google OAuth
Result: ❌ REJECTED - "Account exists with email/password"
```

### New Behavior (After Account Linking)
```
User signed up with: email/password
User tries to login with: Google OAuth
Result: ✅ ACCEPTED - Google identity auto-linked to existing account
```

**No action required** - The system automatically handles linking on next login attempt.

---

## Frontend Implementation (Optional)

If you want to show users their linked authentication methods:

```javascript
// Get user's linked providers
async function showLinkedMethods() {
  const token = sessionStorage.getItem('access_token');
  const res = await fetch('/api/auth/linked-providers', {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  const data = await res.json();
  
  console.log('Linked methods:', data.providers);
  // Show users: "You can sign in with: Email, Google"
}

// Check what methods can still be linked
async function checkAvailableLinking() {
  const token = sessionStorage.getItem('access_token');
  const res = await fetch('/api/auth/account-linking-status', {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  const data = await res.json();
  
  console.log('Can link:', data.available_methods);
  // Show "Link GitHub", "Link Discord" etc.
}
```

---

## Troubleshooting

### Issue: "Account is already linked to another user"
**Cause:** User tried to link an OAuth account that's already linked to a different user account.
**Solution:** Cannot merge accounts. User needs different OAuth account or different email.

### Issue: User can't login after linking
**Cause:** Token expired or session cleared
**Solution:** Clear browser cache/storage and log in again
```javascript
sessionStorage.clear();
localStorage.clear();
```

### Issue: Email appears in multiple accounts
**Cause:** Should not happen - database constraints prevent this
**Solution:** Contact support - likely a data corruption issue

---

## Security Considerations

✅ **Secure:**
- OAuth identities cannot be relinked to different accounts
- Email uniqueness enforced at database level
- All linking operations require authenticated user
- Provider user IDs validated against Supabase

⚠️ **Important:**
- Only users with same email can link accounts
- Compromised email = can link unauthorized providers
- Consider adding 2FA for sensitive accounts
- Audit log linking changes for compliance

---

## Performance Impact

Database queries for account linking:

| Operation | Index | Time | Impact |
|-----------|-------|------|--------|
| Find user by email | `idx_auth_linked_identities_email` | ~1ms | Minimal |
| Get linked providers | `idx_auth_linked_identities_user_id` | ~1ms | Minimal |
| Check provider linked | `idx_auth_linked_identities_provider_user_id` | <1ms | Negligible |
| Link new identity | Full table scan (unique constraint) | ~5ms | Low |

No significant performance impact expected.

---

## Testing Checklist

- [ ] Deployment migration succeeded
- [ ] User can sign up with email/password
- [ ] User can sign up with Google OAuth
- [ ] Email→OAuth linking works (same email)
- [ ] OAuth→Email linking works
- [ ] GET /api/auth/linked-providers returns correct data
- [ ] Cannot link same OAuth to 2 users
- [ ] Existing users get auto-linked on login
- [ ] All auth endpoints return 200/4xx as expected
- [ ] No errors in Sentry error tracking

---

## Rollback Plan

If account linking causes issues:

```bash
# Revert database
# 1. Delete newly created entries
DELETE FROM auth_linked_identities WHERE created_at > '2024-XX-XX 00:00:00';

# 2. Drop new table (careful!)
DROP TABLE auth_linked_identities;

# Revert code
git revert <commit_hash>
gcloud app deploy
```

---

## Future Enhancements

1. **Two-Factor Authentication:** Require 2FA before linking new methods
2. **Email Verification:** Verify email ownership before linking
3. **Unlinking Methods:** Allow users to unlink unused methods
4. **Primary Provider:** Let users choose which method is "primary"
5. **Login History:** Show user which devices logged in with which method
6. **Suspicious Activity Alerts:** Alert when new provider linked to account
7. **Social Login Merging UI:** Add settings page to manage linked accounts
8. **Account Recovery:** Use linked methods for account recovery

---

## Support

For issues, questions, or feature requests:
- Check error logs: `gcloud app logs read`
- Check Sentry: https://sentry.io (if configured)
- Run health check: `curl https://app.velank.io/api/auth/health`

