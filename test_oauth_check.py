#!/usr/bin/env python3
"""
Test script to validate OAuth-only account detection
Run locally before deploying to production
"""

import os
import sys
import json
import requests
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(dotenv_path=BASE_DIR / '.env', override=False)

# Test the OAuth check logic
def test_oauth_check(email: str):
    """Test the check_user_oauth_only logic"""
    
    print(f"\n{'='*60}")
    print(f"Testing OAuth check for: {email}")
    print(f"{'='*60}")
    
    service_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY', '').strip()
    supabase_url = os.getenv('SUPABASE_URL', '').strip().rstrip('/')
    
    print(f"\n1. Checking config:")
    print(f"   Service key present: {bool(service_key)}")
    print(f"   URL: {supabase_url if supabase_url else 'MISSING'}")
    
    if not service_key or not supabase_url:
        print("\n❌ ERROR: Missing SUPABASE_SERVICE_ROLE_KEY or SUPABASE_URL in .env")
        return False, []
    
    # Call admin API
    admin_url = f"{supabase_url}/auth/v1/admin/users?email={email}"
    print(f"\n2. Calling Admin API:")
    print(f"   URL: {admin_url}")
    
    try:
        response = requests.get(
            admin_url,
            headers={
                'Authorization': f'Bearer {service_key}',
                'apikey': os.getenv('SUPABASE_ANON_KEY', service_key),
                'Content-Type': 'application/json'
            },
            timeout=5.0
        )
        
        print(f"   Status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"\n❌ API Error (status {response.status_code}):")
            print(f"   Response: {response.text[:500]}")
            return False, []
        
        data = response.json()
        print(f"\n3. Full API Response:")
        print(json.dumps(data, indent=2))
        
        users = data.get('users', [])
        print(f"\n4. Found {len(users)} user(s)")
        
        if not users:
            print(f"   ❌ No users found")
            return False, []
        
        # Find matching user
        user = None
        print(f"\n5. Looking for user matching: {email}")
        for i, u in enumerate(users):
            user_email = u.get('email', '')
            print(f"   User {i}: {user_email}")
            if user_email.lower() == email.lower():
                user = u
                print(f"   ✓ MATCH FOUND")
                break
        
        if not user:
            print(f"\n❌ No user found matching {email}")
            return False, []
        
        # Check identities
        identities = user.get('identities', []) or []
        print(f"\n6. User's identities:")
        print(json.dumps(identities, indent=2))
        
        # Extract providers
        providers = []
        has_email_provider = False
        
        if isinstance(identities, list):
            for identity in identities:
                if isinstance(identity, dict):
                    provider = identity.get('provider', '').lower()
                    if provider:
                        providers.append(provider)
                        if provider == 'email':
                            has_email_provider = True
        
        print(f"\n7. Analysis:")
        print(f"   Raw identities: {identities}")
        print(f"   Extracted providers: {providers}")
        print(f"   Has email provider: {has_email_provider}")
        
        is_oauth_only = len(providers) > 0 and not has_email_provider
        print(f"\n8. Result:")
        print(f"   is_oauth_only: {is_oauth_only}")
        print(f"   providers: {providers}")
        
        if is_oauth_only:
            print(f"\n✓ SUCCESS: Account is OAuth-only (can't login with password)")
        else:
            print(f"\n✗ Account can login with password or has no identities")
        
        return is_oauth_only, providers
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False, []


if __name__ == "__main__":
    # Test with the OAuth account
    print("LOCAL OAUTH CHECK TEST")
    print("Testing the OAuth-only detection logic")
    
    # Test with app.velank@gmail.com (should be OAuth-only)
    test_oauth_check("app.velank@gmail.com")
    
    # Also test with another account
    test_oauth_check("admin.arabglobal@gmail.com")
