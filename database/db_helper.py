"""
Database helper for Supabase integration
Provides high-level methods for interacting with Supabase
"""

import logging
import os
from typing import List, Dict, Optional, Tuple
from supabase import create_client, Client
from datetime import datetime, date
import json

logger = logging.getLogger('velank.db_helper')

class SupabaseDB:
    """Wrapper for Supabase client with convenience methods"""
    
    def __init__(self, client: Client = None):
        if client is not None:
            self.client = client
            self.url = ''
            self.key = ''
            return

        self.url = os.getenv('SUPABASE_URL')
        self.key = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY') or os.getenv('SUPABASE_ANON_KEY')
        
        if not self.url or not self.key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY (or SUPABASE_SERVICE_ROLE_KEY) must be set in environment")
        
        self.client: Client = create_client(self.url, self.key)
    
    # =========================================================================
    # USER PROFILE METHODS
    # =========================================================================
    
    def get_user_profile(self, user_id: str) -> Optional[Dict]:
        """Get user profile by user_id"""
        result = self.client.table('user_profiles').select('*').eq('user_id', user_id).execute()
        return result.data[0] if result.data else None
    
    def create_user_profile(self, user_id: str, profile_data: Dict) -> Dict:
        """Create a new user profile"""
        profile_data['user_id'] = user_id
        result = self.client.table('user_profiles').insert(profile_data).execute()
        return result.data[0]
    
    def update_user_profile(self, user_id: str, profile_data: Dict) -> Dict:
        """Update user profile"""
        result = self.client.table('user_profiles').update(profile_data).eq('user_id', user_id).execute()
        return result.data[0] if result.data else None
    
    def get_user_settings(self, user_id: str) -> Dict:
        """Get all user settings (profile + subscription + usage)"""
        profile = self.get_user_profile(user_id)
        subscription = self.get_subscription(user_id)
        stats = self.get_dashboard_stats(user_id)
        
        return {
            'profile': profile,
            'subscription': subscription,
            'stats': stats
        }
    
    # =========================================================================
    # SUBSCRIPTION METHODS
    # =========================================================================
    
    def get_subscription(self, user_id: str) -> Optional[Dict]:
        """Get user subscription"""
        result = self.client.table('subscriptions').select('*').eq('user_id', user_id).execute()
        return result.data[0] if result.data else {'plan': 'free', 'status': 'active'}
    
    def create_subscription(self, user_id: str, plan: str = 'free') -> Dict:
        """Create a new subscription"""
        result = self.client.table('subscriptions').insert({
            'user_id': user_id,
            'plan': plan,
            'status': 'active'
        }).execute()
        return result.data[0]
    
    def update_subscription(self, user_id: str, subscription_data: Dict) -> Dict:
        """Update subscription"""
        result = self.client.table('subscriptions').update(subscription_data).eq('user_id', user_id).execute()
        return result.data[0] if result.data else None
    
    def can_generate_post(self, user_id: str) -> bool:
        """Check if user can generate more posts this month"""
        result = self.client.rpc('can_generate_post').execute()
        return result.data if result.data is not None else False
    
    def can_upload_kb_file(self, user_id: str, file_size_bytes: int) -> bool:
        """Check if user can upload KB file"""
        result = self.client.rpc('can_upload_kb_file', {'file_size_bytes': file_size_bytes}).execute()
        return result.data if result.data is not None else False
    
    # =========================================================================
    # KNOWLEDGE BASE METHODS
    # =========================================================================
    
    def list_kb_files(self, user_id: str) -> List[Dict]:
        """List all KB files for user"""
        result = self.client.table('kb_files').select('*').eq('user_id', user_id).order('created_at', desc=True).execute()
        return result.data
    
    def get_kb_file(self, file_id: str) -> Optional[Dict]:
        """Get KB file by ID"""
        result = self.client.table('kb_files').select('*').eq('id', file_id).execute()
        return result.data[0] if result.data else None
    
    def create_kb_file(self, user_id: str, file_data: Dict) -> Dict:
        """Create KB file record"""
        file_data['user_id'] = user_id
        result = self.client.table('kb_files').insert(file_data).execute()
        return result.data[0]
    
    def update_kb_file(self, file_id: str, file_data: Dict) -> Dict:
        """Update KB file record"""
        result = self.client.table('kb_files').update(file_data).eq('id', file_id).execute()
        return result.data[0] if result.data else None
    
    def delete_kb_file(self, file_id: str) -> bool:
        """Delete KB file record and embeddings"""
        # Delete embeddings first
        self.client.table('kb_embeddings').delete().eq('file_id', file_id).execute()
        # Delete file record
        result = self.client.table('kb_files').delete().eq('id', file_id).execute()
        return len(result.data) > 0
    
    def get_kb_stats(self, user_id: str) -> Dict:
        """Get KB usage stats"""
        result = self.client.table('kb_usage_stats').select('*').eq('user_id', user_id).execute()
        if result.data:
            return result.data[0]
        return {
            'total_files': 0,
            'total_size_bytes': 0,
            'total_chunks': 0
        }
    
    # =========================================================================
    # EMBEDDING METHODS (for pgvector)
    # =========================================================================
    
    def insert_embeddings(self, embeddings: List[Dict]) -> bool:
        """Insert embeddings in batch"""
        try:
            result = self.client.table('kb_embeddings').insert(embeddings).execute()
            return len(result.data) > 0
        except Exception as e:
            logger.exception('Error inserting embeddings: %s', e)
            return False
    
    def search_embeddings(self, user_id: str, query_embedding: List[float], 
                         match_threshold: float = 0.7, match_count: int = 4) -> List[Dict]:
        """Search KB using vector similarity"""
        result = self.client.rpc('match_kb_chunks', {
            'query_embedding': query_embedding,
            'match_threshold': match_threshold,
            'match_count': match_count,
            'filter_user_id': user_id
        }).execute()
        return result.data if result.data else []
    
    def search_embeddings_by_files(self, user_id: str, query_embedding: List[float],
                                   file_ids: List[str], match_threshold: float = 0.7,
                                   match_count: int = 4) -> List[Dict]:
        """Search specific files only"""
        result = self.client.rpc('match_kb_chunks_by_files', {
            'query_embedding': query_embedding,
            'file_ids': file_ids,
            'match_threshold': match_threshold,
            'match_count': match_count
        }).execute()
        return result.data if result.data else []
    
    # =========================================================================
    # POST METHODS
    # =========================================================================
    
    def create_post(self, user_id: str, post_data: Dict) -> Dict:
        """Create a new post"""
        post_data['user_id'] = user_id
        result = self.client.table('posts').insert(post_data).execute()
        
        # Increment usage counter
        self.increment_usage(user_id, 'post_generated')
        
        return result.data[0]
    
    def get_post(self, post_id: str) -> Optional[Dict]:
        """Get post by ID"""
        result = self.client.table('posts').select('*').eq('id', post_id).execute()
        return result.data[0] if result.data else None
    
    def update_post(self, post_id: str, post_data: Dict) -> Dict:
        """Update post"""
        result = self.client.table('posts').update(post_data).eq('id', post_id).execute()
        return result.data[0] if result.data else None
    
    def list_posts(self, user_id: str, status: Optional[str] = None, 
                  limit: int = 50, offset: int = 0) -> List[Dict]:
        """List posts with optional status filter"""
        query = self.client.table('posts').select('*').eq('user_id', user_id)
        
        if status:
            query = query.eq('status', status)
        
        result = query.order('created_at', desc=True).range(offset, offset + limit - 1).execute()
        return result.data
    
    def search_posts(self, user_id: str, search_term: str, limit: int = 50) -> List[Dict]:
        """Search posts by content or topic"""
        result = self.client.table('posts').select('*').eq('user_id', user_id).or_(
            f'content.ilike.%{search_term}%,topic.ilike.%{search_term}%'
        ).order('created_at', desc=True).limit(limit).execute()
        return result.data
    
    def delete_post(self, post_id: str) -> bool:
        """Delete post"""
        result = self.client.table('posts').delete().eq('id', post_id).execute()
        return len(result.data) > 0
    
    # =========================================================================
    # SCHEDULED POST METHODS
    # =========================================================================
    
    def create_scheduled_post(self, user_id: str, post_id: str, scheduled_for: datetime, timezone: str) -> Dict:
        """Schedule a post"""
        result = self.client.table('scheduled_posts').insert({
            'user_id': user_id,
            'post_id': post_id,
            'scheduled_for': scheduled_for.isoformat(),
            'timezone': timezone,
            'status': 'pending'
        }).execute()
        return result.data[0]
    
    def list_scheduled_posts(self, user_id: str, status: str = 'pending') -> List[Dict]:
        """List scheduled posts"""
        query = self.client.table('scheduled_posts').select('*, posts(*)').eq('user_id', user_id)
        
        if status:
            query = query.eq('status', status)
        
        result = query.order('scheduled_for').execute()
        return result.data
    
    def get_due_scheduled_posts(self) -> List[Dict]:
        """Get posts that are due to be published"""
        now = datetime.utcnow().isoformat()
        result = self.client.table('scheduled_posts').select('*, posts(*)').eq('status', 'pending').lte('scheduled_for', now).execute()
        return result.data
    
    def update_scheduled_post(self, scheduled_post_id: str, data: Dict) -> Dict:
        """Update scheduled post"""
        result = self.client.table('scheduled_posts').update(data).eq('id', scheduled_post_id).execute()
        return result.data[0] if result.data else None
    
    def cancel_scheduled_post(self, scheduled_post_id: str) -> bool:
        """Cancel scheduled post"""
        result = self.client.table('scheduled_posts').update({'status': 'cancelled'}).eq('id', scheduled_post_id).execute()
        return len(result.data) > 0
    
    # =========================================================================
    # USAGE TRACKING
    # =========================================================================
    
    def increment_usage(self, user_id: str, action_type: str, increment_value: int = 1) -> None:
        """Increment usage counter"""
        self.client.rpc('increment_usage', {
            'action_type': action_type,
            'increment_value': increment_value
        }).execute()
    
    def get_monthly_usage(self, user_id: str, month: Optional[date] = None) -> Dict:
        """Get usage for specific month"""
        if not month:
            month = date.today().replace(day=1)
        
        result = self.client.table('usage_monthly').select('*').eq('user_id', user_id).eq('month', month.isoformat()).execute()
        
        if result.data:
            return result.data[0]
        
        return {
            'posts_generated': 0,
            'posts_published': 0,
            'kb_files_uploaded': 0,
            'kb_storage_bytes': 0
        }
    
    # =========================================================================
    # DASHBOARD & ANALYTICS
    # =========================================================================
    
    def get_dashboard_stats(self, user_id: str) -> Dict:
        """Get all dashboard stats"""
        result = self.client.rpc('get_dashboard_stats', {'target_user_id': user_id}).execute()
        return result.data if result.data else {}
    
    def get_next_scheduled_post(self, user_id: str) -> Optional[Dict]:
        """Get next scheduled post"""
        result = self.client.rpc('get_next_scheduled_post').execute()
        return result.data if result.data else None
    
    def get_posting_streak(self, user_id: str) -> int:
        """Get user's posting streak"""
        result = self.client.rpc('calculate_posting_streak', {'target_user_id': user_id}).execute()
        return result.data if result.data is not None else 0
    
    # =========================================================================
    # STORAGE METHODS (for KB files)
    # =========================================================================
    
    # MIME type map for KB uploads
    _MIME_MAP = {
        '.pdf':  'application/pdf',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        '.doc':  'application/msword',
        '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        '.txt':  'text/plain',
        '.md':   'text/markdown',
        '.csv':  'text/csv',
    }

    def upload_to_storage(self, user_id: str, file_path: str, file_data: bytes) -> str:
        """Upload file to Supabase Storage with correct content-type."""
        storage_path = f"{user_id}/{file_path}"
        ext = os.path.splitext(file_path)[1].lower()
        content_type = self._MIME_MAP.get(ext, 'application/octet-stream')

        result = self.client.storage.from_('kb-files').upload(
            storage_path,
            file_data,
            file_options={'content-type': content_type}
        )

        return storage_path
    
    def download_from_storage(self, storage_path: str) -> bytes:
        """Download file from Supabase Storage"""
        result = self.client.storage.from_('kb-files').download(storage_path)
        return result
    
    def delete_from_storage(self, storage_path: str) -> bool:
        """Delete file from Supabase Storage"""
        try:
            self.client.storage.from_('kb-files').remove([storage_path])
            return True
        except Exception as e:
            logger.exception('Error deleting from storage: %s', e)
            return False
    
    def get_storage_url(self, storage_path: str) -> str:
        """Get signed URL for file"""
        result = self.client.storage.from_('kb-files').create_signed_url(storage_path, 3600)  # 1 hour expiry
        return result['signedURL']
    
    # =========================================================================
    # BACKGROUND JOB TRACKING
    # =========================================================================
    
    def create_background_job(self, job_type: str, user_id: Optional[str] = None, metadata: Optional[Dict] = None) -> Dict:
        """Create background job record"""
        result = self.client.table('background_jobs').insert({
            'job_type': job_type,
            'user_id': user_id,
            'status': 'pending',
            'metadata': json.dumps(metadata) if metadata else None
        }).execute()
        return result.data[0]
    
    def update_background_job(self, job_id: str, status: str, error_message: Optional[str] = None) -> Dict:
        """Update background job status"""
        data = {'status': status}
        
        if status == 'running':
            data['started_at'] = datetime.utcnow().isoformat()
        elif status in ['completed', 'failed']:
            data['completed_at'] = datetime.utcnow().isoformat()
        
        if error_message:
            data['error_message'] = error_message
        
        result = self.client.table('background_jobs').update(data).eq('id', job_id).execute()
        return result.data[0] if result.data else None
    
    # =========================================================================
    # SYSTEM LOGGING
    # =========================================================================
    
    def log(self, level: str, message: str, user_id: Optional[str] = None, metadata: Optional[Dict] = None) -> None:
        """Log system event"""
        try:
            self.client.table('system_logs').insert({
                'level': level,
                'message': message,
                'user_id': user_id,
                'metadata': json.dumps(metadata) if metadata else None
            }).execute()
        except Exception as e:
            logger.exception('Error logging to database: %s', e)


# Singleton instance
_db_instance = None

def get_db(client: Client = None) -> SupabaseDB:
    """Get or create database instance. Pass a client to share an existing connection."""
    global _db_instance
    if _db_instance is None:
        _db_instance = SupabaseDB(client=client)
    return _db_instance
