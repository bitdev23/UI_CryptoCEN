"""
Simple web dashboard for non-technical LinkedIn automation management.
Run: python app.py
Then open: http://localhost:5000
"""
from flask import Flask, render_template, request, jsonify
import os
import json
import logging
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False

# ============= CONFIGURATION HELPERS =============

def load_config():
    """Load configuration from .env file"""
    config = {
        'AI_PROVIDER': os.getenv('AI_PROVIDER', 'google'),
        'GOOGLE_API_KEY': os.getenv('GOOGLE_API_KEY', ''),
        'ANTHROPIC_API_KEY': os.getenv('ANTHROPIC_API_KEY', ''),
        'LINKEDIN_ACCESS_TOKEN': os.getenv('LINKEDIN_ACCESS_TOKEN', ''),
        'LINKEDIN_PERSON_ID': os.getenv('LINKEDIN_PERSON_ID', ''),
        'LINKEDIN_CLIENT_ID': os.getenv('LINKEDIN_CLIENT_ID', ''),
        'LINKEDIN_CLIENT_SECRET': os.getenv('LINKEDIN_CLIENT_SECRET', ''),
        'TEST_MODE': os.getenv('TEST_MODE', 'true').lower() in ('true', '1'),
        'CONTENT_PROFILE': os.getenv('CONTENT_PROFILE', 'arab_global_crypto'),
        'POST_TIME_HOUR': int(os.getenv('POST_TIME_HOUR', '11')),
        'POST_TIME_MINUTE': int(os.getenv('POST_TIME_MINUTE', '0')),
        'TIMEZONE': os.getenv('TIMEZONE', 'Asia/Kolkata'),
        'MIN_POST_LENGTH': int(os.getenv('MIN_POST_LENGTH', '150')),
        'MAX_POST_LENGTH': int(os.getenv('MAX_POST_LENGTH', '1000')),
        'ENABLE_MARKET_GROUNDING': os.getenv('ENABLE_MARKET_GROUNDING', 'true').lower() in ('true', '1'),
    }
    return config

def save_config(config):
    """Save configuration to .env file"""
    env_content = f"""AI_PROVIDER={config['AI_PROVIDER']}
GOOGLE_API_KEY={config['GOOGLE_API_KEY']}
ANTHROPIC_API_KEY={config['ANTHROPIC_API_KEY']}
LINKEDIN_ACCESS_TOKEN={config['LINKEDIN_ACCESS_TOKEN']}
LINKEDIN_PERSON_ID={config['LINKEDIN_PERSON_ID']}
LINKEDIN_CLIENT_ID={config['LINKEDIN_CLIENT_ID']}
LINKEDIN_CLIENT_SECRET={config['LINKEDIN_CLIENT_SECRET']}
TEST_MODE={'true' if config['TEST_MODE'] else 'false'}
CONTENT_PROFILE={config['CONTENT_PROFILE']}
POST_TIME_HOUR={config['POST_TIME_HOUR']}
POST_TIME_MINUTE={config['POST_TIME_MINUTE']}
TIMEZONE={config['TIMEZONE']}
MIN_POST_LENGTH={config['MIN_POST_LENGTH']}
MAX_POST_LENGTH={config['MAX_POST_LENGTH']}
ENABLE_MARKET_GROUNDING={'true' if config['ENABLE_MARKET_GROUNDING'] else 'false'}
"""
    with open('.env', 'w') as f:
        f.write(env_content)

# ============= ROUTES =============

@app.route('/')
def dashboard():
    """Main dashboard"""
    config = load_config()
    
    # Check if system is configured
    is_configured = bool(
        config['LINKEDIN_ACCESS_TOKEN'] and 
        config['LINKEDIN_PERSON_ID'] and
        (config['GOOGLE_API_KEY'] or config['ANTHROPIC_API_KEY'])
    )
    
    return render_template('dashboard.html', 
                         config=config, 
                         is_configured=is_configured,
                         current_time=datetime.now().isoformat())

@app.route('/api/config', methods=['GET'])
def get_config():
    """Get current configuration"""
    config = load_config()
    # Don't expose full API keys
    config['GOOGLE_API_KEY'] = '***' + config['GOOGLE_API_KEY'][-8:] if config['GOOGLE_API_KEY'] else ''
    config['ANTHROPIC_API_KEY'] = '***' + config['ANTHROPIC_API_KEY'][-8:] if config['ANTHROPIC_API_KEY'] else ''
    config['LINKEDIN_ACCESS_TOKEN'] = '***' + config['LINKEDIN_ACCESS_TOKEN'][-8:] if config['LINKEDIN_ACCESS_TOKEN'] else ''
    return jsonify(config)

