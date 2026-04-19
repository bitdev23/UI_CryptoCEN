# Smart Password Detection for OAuth Users

## Problem Solved

**Scenario:** User signs up with Google OAuth, then tries to log in with email/password.

**Old Behavior:** ❌ Generic error "Invalid email or password" (confusing!)

**New Behavior:** ✅ Smart error that explains they need to use OAuth or reset password

---

## How It Works

When a user tries email/password login:

1. **Check fails** → Password doesn't work
2. **System detects** → Account exists but has no password (OAuth-only)
3. **Return smart error** → Tells user exactly what to do

```json
{
  "success": false,
  "message": "This account was created with Google and has no password. Please log in with Google or reset your password.",
  "error_type": "oauth_only_account",
  "action": "Use OAuth login or reset password",
  "can_reset_password": true
}
```

---

## Frontend Implementation

### Detect OAuth-Only Account Error

```javascript
async function handleLogin(email, password) {
  const response = await fetch('/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password })
  });
  
  const data = await response.json();
  
  if (!data.success && data.error_type === 'oauth_only_account') {
    // User has OAuth but no password
    showOAuthOnlyError(data);
    return;
  }
  
  if (data.success) {
    // Normal login success
    handleLoginSuccess(data);
  }
}
```

### Show User-Friendly Message

```javascript
function showOAuthOnlyError(errorData) {
  const dialog = document.getElementById('oauth-only-modal');
  
  dialog.querySelector('.message').innerHTML = `
    <h3>Account Created with OAuth</h3>
    <p>${errorData.message}</p>
    <div class="actions">
      <button onclick="redirectToOAuthLogin()">
        ✓ Log In with Google
      </button>
      <button onclick="requestPasswordReset()">
        ✓ Set Password (via Email)
      </button>
    </div>
  `;
  
  dialog.showModal();
}
```

### Request Password Reset

```javascript
async function requestPasswordReset() {
  const email = document.querySelector('input[name="email"]').value;
  
  const response = await fetch('/api/auth/password-reset', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email })
  });
  
  const data = await response.json();
  
  if (data.success) {
    showToast('✓ Password reset email sent. Check your inbox!');
    localStorage.setItem('reset_email_sent', email);
  } else {
    showToast('✗ Could not send reset email', 'error');
  }
}
```

---

## User Journey

### Scenario 1: OAuth Sign Up → Email Login Attempt

```
1. User creates account with Google
   └─ No password set
   
2. Forgets they used OAuth, tries email/password login
   └─ Email login fails (no password)
   
3. System responds:
   └─ Shows helpful error
   └─ Button 1: "Log in with Google" 
   └─ Button 2: "Set password via email"
   
4. User clicks "Set password"
   └─ Gets password reset email ✓
   └─ Sets password via link
   
5. Now they can use either:
   └─ Google OAuth
   └─ Email + new password ✓
```

### Scenario 2: Email Sign Up → Works as Before

```
1. User creates account with email/password ✓
2. Can log in normally ✓
3. Later can also link Google OAuth ✓
```

---

## Database Query (How It's Detected)

```sql
-- System queries: Does this email have both?
SELECT provider 
FROM auth_linked_identities 
WHERE email = 'user@example.com';

Results:
- Empty? → User doesn't exist
- ['google']? → OAuth-only (no password) → Show smart error
- ['email']? → Has password, login should work normally
- ['email', 'google']? → Both linked, works with either
```

---

## Error Response Format

```json
{
  "success": false,
  "message": "This account was created with Google and has no password. Please log in with Google or reset your password.",
  "error_type": "oauth_only_account",
  "action": "Use OAuth login or reset password",
  "can_reset_password": true
}
```

**When to show this:**
- `error_type` === `'oauth_only_account'` AND
- `can_reset_password` === `true`

---

## Testing Checklist

- [ ] Create account with Google OAuth (don't set password)
- [ ] Try logging in with email + any password
- [ ] Verify you get the smart error (not generic "Invalid password")
- [ ] Click "Set password" → Get email reset link
- [ ] Set new password → Can now log in with email ✓
- [ ] Switch back to Google OAuth login → Still works ✓

---

## Edge Cases Handled

| Situation | Behavior |
|-----------|----------|
| OAuth user tries email login | Smart error message |
| Email user tries to login | Normal error if password wrong |
| OAuth user clicks "Set Password" | Gets password reset email |
| User resets password | Can now use both methods |
| OAuth user has multiple providers | Shows all linked methods |
| OAuth account doesn't exist in system | Normal "Invalid email or password" |

---

## Backend Functions (For Reference)

**Function:** `check_user_oauth_only(email)`
- Returns: `(is_oauth_only: bool, providers_list: list)`
- Queries `auth_linked_identities` table
- Detects if user has email provider or only OAuth

**Triggered when:**
- User tries email/password login
- Login fails with invalid credentials
- System checks if account exists with OAuth but no password

---

## No Code Changes Needed on Frontend (Unless...)

You only need to update your login error handling if you want to:
1. Show a custom UI for OAuth-only accounts
2. Auto-redirect to OAuth login button
3. Show the linked providers the user has

Otherwise, the error message is already descriptive for users.

---

## Related Features

- Account Linking System (allows multiple auth methods on same account)
- Password Reset Flow (for setting password after OAuth signup)
- OAuth Sign Up (creates OAuth-only account initially)
- Email/Password Sign Up (creates email-only account initially)

