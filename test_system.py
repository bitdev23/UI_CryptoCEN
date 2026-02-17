#!/usr/bin/env python
"""Comprehensive system test for LinkedIn automation."""
import requests
import time
import sys

time.sleep(2)

tests_passed = 0
tests_total = 0

def test(name, condition, details=""):
    global tests_passed, tests_total
    tests_total += 1
    status = "PASS" if condition else "FAIL"
    symbol = "✓" if condition else "✗"
    print(f"{symbol} {name:30} {status:6} {details}")
    if condition:
        tests_passed += 1
    return condition

print("="*70)
print("LINKEDIN AUTOMATION SYSTEM TEST")
print("="*70)

# Test 1: Generate Preview
print("\n[1/4] Testing Generate Preview")
try:
    response = requests.get('http://localhost:5000/api/generate-preview', timeout=30)
    success = response.status_code == 200
    test("Generate Preview", success, f"Status {response.status_code}")
    if success:
        data = response.json()
        has_content = data.get('success') and data.get('post')
        test("  - Content Generated", has_content)
except Exception as e:
    test("Generate Preview", False, str(e))

# Test 2: Save Config as Live Mode
print("\n[2/4] Testing Config Save (Live Mode)")
try:
    config = {
        'TEST_MODE': False,
        'AI_PROVIDER': 'google',
        'POST_TIME_HOUR': 11,
        'POST_TIME_MINUTE': 0
    }
    response = requests.post('http://localhost:5000/api/config', json=config)
    success = response.status_code == 200
    test("Config Save", success, f"Status {response.status_code}")
    if success:
        data = response.json()
        test("  - Response Success", data.get('success'))
except Exception as e:
    test("Config Save", False, str(e))

# Test 3: Verify Config
print("\n[3/4] Testing Config Verification")
try:
    response = requests.get('http://localhost:5000/api/config')
    success = response.status_code == 200
    test("Get Config", success, f"Status {response.status_code}")
    if success:
        data = response.json()
        test_mode = data.get('TEST_MODE')
        test("  - TEST_MODE = False", test_mode == False, f"Current: {test_mode}")
except Exception as e:
    test("Get Config", False, str(e))

# Test 4: Post Now
print("\n[4/4] Testing Post Now (Live Mode)")
try:
    response = requests.post('http://localhost:5000/api/post-now', timeout=30)
    success = response.status_code == 200
    test("Post Now", success, f"Status {response.status_code}")
    if success:
        data = response.json()
        test("  - Response Success", data.get('success'))
        message = data.get('message', '')
        is_live = 'published successfully' in message.lower()
        test("  - Posted to LinkedIn", is_live, f"Message: {message[:50]}")
except Exception as e:
    test("Post Now", False, str(e))

# Summary
print("\n" + "="*70)
print(f"RESULTS: {tests_passed}/{tests_total} tests passed")
print("="*70)

if tests_passed == tests_total:
    print("\n✓ ALL TESTS PASSED - System is working correctly!")
    sys.exit(0)
else:
    print(f"\n✗ {tests_total - tests_passed} test(s) failed")
    sys.exit(1)
