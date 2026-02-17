#!/usr/bin/env python
"""Show examples of improved content quality."""
import requests
import time

time.sleep(1)

# Generate a few previews to show the quality
for i in range(2):
    print(f"\n{'='*70}")
    print(f"EXAMPLE {i+1} - Generated Preview")
    print(f"{'='*70}")
    response = requests.get('http://localhost:5000/api/generate-preview', timeout=30)
    if response.status_code == 200:
        preview = response.json()
        content = preview.get('post', '')
        print(content)
    time.sleep(2)
