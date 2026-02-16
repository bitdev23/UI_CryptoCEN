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
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
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
        'ACTIVE_PERSONA': os.getenv('ACTIVE_PERSONA', 'professional'),
        'TONE': os.getenv('TONE', 'professional'),
        'STYLE': os.getenv('STYLE', 'formal'),
        'EMOJI_USAGE': os.getenv('EMOJI_USAGE', 'moderate'),
        'HASHTAG_COUNT': os.getenv('HASHTAG_COUNT', '3'),
        'LANGUAGE': os.getenv('LANGUAGE', 'English'),
        'AUDIENCE_KEYWORDS': os.getenv('AUDIENCE_KEYWORDS', ''),
        'CONTENT_TOPICS': os.getenv('CONTENT_TOPICS', '')
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
    """Job to run scheduled posting"""
    try:
        logger.info("Running scheduled post job")
        
        # Check for scheduled posts that are due
        if os.path.exists('data/scheduled_posts.json'):
            try:
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
        
        # Generate and post new content (existing logic)
        config_obj = load_config()
        if config_obj['TEST_MODE']:
            logger.info("Skipping daily post generation - TEST_MODE is enabled")
            return
            
        # Generate content directly (simplified version)
        ai = AIProvider()
        profile_key = config_obj['CONTENT_PROFILE']
        profile = cfg.PROFILES.get(profile_key, cfg.PROFILES[cfg.DEFAULT_PROFILE])
        theme = random.choice(profile.get('content_themes', []))
        fmt = random.choice(cfg.POST_FORMATS)
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
    """Start the background scheduler"""
    def scheduler_thread():
        config = load_config()
        if config['TEST_MODE']:
            logger.info("Scheduler not started - TEST_MODE is enabled")
            return
            
        tz = pytz.timezone(config['TIMEZONE'])
        schedule_time = f"{config['POST_TIME_HOUR']:02d}:{config['POST_TIME_MINUTE']:02d}"
        
        schedule.every().day.at(schedule_time).do(scheduled_post_job)
        logger.info("Scheduler started - will post daily at %s %s", schedule_time, config['TIMEZONE'])
        
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    
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
        
        # Simple prompt for preview generation
        prompt = f"""Generate a LinkedIn post about: {theme}

Company context: {services}

Post format: {fmt}

Make it engaging, professional, and include relevant hashtags. Keep it between {config_obj.get('MIN_POST_LENGTH', 150)} and {config_obj.get('MAX_POST_LENGTH', 1000)} characters."""

        logger.info(f"Generating preview with prompt: {prompt[:100]}...")
        
        result = ai.generate(prompt, max_tokens=500)
        if not result or 'text' not in result:
            logger.error(f"Invalid AI response: {result}")
            return jsonify({'success': False, 'message': "AI returned empty response"}), 400
            
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
    """Generate and post immediately"""
    try:
        from ai_provider import AIProvider
        from linkedin_poster import LinkedInPoster
        import random
        import config as cfg
        
        config_obj = load_config()
        
        # Generate content directly (simplified version)
        ai = AIProvider()
        profile_key = config_obj['CONTENT_PROFILE']
        profile = cfg.PROFILES.get(profile_key, cfg.PROFILES[cfg.DEFAULT_PROFILE])
        theme = random.choice(profile.get('content_themes', []))
        fmt = random.choice(cfg.POST_FORMATS)
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
        
        status_message = "Post published successfully!" if post_result.get('status') == 'posted' else "Post preview generated (test mode)"
        
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
        
        # Save uploaded files
        uploaded_count = 0
        allowed_extensions = ('.pdf', '.docx')
        
        for file in files:
            if not file or not file.filename:
                continue
            
            filename = secure_filename(file.filename)
            file_ext = filename.lower()
            
            # Check if file has allowed extension
            if not any(file_ext.endswith(ext) for ext in allowed_extensions):
                logger.warning("Skipping non-PDF/DOCX file: %s", filename)
                continue
            
            try:
                filepath = os.path.join('data/pdfs', filename)
                file.save(filepath)
                logger.info("Saved file: %s", filepath)
                uploaded_count += 1
            except Exception as e:
                logger.exception("Failed to save file %s: %s", filename, e)
                continue
        
        if uploaded_count == 0:
            logger.warning("No PDF/DOCX files found in upload")
            return jsonify({'success': False, 'message': 'No PDF or DOCX files found in upload'}), 400
        
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
            else:
                logger.warning("No documents loaded from PDFs/DOCX files")
        except Exception as e:
            rag_error = str(e)
            logger.exception("RAG build error: %s", e)
        
        # Return success even if RAG fails (files were uploaded)
        response_msg = f'Successfully uploaded {uploaded_count} file(s)'
        if rag_error:
            response_msg += f' (RAG training skipped: {rag_error})'
        
        return jsonify({
            'success': True,
            'message': response_msg,
            'uploaded': uploaded_count
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
        
        rag = RAGStore(persist_dir="data/chroma_db")
        
        # Load and build
        if os.path.exists('data/pdfs'):
            docs = load_pdfs("data/pdfs")
            if not docs:
                return jsonify({
                    'success': False,
                    'message': 'No documents found in knowledge base'
                }), 400
            
            rag.build_from_documents(docs)
            rag.persist()
            
            return jsonify({
                'success': True,
                'message': f'Model trained successfully with {len(docs)} documents'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Knowledge base (data/pdfs) not found'
            }), 400
    except Exception as e:
        logger.exception("Model training failed")
        return jsonify({'success': False, 'message': f'Training failed: {str(e)}'}), 500

@app.route('/api/knowledge-base-status', methods=['GET'])
def knowledge_base_status():
    """Get knowledge base statistics"""
    try:
        from rag_system import RAGStore
        
        rag = RAGStore(persist_dir="data/chroma_db")
        
        pdf_count = 0
        if os.path.exists('data/pdfs'):
            pdf_count = len([f for f in os.listdir('data/pdfs') if f.endswith('.pdf')])
        
        is_trained = rag.is_built()
        
        return jsonify({
            'success': True,
            'trained': is_trained,
            'pdf_count': pdf_count,
            'status': 'Ready for use' if is_trained else 'Needs training',
            'rag_ready': is_trained
        })
    except Exception as e:
        logger.exception("Knowledge base status check failed")
        return jsonify({
            'success': False,
            'message': f'Status check failed: {str(e)}'
        }), 500

if __name__ == '__main__':
    # Start the scheduler in background
    start_scheduler()
    
    # Disable debug mode in production
    debug_mode = os.getenv('FLASK_ENV') != 'production'
    app.run(debug=debug_mode, port=int(os.getenv('PORT', 5000)), host='0.0.0.0')
