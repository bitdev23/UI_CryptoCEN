#!/usr/bin/env python3
import os
from dotenv import load_dotenv
load_dotenv()

print("AI_PROVIDER:", os.getenv('AI_PROVIDER'))
print("ANTHROPIC_API_KEY exists:", bool(os.getenv('ANTHROPIC_API_KEY')))
print("ANTHROPIC_API_KEY preview:", os.getenv('ANTHROPIC_API_KEY', '')[:20] + "...")

from ai_provider import AIProvider

try:
    ai = AIProvider()
    print(f"✅ AIProvider initialized with: {ai.provider}")
    
    # Try a quick generation
    result = ai.generate("Say: Hello from Claude", max_tokens=50)
    print(f"✅ Generation successful!")
    print(f"Response: {result['text']}")
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
