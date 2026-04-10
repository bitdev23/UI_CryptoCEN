#!/usr/bin/env python3
"""Smoke test: verify provider routing works for all task types."""

import json
from ai_provider import AIProvider
import os
from dotenv import load_dotenv

load_dotenv(override=True)

# Initialize provider
ai = AIProvider(
    os.getenv('AI_PROVIDER', 'deepseek'),
    api_keys={
        'GOOGLE_API_KEY': os.getenv('GOOGLE_API_KEY', ''),
        'OPENAI_API_KEY': os.getenv('OPENAI_API_KEY', ''),
        'ANTHROPIC_API_KEY': os.getenv('ANTHROPIC_API_KEY', ''),
        'DEEPSEEK_API_KEY': os.getenv('DEEPSEEK_API_KEY', ''),
        'XAI_API_KEY': os.getenv('XAI_API_KEY', ''),
    }
)

# Test generation with all task types
tasks = ['generate', 'rewrite', 'repurpose', 'style_clone', 'analysis', 'evaluate']

print('🚀 Testing AI Provider routing...\n')
success_count = 0

for task in tasks:
    try:
        prompt = f'Write a LinkedIn post about AI trends in 100 words.'
        result = ai.generate(prompt, max_tokens=200, task=task)
        
        print(f'✅ Task: {task}')
        print(f'   Provider: {result.get("provider")}')
        print(f'   Model: {result.get("model")}')
        usage = result.get("usage", {})
        print(f'   Tokens: {usage.get("prompt_tokens", 0)} prompt, {usage.get("completion_tokens", 0)} completion')
        print(f'   Latency: {result.get("latency_ms", "N/A")}ms')
        print(f'   Post preview: {result.get("text", "")[:80]}...\n')
        success_count += 1
    except Exception as e:
        print(f'❌ Task: {task} FAILED')
        print(f'   Error: {str(e)}\n')

print(f'\n✅ Result: {success_count}/{len(tasks)} tasks completed successfully!')
if success_count == len(tasks):
    print('🎯 All systems ready for production deployment!')