@app.route('/api/config', methods=['POST'])
def update_config():
    """Update configuration"""
    try:
        data = request.get_json()
        config = load_config()
        
        # Only update if new values provided (preserve masked values)
        for key in data:
            if data[key] and not data[key].startswith('***'):
                config[key] = data[key]
        
        save_config(config)
        return jsonify({'success': True, 'message': 'Configuration saved!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

@app.route('/api/test-api', methods=['POST'])
def test_api():
    """Test AI API configuration"""
    try:
        from ai_provider import AIProvider
        ai = AIProvider()
        result = ai.generate("Say 'API is working' in 5 words", max_tokens=50)
        return jsonify({'success': True, 'message': f"API Working! Response: {result['text'][:100]}"})
    except Exception as e:
        return jsonify({'success': False, 'message': f"API Error: {str(e)}"})

@app.route('/api/test-linkedin', methods=['POST'])
def test_linkedin():
    """Test LinkedIn authentication"""
    try:
        from linkedin_poster import LinkedInPoster
        poster = LinkedInPoster(test_mode=True)
        return jsonify({'success': True, 'message': 'LinkedIn authentication test passed!'})
    except Exception as e:
        return jsonify({'success': False, 'message': f"LinkedIn Error: {str(e)}"})

@app.route('/api/generate-preview', methods=['GET'])
def generate_preview():
    """Generate a preview post"""
    try:
        from ai_provider import AIProvider
        import random
        import config as cfg
        
        ai = AIProvider()
        config_obj = load_config()
        profile_key = config_obj['CONTENT_PROFILE']
        profile = cfg.PROFILES.get(profile_key, cfg.PROFILES[cfg.DEFAULT_PROFILE])
        theme = random.choice(profile.get('content_themes', []))
        fmt = random.choice(cfg.POST_FORMATS)
        services = profile.get('company_info', {}).get('services', '')
        
        # Simple prompt for preview generation
        prompt = f"""Generate a LinkedIn post about: {theme}

Company context: {services}

Post format: {fmt}

Make it engaging, professional, and include relevant hashtags. Keep it between {config_obj['MIN_POST_LENGTH']} and {config_obj['MAX_POST_LENGTH']} characters."""

        result = ai.generate(prompt, max_tokens=500)
        content = result['text'].strip()
        
        # Generate some basic hashtags
        hashtags = ['#LinkedIn', '#Business', '#Innovation']
        if 'crypto' in theme.lower():
            hashtags.extend(['#Crypto', '#Blockchain', '#DigitalAssets'])
        if 'arab' in theme.lower():
            hashtags.extend(['#MiddleEast', '#UAE', '#Dubai'])
        
        return jsonify({
            'success': True,
            'post': content,
            'hashtags': hashtags,
            'theme': theme
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f"Generation Error: {str(e)}"})

@app.route('/api/posts', methods=['GET'])
def get_posts():
    """Get recently generated posts"""
    try:
        if os.path.exists('data/posts.json'):
            with open('data/posts.json', 'r') as f:
                posts = json.load(f)
                # Return last 10 posts
                return jsonify({'success': True, 'posts': posts[-10:][::-1]})
        return jsonify({'success': True, 'posts': []})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/scheduler/status', methods=['GET'])
def scheduler_status():
    """Get scheduler status"""
    config = load_config()
    return jsonify({
        'enabled': not config['TEST_MODE'],
        'schedule': f"{config['POST_TIME_HOUR']:02d}:{config['POST_TIME_MINUTE']:02d}",
        'timezone': config['TIMEZONE']
    })

@app.route('/api/post-now', methods=['POST'])
def post_now():
    """Generate and post immediately"""
    try:
        from ai_provider import AIProvider
        from linkedin_poster import LinkedInPoster
        from content_generator import ContentGenerator
        from rag_system import RAGStore
        import random
        import config as cfg
        
        config_obj = load_config()
        
        # Build RAG system
        rag = RAGStore(persist_dir="data/chroma_db")
        if not rag.is_built():
            # If not built, try to build it
            try:
                from pdf_processor import load_pdfs
                docs = load_pdfs("data/pdfs")
                rag.build_from_documents(docs)
                rag.persist()
            except Exception as e:
                logger.warning("Could not build RAG from PDFs: %s", e)
        
        # Generate content
        ai = AIProvider()
        cg = ContentGenerator(rag, ai)
        profile_key = config_obj['CONTENT_PROFILE']
        profile = cfg.PROFILES.get(profile_key, cfg.PROFILES[cfg.DEFAULT_PROFILE])
        theme = random.choice(profile.get('content_themes', []))
        fmt = random.choice(cfg.POST_FORMATS)
        services = profile.get('company_info', {}).get('services', '')
        query = f"{theme} {services}"
        
        post = cg.generate_post(theme, fmt, query)
        
        # Post to LinkedIn
        poster = LinkedInPoster(test_mode=config_obj['TEST_MODE'])
        result = poster.post(post['content'])
        
        # Save to posts history
        post_data = {
            'content': post['content'],
            'hashtags': post.get('hashtags', []),
            'theme': theme,
            'created_at': datetime.now().isoformat(),
            'posted': result['status'] == 'posted',
            'test_mode': config_obj['TEST_MODE']
        }
        
        # Load existing posts
        posts = []
        if os.path.exists('data/posts.json'):
            try:
                with open('data/posts.json', 'r') as f:
                    posts = json.load(f)
            except:
                posts = []
        
        posts.append(post_data)
        
        # Save back
        with open('data/posts.json', 'w') as f:
            json.dump(posts, f, indent=2)
        
        status_message = "Post published successfully!" if result['status'] == 'posted' else "Post preview generated (test mode)"
        
        return jsonify({
            'success': True,
            'message': status_message,
            'post': post_data,
            'result': result
        })
    except Exception as e:
        logger.exception("Failed to post now")
        return jsonify({'success': False, 'message': f"Posting failed: {str(e)}"})

if __name__ == '__main__':
    # Disable debug mode in production
    debug_mode = os.getenv('FLASK_ENV') != 'production'
    app.run(debug=debug_mode, port=int(os.getenv('PORT', 5000)), host='0.0.0.0')
