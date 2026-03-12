#!/usr/bin/env python3
import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

from database.db_helper import get_db

try:
    db = get_db()
    print("✅ Supabase client initialized successfully!")
    print(f"✅ Connected to Supabase")
    print(f"   URL: {os.getenv('SUPABASE_URL')}")
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
