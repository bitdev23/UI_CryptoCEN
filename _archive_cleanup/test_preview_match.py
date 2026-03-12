#!/usr/bin/env python
"""Test that fix works: preview content matches posted content, and content quality is good."""
import requests
import time

time.sleep(3)

print("="*70)
print("VERIFICATION TEST: Preview vs Posted Content")
print("="*70)

# Test 1: Generate a preview
print("\n[TEST 1] Generating preview...")
response = requests.get('http://localhost:5000/api/generate-preview', timeout=30)
if response.status_code != 200:
    print(f"ERROR: Status {response.status_code}")
    exit(1)

preview_data = response.json()
preview_content = preview_data.get('post', '')
preview_hashtags = preview_data.get('hashtags', [])

print(f"✓ Preview generated ({len(preview_content)} chars)")
print(f"\nPreview content:\n{preview_content[:200]}...\n")

# Check for placeholder text
has_placeholder = any(x in preview_content for x in ['[Exchange Name]', '[Exchange]', '[Company Name]'])
if has_placeholder:
    print("✗ FAIL: Preview contains placeholder text like [Exchange Name]")
else:
    print("✓ PASS: No placeholder text in preview")

# Test 2: Post the preview
print("\n[TEST 2] Posting preview content...")
response = requests.post('http://localhost:5000/api/post-now', 
    json={
        'content': preview_content,
        'hashtags': preview_hashtags,
        'usePreview': True
    },
    timeout=30
)

if response.status_code != 200:
    print(f"ERROR: Status {response.status_code}")
    exit(1)

post_data = response.json()
if not post_data.get('success'):
    print(f"ERROR: {post_data.get('message')}")
    exit(1)

print(f"✓ Content posted successfully")
print(f"Message: {post_data.get('message')}")

posted_content = post_data.get('post', {}).get('content', '')

# Test 3: Verify posted content matches preview
print("\n[TEST 3] Verifying posted content matches preview...")
if posted_content == preview_content:
    print("✓ PASS: Posted content is IDENTICAL to preview")
else:
    print("✗ FAIL: Posted content differs from preview!")
    print(f"\nPreview ({len(preview_content)} chars):\n{preview_content[:150]}...")
    print(f"\nPosted ({len(posted_content)} chars):\n{posted_content[:150]}...")

# Test 4: Check content quality
print("\n[TEST 4] Checking content quality...")
quality_issues = []

if len(preview_content) < 100:
    quality_issues.append("Content too short (<100 chars)")

bad_phrases = [
    '[Exchange Name]', '[Company Name]', '[Exchange]', '[Name]',
    'Here\'s a LinkedIn post',  # Indicates generated preamble
    'generic', 'placeholder'
]

for phrase in bad_phrases:
    if phrase.lower() in preview_content.lower():
        quality_issues.append(f"Contains: '{phrase}'")

if quality_issues:
    print("✗ QUALITY ISSUES:")
    for issue in quality_issues:
        print(f"  - {issue}")
else:
    print("✓ PASS: Content looks high quality!")
    print(f"  - Content length: {len(preview_content)} chars")
    print(f"  - No placeholder text")
    print(f"  - No generic phrases")

# Summary
print("\n" + "="*70)
print("VERIFICATION COMPLETE")
print("="*70)
