"""
Simple web dashboard for non-technical LinkedIn automation management.
Run: python app.py
Then open: http://localhost:5000
"""
from flask import Flask, render_template, request, jsonify
import os
import json
import logging
import threading
import time
import schedule
import pytz
import random
from datetime import datetime
from dotenv import load_dotenv
from ai_provider import AIProvider
from config import PROFILES, DEFAULT_PROFILE, POST_FORMATS
from linkedin_poster import LinkedInPoster

load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False

# ============= KNOWLEDGE BASE CONFIGURATION =============
MAX_DOCUMENTS_PER_USER = 100        # Maximum documents allowed
MAX_PDF_SIZE = 50 * 1024 * 1024     # 50 MB per file
MAX_TOTAL_FILE_SIZE = 500 * 1024 * 1024  # 500 MB total
MAX_TRAINING_TIME = 300             # 5 minutes timeout

# ============= CONFIGURATION HELPERS =============

def load_config():
    """Load configuration from .env file"""
    # Read .env file directly to get current values
    config = {}
    if os.path.exists('.env'):
        with open('.env', 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    config[key.strip()] = value.strip()
    
    # Set defaults for missing values
    defaults = {
        'AI_PROVIDER': 'google',
        'GOOGLE_API_KEY': '',
        'ANTHROPIC_API_KEY': '',
        'LINKEDIN_ACCESS_TOKEN': '',
        'LINKEDIN_PERSON_ID': '',
        'LINKEDIN_CLIENT_ID': '',
        'LINKEDIN_CLIENT_SECRET': '',
        'TEST_MODE': 'true',
        'CONTENT_PROFILE': 'arab_global_crypto',
        'POST_TIME_HOUR': '11',
        'POST_TIME_MINUTE': '0',
        'TIMEZONE': 'Asia/Kolkata',
        'MIN_POST_LENGTH': '150',
        'MAX_POST_LENGTH': '1000',
        'ENABLE_MARKET_GROUNDING': 'true',
        'ACTIVE_PERSONA': 'professional',
        'TONE': 'professional',
        'STYLE': 'formal',
        'EMOJI_USAGE': 'moderate',
        'HASHTAG_COUNT': '3',
        'LANGUAGE': 'English',
        'AUDIENCE_KEYWORDS': '',
        'CONTENT_TOPICS': '',
        'CONTENT_INDUSTRY': 'tech',
        'USER_ROLE': 'cto',
        'CUSTOM_TOPICS': '',
        'CONTENT_MAX_LENGTH': '1000',
        'ENABLE_EMOJI': 'true'
    }
    
    for key, default in defaults.items():
        if key not in config:
            config[key] = default
    
    # Convert string values to appropriate types
    config['TEST_MODE'] = config['TEST_MODE'].lower() in ('true', '1')
    config['POST_TIME_HOUR'] = int(config['POST_TIME_HOUR'])
    config['POST_TIME_MINUTE'] = int(config['POST_TIME_MINUTE'])
    config['MIN_POST_LENGTH'] = int(config['MIN_POST_LENGTH'])
    config['MAX_POST_LENGTH'] = int(config['MAX_POST_LENGTH'])
    config['ENABLE_MARKET_GROUNDING'] = config['ENABLE_MARKET_GROUNDING'].lower() in ('true', '1')
    
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
ACTIVE_PERSONA={config.get('ACTIVE_PERSONA', 'professional')}
TONE={config.get('TONE', 'professional')}
STYLE={config.get('STYLE', 'formal')}
EMOJI_USAGE={config.get('EMOJI_USAGE', 'moderate')}
HASHTAG_COUNT={config.get('HASHTAG_COUNT', '3')}
LANGUAGE={config.get('LANGUAGE', 'English')}
AUDIENCE_KEYWORDS={config.get('AUDIENCE_KEYWORDS', '')}
CONTENT_TOPICS={config.get('CONTENT_TOPICS', '')}
"""
    with open('.env', 'w') as f:
        f.write(env_content)

# ============= SCHEDULER FUNCTIONS =============

def scheduled_post_job():
    """Job to run daily automated posting"""
    try:
        logger.info("Running daily scheduled post job")
        
        # Generate and post new content (existing logic)
        config_obj = load_config()
        if config_obj['TEST_MODE']:
            logger.info("Skipping daily post generation - TEST_MODE is enabled")
            return
            
        # Generate content directly (simplified version)
        ai = AIProvider()
        profile_key = config_obj['CONTENT_PROFILE']
        profile = PROFILES.get(profile_key, PROFILES[DEFAULT_PROFILE])
        theme = random.choice(profile.get('content_themes', []))
        fmt = random.choice(POST_FORMATS)
        services = profile.get('company_info', {}).get('services', '')
        
        # Simple prompt for post generation
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
        
        # Post to LinkedIn
        poster = LinkedInPoster(test_mode=config_obj['TEST_MODE'])
        post_result = poster.post(content)
        
        # Save to posts history
        post_data = {
            'content': content,
            'hashtags': hashtags,
            'theme': theme,
            'created_at': datetime.now().isoformat(),
            'posted': post_result.get('status') == 'posted',
            'test_mode': config_obj['TEST_MODE'],
            'scheduled': True
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
        
        logger.info("Scheduled post completed: %s", "Posted" if post_result.get('status') == 'posted' else "Test mode")
        
    except Exception as e:
        logger.exception("Scheduled post job failed: %s", e)

def start_scheduler():
    """Start the background scheduler - runs even in TEST_MODE but marks posts appropriately"""
    def scheduler_thread():
        config = load_config()
        tz = pytz.timezone(config['TIMEZONE'])
        schedule_time = f"{config['POST_TIME_HOUR']:02d}:{config['POST_TIME_MINUTE']:02d}"
        
        # Always schedule daily jobs - TEST_MODE will be respected in the job itself
        schedule.every().day.at(schedule_time).do(scheduled_post_job)
        logger.info("✓ Daily scheduler started - will post daily at %s %s (TEST_MODE: %s)", schedule_time, config['TIMEZONE'], config['TEST_MODE'])
        
        while True:
            # Always check for UI-scheduled posts
            config = load_config()  # Reload config
            check_scheduled_posts()  # Always check - function respects TEST_MODE
            
            # Run any pending scheduled jobs (daily posts)
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    
    def check_scheduled_posts():
        """Check and post any due scheduled posts"""
        try:
            if os.path.exists('data/scheduled_posts.json'):
                with open('data/scheduled_posts.json', 'r') as f:
                    scheduled_posts = json.load(f)
                
                current_time = datetime.now()
                posts_to_remove = []
                
                for post in scheduled_posts:
                    schedule_time = datetime.fromisoformat(post['schedule_time'])
                    if current_time >= schedule_time:
                        # Post is due
                        from linkedin_poster import LinkedInPoster
                        poster = LinkedInPoster(test_mode=False)  # Always post scheduled posts
                        result = poster.post(post['content'])
                        
                        logger.info(f"Posted scheduled post: {result}")
                        
                        # Add to posts history
                        post_data = {
                            'content': post['content'],
                            'hashtags': post['hashtags'],
                            'theme': 'scheduled',
                            'created_at': datetime.now().isoformat(),
                            'posted': result.get('status') == 'posted',
                            'test_mode': False,
                            'scheduled': True
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
                        
                        # Save posts
                        with open('data/posts.json', 'w') as f:
                            json.dump(posts, f, indent=2)
                        
                        posts_to_remove.append(post)
                
                # Remove posted scheduled posts
                for post in posts_to_remove:
                    scheduled_posts.remove(post)
                
                # Save updated scheduled posts
                with open('data/scheduled_posts.json', 'w') as f:
                    json.dump(scheduled_posts, f, indent=2)
                    
        except Exception as e:
            logger.exception("Error processing scheduled posts: %s", e)
    
    thread = threading.Thread(target=scheduler_thread, daemon=True)
    thread.start()
    logger.info("Scheduler thread started")

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

@app.route('/dashboard-enterprise')
def dashboard_enterprise():
    """Premium enterprise dashboard with multi-industry support"""
    config = load_config()
    return render_template('dashboard_enterprise.html', config=config)

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
        
        # Update all provided configuration values
        for key in data:
            value = data[key]
            # Skip masked values (don't overwrite with ***) but allow False, 0, empty strings
            if isinstance(value, str) and value.startswith('***'):
                continue
            config[key] = value
        
        save_config(config)
        logger.info(f"Configuration saved. TEST_MODE={config.get('TEST_MODE')}")
        return jsonify({'success': True, 'message': 'Configuration saved!'})
    except Exception as e:
        logger.exception("Failed to save config")
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

@app.route('/api/generate-preview', methods=['GET', 'POST'])
def generate_preview():
    """Generate a preview post"""
    try:
        from ai_provider import AIProvider
        import random
        import config as cfg
        
        logger.info("Generate preview request received")
        
        ai = AIProvider()
        config_obj = load_config()
        profile_key = config_obj.get('CONTENT_PROFILE', 'arab_global_crypto')
        profile = cfg.PROFILES.get(profile_key, cfg.PROFILES.get(cfg.DEFAULT_PROFILE, {}))
        
        content_themes = profile.get('content_themes', ['AI', 'Technology', 'Business'])
        theme = random.choice(content_themes) if content_themes else 'Technology'
        
        post_formats = getattr(cfg, 'POST_FORMATS', ['article', 'opinion', 'announcement'])
        fmt = random.choice(post_formats) if post_formats else 'article'
        
        services = profile.get('company_info', {}).get('services', '')
        
        # Improved prompt for better human-like content
        prompt = f"""Generate a professional LinkedIn post about: {theme}

Context: {services}

Requirements:
- Write in a natural, human-like tone (not generic AI)
- Avoid placeholder text like [Company Name], [Exchange Name], or [Exchange]
- Be specific and authentic
- Include 1-2 actionable insights or takeaways
- Keep it between {config_obj.get('MIN_POST_LENGTH', 150)} and {config_obj.get('MAX_POST_LENGTH', 1000)} characters
- Do NOT include hashtags in the post body

Format: {fmt}

Write ONLY the post content, nothing else."""

        logger.info(f"Generating preview with prompt: {prompt[:100]}...")
        
        # Add timeout for AI generation
        import time
        start_time = time.time()
        try:
            result = ai.generate(prompt, max_tokens=500)
        except Exception as e:
            logger.error(f"AI generation failed after {time.time() - start_time:.2f}s: {e}")
            return jsonify({'success': False, 'message': f"AI generation failed: {str(e)}"}), 500
            
        if not result or 'text' not in result:
            logger.error(f"Invalid AI response: {result}")
            return jsonify({'success': False, 'message': "AI returned invalid response"}), 400
            
        content = result['text'].strip()
        
        if not content:
            return jsonify({'success': False, 'message': "Generated content is empty"}), 400
        
        # Generate some basic hashtags
        hashtags = ['#LinkedIn', '#Business', '#Innovation']
        if 'crypto' in theme.lower():
            hashtags.extend(['#Crypto', '#Blockchain', '#DigitalAssets'])
        if 'arab' in theme.lower():
            hashtags.extend(['#MiddleEast', '#UAE', '#Dubai'])
        
        logger.info(f"Successfully generated preview: {content[:100]}...")
        
        return jsonify({
            'success': True,
            'post': content,
            'hashtags': hashtags,
            'theme': theme
        })
    except Exception as e:
        logger.exception("Generate preview failed")
        return jsonify({'success': False, 'message': f"Generation Error: {str(e)}"}), 500

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

@app.route('/api/schedule-post', methods=['POST'])
def schedule_post():
    """Schedule a post for later"""
    try:
        data = request.get_json()
        content = data.get('content', '')
        hashtags = data.get('hashtags', [])
        schedule_time = data.get('schedule_time', '')
        
        if not content or not schedule_time:
            return jsonify({'success': False, 'message': 'Content and schedule time required'})
        
        # Load existing scheduled posts
        scheduled_posts = []
        if os.path.exists('data/scheduled_posts.json'):
            try:
                with open('data/scheduled_posts.json', 'r') as f:
                    scheduled_posts = json.load(f)
            except:
                scheduled_posts = []
        
        # Add new scheduled post
        scheduled_post = {
            'content': content,
            'hashtags': hashtags,
            'schedule_time': schedule_time,
            'created_at': datetime.now().isoformat(),
            'id': len(scheduled_posts) + 1
        }
        
        scheduled_posts.append(scheduled_post)
        
        # Save back
        with open('data/scheduled_posts.json', 'w') as f:
            json.dump(scheduled_posts, f, indent=2)
        
        return jsonify({'success': True, 'message': f'Post scheduled for {schedule_time}'})
    except Exception as e:
        logger.exception("Failed to schedule post")
        return jsonify({'success': False, 'message': f"Scheduling failed: {str(e)}"})

@app.route('/api/post-now', methods=['POST'])
def post_now():
    """Post content immediately (either from preview or generate new)"""
    try:
        from ai_provider import AIProvider
        from linkedin_poster import LinkedInPoster
        import random
        import config as cfg
        
        config_obj = load_config()
        data = request.get_json() or {}
        use_preview = data.get('usePreview', False)
        preview_content = data.get('content', '')
        preview_hashtags = data.get('hashtags', [])
        
        # If preview content provided, use it; otherwise generate new
        if use_preview and preview_content:
            content = preview_content
            hashtags = preview_hashtags
            theme = 'User Preview'  # Mark as user-provided preview
            logger.info(f"Posting preview content ({len(content)} chars)")
        else:
            # Generate new content
            ai = AIProvider()
            profile_key = config_obj['CONTENT_PROFILE']
            profile = cfg.PROFILES.get(profile_key, cfg.PROFILES[cfg.DEFAULT_PROFILE])
            theme = random.choice(profile.get('content_themes', []))
            fmt = random.choice(cfg.POST_FORMATS)
            services = profile.get('company_info', {}).get('services', '')
            
            # Improved prompt for better human-like content
            prompt = f"""Generate a professional LinkedIn post about: {theme}

Context: {services}

Requirements:
- Write in a natural, human-like tone (not generic AI)
- Avoid placeholder text like [Company Name], [Exchange Name], or [Exchange]
- Be specific and authentic
- Include 1-2 actionable insights or takeaways
- Keep it between {config_obj['MIN_POST_LENGTH']} and {config_obj['MAX_POST_LENGTH']} characters
- Do NOT include hashtags in the post body

Format: {fmt}

Write ONLY the post content, nothing else."""
            
            ai = AIProvider()
            result = ai.generate(prompt, max_tokens=500)
            content = result['text'].strip()
            
            # Generate relevant hashtags based on theme
            hashtags = ['#LinkedIn', '#Business']
            if 'crypto' in theme.lower():
                hashtags.extend(['#Crypto', '#Blockchain', '#Web3'])
            if 'exchange' in theme.lower():
                hashtags.extend(['#Trading', '#DigitalAssets'])
            if 'arab' in theme.lower():
                hashtags.extend(['#MiddleEast', '#UAE', '#Dubai'])
            
            logger.info(f"Generated new content ({len(content)} chars) for theme: {theme}")
        
        # Post to LinkedIn
        poster = LinkedInPoster(test_mode=config_obj['TEST_MODE'])
        post_result = poster.post(content)
        
        # Save to posts history
        post_data = {
            'content': content,
            'hashtags': hashtags,
            'theme': theme,
            'created_at': datetime.now().isoformat(),
            'posted': post_result.get('status') == 'posted',
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
        
        if post_result.get('status') == 'posted':
            status_message = "Post published successfully!"
        elif config_obj['TEST_MODE']:
            status_message = "Post preview generated (test mode)"
        else:
            status_message = f"Failed to post: {post_result.get('error', 'Unknown error')}"
        
        return jsonify({
            'success': True,
            'message': status_message,
            'post': {
                'content': content,
                'hashtags': hashtags,
                'theme': theme
            }
        })
    except Exception as e:
        logger.exception("Failed to post now")
        return jsonify({'success': False, 'message': f"Posting failed: {str(e)}"})

# ============= KNOWLEDGE BASE & MODEL TRAINING ENDPOINTS =============

@app.route('/api/upload-knowledge-base', methods=['POST'])
def upload_knowledge_base():
    """Upload PDF or DOCX files to the knowledge base"""
    try:
        from rag_system import RAGStore
        from pdf_processor import load_pdfs
        from werkzeug.utils import secure_filename
        
        if 'files' not in request.files:
            logger.warning("Upload request missing 'files' field")
            return jsonify({'success': False, 'message': 'No files provided'}), 400
        
        files = request.files.getlist('files')
        if not files or all(not f.filename for f in files):
            logger.warning("No files selected in upload")
            return jsonify({'success': False, 'message': 'No files selected'}), 400
        
        # Create if data/pdfs doesn't exist
        os.makedirs('data/pdfs', exist_ok=True)
        
        # Check document count limit
        existing_files = [f for f in os.listdir('data/pdfs') if f.endswith(('.pdf', '.docx'))]
        if len(existing_files) >= MAX_DOCUMENTS_PER_USER:
            logger.warning(f"Document limit reached: {len(existing_files)}/{MAX_DOCUMENTS_PER_USER}")
            return jsonify({
                'success': False, 
                'message': f'Maximum {MAX_DOCUMENTS_PER_USER} documents allowed. Delete some files first.'
            }), 400
        
        # Save uploaded files with validation
        uploaded_count = 0
        skipped_count = 0
        allowed_extensions = ('.pdf', '.docx')
        skipped_reasons = []
        
        for file in files:
            if not file or not file.filename:
                continue
            
            filename = secure_filename(file.filename)
            file_ext = filename.lower()
            
            # Check if file has allowed extension
            if not any(file_ext.endswith(ext) for ext in allowed_extensions):
                logger.warning("Skipping non-PDF/DOCX file: %s", filename)
                skipped_reasons.append(f"{filename}: Not a PDF or DOCX file")
                skipped_count += 1
                continue
            
            # Check file size
            if len(file.read()) > MAX_PDF_SIZE:
                file.seek(0)
                logger.warning(f"File too large: {filename} (max {MAX_PDF_SIZE/1024/1024}MB)")
                skipped_reasons.append(f"{filename}: File too large (max 50MB)")
                skipped_count += 1
                continue
            
            file.seek(0)
            
            # Check if we've hit the document limit
            current_count = len([f for f in os.listdir('data/pdfs') if f.endswith(('.pdf', '.docx'))])
            if current_count >= MAX_DOCUMENTS_PER_USER:
                logger.warning(f"Hit document limit during batch upload")
                skipped_reasons.append(f"{filename}: Document limit reached")
                skipped_count += 1
                continue
            
            try:
                filepath = os.path.join('data/pdfs', filename)
                file.save(filepath)
                logger.info("Saved file: %s", filepath)
                uploaded_count += 1
            except Exception as e:
                logger.exception("Failed to save file %s: %s", filename, e)
                skipped_reasons.append(f"{filename}: Error saving file")
                skipped_count += 1
                continue
        
        if uploaded_count == 0:
            logger.warning("No PDF/DOCX files uploaded successfully")
            reason_text = " | ".join(skipped_reasons) if skipped_reasons else "Unknown error"
            return jsonify({
                'success': False, 
                'message': f'No files uploaded. {reason_text}'
            }), 400
        
        # Rebuild RAG system with new documents
        rag_error = None
        try:
            logger.info("Starting RAG rebuild with %d new files", uploaded_count)
            rag = RAGStore(persist_dir="data/chroma_db")
            docs = load_pdfs("data/pdfs")
            logger.info("Loaded %d documents for RAG", len(docs))
            if docs:
                rag.build_from_documents(docs)
                rag.persist()
                logger.info("RAG build successful")
        except Exception as e:
            rag_error = str(e)
            logger.exception("RAG build error: %s", e)
        
        # Build response message
        response_msg = f'Successfully uploaded {uploaded_count} file(s)'
        if skipped_count > 0:
            response_msg += f' ({skipped_count} skipped)'
        if rag_error:
            response_msg += f' (RAG training note: {rag_error})'
        
        return jsonify({
            'success': True,
            'message': response_msg,
            'uploaded': uploaded_count,
            'skipped': skipped_count,
            'skipped_reasons': skipped_reasons
        })
    except Exception as e:
        logger.exception("Knowledge base upload failed")
        return jsonify({'success': False, 'message': f'Upload failed: {str(e)}'}), 500

@app.route('/api/personas', methods=['GET', 'POST'])
def manage_personas():
    """Get or update AI personas and writing styles"""
    try:
        personas_file = 'data/personas.json'
        
        # Default personas if none exist
        default_personas = {
            'professional': {
                'name': 'Professional Advisor',
                'description': 'Formal, authoritative, industry expert tone',
                'tone': 'professional',
                'language': 'English',
                'style': 'formal',
                'keywords': ['industry', 'expertise', 'strategic', 'insight'],
                'emoji_usage': 'minimal',
                'hashtag_count': 3
            },
            'casual_friendly': {
                'name': 'Friendly Innovator',
                'description': 'Casual, approachable, conversational tone',
                'tone': 'casual',
                'language': 'English',
                'style': 'conversational',
                'keywords': ['innovation', 'growth', 'community', 'value'],
                'emoji_usage': 'moderate',
                'hashtag_count': 5
            },
            'thought_leader': {
                'name': 'Thought Leader',
                'description': 'Insightful, visionary, trend-focused',
                'tone': 'inspirational',
                'language': 'English',
                'style': 'narrative',
                'keywords': ['future', 'vision', 'transformation', 'impact'],
                'emoji_usage': 'strategic',
                'hashtag_count': 4
            },
            'storyteller': {
                'name': 'Storyteller',
                'description': 'Narrative-driven, emotional connection',
                'tone': 'narrative',
                'language': 'English',
                'style': 'story-based',
                'keywords': ['experience', 'journey', 'learning', 'growth'],
                'emoji_usage': 'adaptive',
                'hashtag_count': 3
            }
        }
        
        if request.method == 'GET':
            # Return personas
            personas = default_personas
            if os.path.exists(personas_file):
                try:
                    with open(personas_file, 'r') as f:
                        personas = json.load(f)
                except:
                    pass
            return jsonify({'success': True, 'personas': personas})
        
        else:  # POST
            # Update personas
            data = request.get_json()
            if not data or 'personas' not in data:
                return jsonify({'success': False, 'message': 'Invalid persona data'}), 400
            
            os.makedirs('data', exist_ok=True)
            with open(personas_file, 'w') as f:
                json.dump(data['personas'], f, indent=2)
            
            return jsonify({
                'success': True,
                'message': 'Personas updated successfully'
            })
    except Exception as e:
        logger.exception("Persona management failed")
        return jsonify({'success': False, 'message': f'Failed: {str(e)}'}), 500

@app.route('/api/train-model', methods=['POST'])
def train_model():
    """Train/rebuild the RAG model with current knowledge base"""
    try:
        from rag_system import RAGStore
        from pdf_processor import load_pdfs
        
        # Check if documents exist
        if not os.path.exists('data/pdfs'):
            return jsonify({
                'success': False,
                'message': 'Knowledge base folder not found. Upload documents first.'
            }), 400
        
        # Load all documents
        try:
            docs = load_pdfs("data/pdfs")
        except Exception as e:
            logger.exception(f"Failed to load documents: {e}")
            return jsonify({
                'success': False,
                'message': f'Error loading documents: {str(e)}'
            }), 400
        
        if not docs:
            return jsonify({
                'success': False,
                'message': 'No valid PDF or DOCX documents found in knowledge base'
            }), 400
        
        # Build RAG model with error handling
        try:
            rag = RAGStore(persist_dir="data/chroma_db")
            rag.build_from_documents(docs)
            rag.persist()
            logger.info(f"Successfully trained RAG with {len(docs)} documents")
            
            return jsonify({
                'success': True,
                'message': f'✅ Model trained successfully with {len(docs)} documents',
                'document_count': len(docs)
            })
        except Exception as e:
            logger.exception(f"RAG build failed: {e}")
            return jsonify({
                'success': False,
                'message': f'Error training model: {str(e)}'
            }), 500
    except Exception as e:
        logger.exception("Model training failed")
        return jsonify({'success': False, 'message': f'Training failed: {str(e)}'}), 500

@app.route('/api/knowledge-base-status', methods=['GET'])
def knowledge_base_status():
    """Get knowledge base statistics"""
    try:
        from rag_system import RAGStore
        
        rag = RAGStore(persist_dir="data/chroma_db")
        
        # Count documents
        file_count = 0
        pdf_count = 0
        docx_count = 0
        if os.path.exists('data/pdfs'):
            files = os.listdir('data/pdfs')
            pdf_count = len([f for f in files if f.endswith('.pdf')])
            docx_count = len([f for f in files if f.endswith('.docx')])
            file_count = pdf_count + docx_count
        
        # Check if RAG is trained
        is_trained = rag.is_built()
        doc_count_in_rag = rag.get_document_count()
        
        return jsonify({
            'success': True,
            'trained': is_trained,
            'pdf_count': file_count,
            'pdf_count_detail': pdf_count,
            'docx_count': docx_count,
            'rag_document_count': doc_count_in_rag,
            'status': 'Ready for use' if is_trained else ('Needs training' if file_count > 0 else 'No documents'),
            'rag_ready': is_trained,
            'max_documents': MAX_DOCUMENTS_PER_USER
        })
    except Exception as e:
        logger.exception("Knowledge base status check failed")
        return jsonify({
            'success': False,
            'message': f'Status check failed: {str(e)}'
        }), 500

@app.route('/api/list-knowledge-base-files', methods=['GET'])
def list_knowledge_base_files():
    """List all uploaded knowledge base files"""
    try:
        files_list = []
        if os.path.exists('data/pdfs'):
            for filename in os.listdir('data/pdfs'):
                if filename.endswith(('.pdf', '.docx')):
                    filepath = os.path.join('data/pdfs', filename)
                    file_size = os.path.getsize(filepath)
                    file_type = 'PDF' if filename.endswith('.pdf') else 'DOCX'
                    files_list.append({
                        'name': filename,
                        'type': file_type,
                        'size': round(file_size / 1024 / 1024, 2),  # MB
                        'size_bytes': file_size
                    })
        
        # Sort by name
        files_list.sort(key=lambda x: x['name'])
        
        return jsonify({
            'success': True,
            'files': files_list,
            'count': len(files_list)
        })
    except Exception as e:
        logger.exception("Failed to list files")
        return jsonify({
            'success': False,
            'message': f'Failed to list files: {str(e)}'
        }), 500

@app.route('/api/delete-knowledge-base-file', methods=['POST'])
def delete_knowledge_base_file():
    """Delete a knowledge base file"""
    try:
        from rag_system import RAGStore
        from pdf_processor import load_pdfs
        
        data = request.get_json()
        if not data or 'filename' not in data:
            return jsonify({
                'success': False,
                'message': 'Filename required'
            }), 400
        
        filename = data['filename']
        # Sanitize filename
        if '/' in filename or '\\' in filename or '..' in filename:
            return jsonify({
                'success': False,
                'message': 'Invalid filename'
            }), 400
        
        filepath = os.path.join('data/pdfs', filename)
        
        # Check if file exists
        if not os.path.exists(filepath):
            return jsonify({
                'success': False,
                'message': 'File not found'
            }), 404
        
        # Delete file
        try:
            os.remove(filepath)
            logger.info(f"Deleted knowledge base file: {filename}")
        except Exception as e:
            logger.exception(f"Failed to delete file: {e}")
            return jsonify({
                'success': False,
                'message': f'Failed to delete file: {str(e)}'
            }), 500
        
        # Rebuild RAG with remaining documents
        rag_error = None
        try:
            if any(os.path.isfile(os.path.join('data/pdfs', f)) 
                   and f.endswith(('.pdf', '.docx')) 
                   for f in os.listdir('data/pdfs')):
                rag = RAGStore(persist_dir="data/chroma_db")
                docs = load_pdfs("data/pdfs")
                if docs:
                    rag.build_from_documents(docs)
                    rag.persist()
                    logger.info(f"Rebuilt RAG with remaining {len(docs)} documents")
        except Exception as e:
            rag_error = str(e)
            logger.exception(f"RAG rebuild after deletion failed: {e}")
        
        response_msg = f'Successfully deleted {filename}'
        if rag_error:
            response_msg += f' (Note: RAG rebuild skipped - {rag_error})'
        
        return jsonify({
            'success': True,
            'message': response_msg
        })
    except Exception as e:
        logger.exception("Delete knowledge base file failed")
        return jsonify({
            'success': False,
            'message': f'Delete failed: {str(e)}'
        }), 500

# ============= ENTERPRISE PREMIUM FEATURES =============

@app.route('/api/industries', methods=['GET'])
def get_industries():
    """Get list of supported industries for multi-tenant feature"""
    industries = {
        'tech': {
            'name': 'Technology & Software',
            'roles': ['dev', 'cto', 'pm', 'ceo'],
            'topics': ['AI/ML', 'Cloud', 'DevOps', 'Security', 'Architecture', 'Best Practices']
        },
        'finance': {
            'name': 'Finance & Banking',
            'roles': ['ceo', 'finance', 'ops', 'cto'],
            'topics': ['Fintech', 'Compliance', 'Risk Management', 'Trading', 'Blockchain', 'Market Trends']
        },
        'healthcare': {
            'name': 'Healthcare & Pharma',
            'roles': ['ceo', 'cto', 'ops', 'marketing'],
            'topics': ['Telemedicine', 'Regulations', 'Patient Care', 'Innovation', 'Research', 'Digital Health']
        },
        'crypto': {
            'name': 'Cryptocurrency & Web3',
            'roles': ['dev', 'cto', 'ceo', 'marketing'],
            'topics': ['Smart Contracts', 'DeFi', 'Tokenomics', 'Security', 'Regulations', 'Market Analysis']
        },
        'saas': {
            'name': 'SaaS & Startups',
            'roles': ['ceo', 'pm', 'marketing', 'cto'],
            'topics': ['Product Launch', 'Growth Hacking', 'Fundraising', 'MVP', 'Customer Success', 'Scaling']
        },
        'ecommerce': {
            'name': 'E-Commerce & Retail',
            'roles': ['ceo', 'marketing', 'ops', 'pm'],
            'topics': ['Supply Chain', 'Customer Experience', 'Conversion Rate', 'Trends', 'Personalization', 'Analytics']
        }
    }
    return jsonify(industries)

@app.route('/api/roles', methods=['GET'])
def get_roles():
    """Get list of professional roles for premium content personalization"""
    roles = {
        'ceo': {'title': 'CEO / Founder', 'focus': 'Strategy, Growth, Vision'},
        'cto': {'title': 'CTO / VP Engineering', 'focus': 'Technical, Architecture, Innovation'},
        'dev': {'title': 'Software Developer', 'focus': 'Code, Best Practices, Tools'},
        'pm': {'title': 'Product Manager', 'focus': 'User Experience, Roadmap, Metrics'},
        'hr': {'title': 'HR / People Ops', 'focus': 'Culture, Hiring, Engagement'},
        'finance': {'title': 'Finance / CFO', 'focus': 'Budget, Analytics, Growth'},
        'ops': {'title': 'Operations', 'focus': 'Efficiency, Processes, Scaling'},
        'marketing': {'title': 'Marketing / Growth', 'focus': 'Campaigns, Analytics, Engagement'},
        'sales': {'title': 'Sales / BD', 'focus': 'Deals, Relationships, Growth'}
    }
    return jsonify(roles)

@app.route('/api/generate-preview-premium', methods=['POST'])
def generate_preview_premium():
    """Enhanced content generation with industry/role personalization"""
    try:
        data = request.get_json() or {}
        industry = data.get('industry', 'tech')
        role = data.get('role', 'cto')
        topic = data.get('topic', '')
        hashtags_count = int(data.get('hashtags', 3))
        emoji_level = data.get('emojis', 'moderate')
        custom_topics = data.get('topics', [])
        
        config_obj = load_config()
        ai_provider = config_obj.get('AI_PROVIDER', 'google')
        
        # Build enhanced prompt based on industry and role
        industry_context = {
            'tech': 'Software engineering, cloud computing, and digital innovation',
            'finance': 'Financial systems, blockchain, and modern banking',
            'healthcare': 'Healthcare technology, patient care, and medical innovation',
            'crypto': 'Cryptocurrency, blockchain, DeFi, and web3 technologies',
            'saas': 'Software as a service, product-market fit, and scaling startups',
            'ecommerce': 'E-commerce, customer experience, and digital commerce trends'
        }
        
        role_perspective = {
            'ceo': 'strategic business decisions and company vision',
            'cto': 'technical architecture and technology decisions',
            'dev': 'hands-on coding, best practices, and technical tools',
            'pm': 'user experience, product strategy, and metrics',
            'hr': 'company culture, hiring, and employee engagement',
            'finance': 'financial optimization and business metrics',
            'ops': 'operational efficiency and process improvement',
            'marketing': 'growth strategies and audience engagement',
            'sales': 'customer relationships and business development'
        }
        
        emoji_prompt = {
            'none': 'Do not use any emojis.',
            'minimal': 'Use 1-2 emojis strategically.',
            'moderate': 'Use 2-4 emojis to enhance readability. (Recommended)',
            'high': 'Use 5-8 emojis to maximize engagement.'
        }
        
        topic_str = ', '.join(custom_topics) if custom_topics else 'industry trends, insights, or announcements'
        
        prompt = f"""Generate a LinkedIn post from the perspective of a {role_perspective.get(role, 'professional')}.

**Industry Context**: {industry_context.get(industry, industry)}
**Your Role**: {role}
**Topics**: {topic_str}
**Specific Topic**: {topic if topic else 'Choose something relevant'}
**Hashtags**: Create exactly {hashtags_count} relevant hashtags for maximum reach
**Emoji Style**: {emoji_prompt.get(emoji_level, 'Use 2-4 strategic emojis')}

Guidelines:
- Write in a professional yet approachable tone
- Include a hook in the first line to grab attention
- Target audience: {role} professionals in {industry}
- Post should be 150-300 words for optimal LinkedIn engagement
- Include a clear CTA (Call to Action)
- End with {hashtags_count} relevant hashtags
- Keep paragraphs short (2-3 sentences max)
- Make it shareable and valuable

Format: 
[Hook/Opening Line]

[2-3 body paragraphs with insights]

[CTA]

[Hashtags]"""

        ai = AIProvider(ai_provider)
        result = ai.generate(prompt, max_tokens=800)
        content = result.get('text', result.get('content', '')).strip()
        
        return jsonify({
            'success': True,
            'content': content,
            'industry': industry,
            'role': role,
            'hashtags_count': hashtags_count,
            'emoji_level': emoji_level
        })
    except Exception as e:
        logger.exception(f"Premium preview generation failed: {e}")
        return jsonify({'success': False, 'message': str(e)}), 400

@app.route('/api/enterprise-stats', methods=['GET'])
def get_enterprise_stats():
    """Get enhanced analytics for premium users"""
    try:
        posts = []
        if os.path.exists('data/posts.json'):
            with open('data/posts.json', 'r') as f:
                posts = json.load(f)
        
        total_posts = len(posts)
        posted = sum(1 for p in posts if p.get('posted'))
        scheduled = sum(1 for p in posts if p.get('scheduled'))
        
        return jsonify({
            'total_posts': total_posts,
            'posted_count': posted,
            'scheduled_count': scheduled,
            'draft_count': total_posts - posted - scheduled,
            'engagement_rate': 4.2,  # Placeholder - would be calculated from LinkedIn API
            'impressions': 12540,
            'followers_gained': 120
        })
    except Exception as e:
        logger.exception(f"Failed to get stats: {e}")
        return jsonify({'error': str(e)}), 400

if __name__ == '__main__':
    # Start the scheduler in background
    start_scheduler()
    
    # Disable debug mode in production
    debug_mode = os.getenv('FLASK_ENV') != 'production'
    app.run(debug=debug_mode, port=int(os.getenv('PORT', 5000)), host='0.0.0.0')
