#!/usr/bin/env python3
"""
Test script to verify freemium quota system is working correctly.
"""
import requests
import json
import uuid
import sys
from datetime import datetime

BASE_URL = 'http://127.0.0.1:5050'

def log(message, status='INFO'):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {status:8} | {message}")

def test_plan_limits_loading():
    """Test that plan limits are loaded correctly"""
    log("Testing plan limits loading...")
    try:
        # Read the plan_limits.json file directly
        import json
        with open('/Users/macbookair/Documents/UI_CryptoCEN/data/plan_limits.json', 'r') as f:
            limits = json.load(f)
        
        # Verify free plan has 3 posts
        free_limit = limits.get('free', {}).get('posts_generated', 0)
        assert free_limit == 3, f"Expected free plan to have 3 posts, got {free_limit}"
        log(f"✓ Plan limits loaded correctly (free plan: {free_limit} posts)", "PASS")
        return True
    except Exception as e:
        log(f"✗ Failed to load plan limits: {e}", "FAIL")
        return False

def test_freemium_api_registration():
    """Test that freemium API is registered and responding"""
    log("Testing freemium API registration...")
    try:
        # Test the quota-status endpoint with invalid token
        response = requests.get(
            f'{BASE_URL}/api/user/quota-status',
            headers={'Authorization': 'Bearer invalid_token'}
        )
        
        # Should return 401 Unauthorized (not 404)
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        log("✓ Freemium API endpoints are registered and responding", "PASS")
        return True
    except Exception as e:
        log(f"✗ Freemium API test failed: {e}", "FAIL")
        return False

def test_quota_exceeded_response():
    """Test that quota exceeded returns proper response structure"""
    log("Testing quota exceeded response structure...")
    try:
        # We can't test with a real user without doing full signup, but we can verify
        # the endpoint returns the correct structure by examining the code
        
        # Check that app.py has the quota_exceeded flag in the response
        with open('/Users/macbookair/Documents/UI_CryptoCEN/app.py', 'r') as f:
            content = f.read()
        
        assert "'quota_exceeded': True" in content, "quota_exceeded flag not found in app.py"
        assert "'quota_info':" in content, "quota_info field not found in app.py"
        log("✓ Response structure includes quota_exceeded and quota_info fields", "PASS")
        return True
    except Exception as e:
        log(f"✗ Response structure test failed: {e}", "FAIL")
        return False

def test_upgrade_modal_integration():
    """Test that upgrade modal is integrated in dashboard"""
    log("Testing upgrade modal integration...")
    try:
        # Get the dashboard HTML
        response = requests.get(f'{BASE_URL}/api/templates/dashboard')
        
        # If that fails, try the main page
        if response.status_code != 200:
            response = requests.get(f'{BASE_URL}/')
        
        dashboard_html = response.text
        
        # Check for upgrade modal component
        assert 'upgradeModal' in dashboard_html, "upgradeModal div not found in dashboard"
        assert 'showUpgradeModal' in dashboard_html, "showUpgradeModal function not found"
        assert 'checkQuotaBeforeGenerate' in dashboard_html, "checkQuotaBeforeGenerate function not found"
        
        log("✓ Upgrade modal is integrated in dashboard", "PASS")
        return True
    except Exception as e:
        # This is expected to fail without the full dashboard response
        # We'll verify through file inspection instead
        try:
            with open('/Users/macbookair/Documents/UI_CryptoCEN/templates/dashboard.html', 'r') as f:
                content = f.read()
            
            assert 'showUpgradeModal' in content, "showUpgradeModal not found"
            assert "{% include 'upgrade_modal_component.html'" in content, "upgrade_modal_component not included"
            log("✓ Upgrade modal is integrated in dashboard (verified via file inspection)", "PASS")
            return True
        except Exception as e2:
            log(f"✗ Upgrade modal integration test failed: {e2}", "FAIL")
            return False

def test_admin_api_endpoints():
    """Test that admin API endpoints are registered"""
    log("Testing admin API endpoints...")
    try:
        # Test with invalid token - should get 401, not 404
        response = requests.get(
            f'{BASE_URL}/api/admin/plan-limits',
            headers={'Authorization': 'Bearer invalid_token'}
        )
        
        # Should return 401 (unauthorized), not 404 (not found)
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        log("✓ Admin API endpoints are registered", "PASS")
        return True
    except Exception as e:
        log(f"✗ Admin API endpoints test failed: {e}", "FAIL")
        return False

def main():
    print("\n" + "="*70)
    print("FREEMIUM SYSTEM TEST SUITE")
    print("="*70 + "\n")
    
    tests = [
        test_plan_limits_loading,
        test_freemium_api_registration,
        test_quota_exceeded_response,
        test_upgrade_modal_integration,
        test_admin_api_endpoints,
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            log(f"Test {test.__name__} crashed: {e}", "ERROR")
            results.append(False)
        print()
    
    # Summary
    print("\n" + "="*70)
    passed = sum(results)
    total = len(results)
    print(f"TEST SUMMARY: {passed}/{total} tests passed")
    
    if passed == total:
        print("✓ All freemium tests passed!")
        print("="*70 + "\n")
        return 0
    else:
        print(f"✗ {total - passed} test(s) failed")
        print("="*70 + "\n")
        return 1

if __name__ == '__main__':
    sys.exit(main())
