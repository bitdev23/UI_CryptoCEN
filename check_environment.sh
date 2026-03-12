#!/bin/bash
# Quick Start Script for ContentAI Pro
# Run this to check if your environment is ready for deployment

echo "🚀 ContentAI Pro - Environment Check"
echo "===================================="
echo ""

# Check Python version
echo "📦 Checking Python version..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    echo "✅ $PYTHON_VERSION"
else
    echo "❌ Python 3 not found. Please install Python 3.9 or higher."
    exit 1
fi

# Check if .env exists
echo ""
echo "🔐 Checking environment file..."
if [ -f .env ]; then
    echo "✅ .env file found"
    
    # Check key variables
    if grep -q "SUPABASE_URL=" .env && grep -q "SUPABASE_KEY=" .env; then
        echo "✅ Supabase credentials configured"
    else
        echo "⚠️  Supabase credentials missing in .env"
        echo "   Add SUPABASE_URL and SUPABASE_KEY"
    fi
    
    if grep -q "GOOGLE_API_KEY=" .env || grep -q "OPENAI_API_KEY=" .env || grep -q "ANTHROPIC_API_KEY=" .env; then
        echo "✅ AI provider configured"
    else
        echo "⚠️  No AI provider API key found"
        echo "   Add at least one: GOOGLE_API_KEY, OPENAI_API_KEY, or ANTHROPIC_API_KEY"
    fi
else
    echo "❌ .env file not found"
    echo "   Copy .env.example to .env and fill in your credentials"
    exit 1
fi

# Check if requirements are installed
echo ""
echo "📚 Checking Python dependencies..."
if python3 -c "import supabase" 2>/dev/null; then
    echo "✅ Supabase library installed"
else
    echo "⚠️  Supabase library not installed"
    echo "   Run: pip install -r requirements.txt"
fi

if python3 -c "import sentence_transformers" 2>/dev/null; then
    echo "✅ Sentence Transformers installed"
else
    echo "⚠️  Sentence Transformers not installed"
    echo "   Run: pip install -r requirements.txt"
fi

if python3 -c "import flask" 2>/dev/null; then
    echo "✅ Flask installed"
else
    echo "⚠️  Flask not installed"
    echo "   Run: pip install -r requirements.txt"
fi

# Check Docker (optional)
echo ""
echo "🐳 Checking Docker (optional for deployment)..."
if command -v docker &> /dev/null; then
    DOCKER_VERSION=$(docker --version)
    echo "✅ $DOCKER_VERSION"
    
    if command -v docker-compose &> /dev/null; then
        COMPOSE_VERSION=$(docker-compose --version)
        echo "✅ $COMPOSE_VERSION"
    else
        echo "⚠️  Docker Compose not found (needed for deployment)"
    fi
else
    echo "⚠️  Docker not found (needed for AWS deployment)"
    echo "   Install from: https://docs.docker.com/get-docker/"
fi

# Test Supabase connection
echo ""
echo "🔌 Testing Supabase connection..."
python3 << 'PYTHON_TEST'
import os
from dotenv import load_dotenv

load_dotenv()

url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_KEY')

if not url or not key:
    print("❌ Supabase credentials not found in .env")
    exit(1)

try:
    from supabase import create_client
    supabase = create_client(url, key)
    
    # Try a simple query
    result = supabase.table('plan_limits').select('plan').execute()
    
    if result.data:
        print(f"✅ Connected to Supabase ({len(result.data)} plans found)")
    else:
        print("⚠️  Connected but no data found. Did you run the schema SQL?")
        
except Exception as e:
    print(f"❌ Failed to connect to Supabase: {e}")
    exit(1)
PYTHON_TEST

# Summary
echo ""
echo "===================================="
echo "📋 Summary"
echo "===================================="
echo ""

# Check if all critical items are ready
READY=true

if [ ! -f .env ]; then
    READY=false
    echo "❌ Create .env file"
fi

if ! python3 -c "import supabase" 2>/dev/null; then
    READY=false
    echo "❌ Install dependencies: pip install -r requirements.txt"
fi

if $READY; then
    echo "✅ Environment ready!"
    echo ""
    echo "Next steps:"
    echo "1. Follow SUPABASE_SETUP_GUIDE.md to configure your database"
    echo "2. Follow MIGRATION_GUIDE.md to update app.py"
    echo "3. Run: python app.py"
    echo "4. Open: http://localhost:5050"
else
    echo "⚠️  Some items need attention (see above)"
    echo ""
    echo "Quick fix:"
    echo "1. Copy .env.example to .env"
    echo "2. Fill in your Supabase credentials"
    echo "3. Run: pip install -r requirements.txt"
    echo "4. Run this script again"
fi

echo ""
echo "For detailed guides, see:"
echo "  - IMPLEMENTATION_SUMMARY.md (start here)"
echo "  - SUPABASE_SETUP_GUIDE.md"
echo "  - MIGRATION_GUIDE.md"
echo "  - AWS_DEPLOYMENT_GUIDE.md"
