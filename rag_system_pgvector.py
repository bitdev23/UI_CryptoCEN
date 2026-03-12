"""
RAG system using Supabase pgvector and sentence-transformers embeddings.
Replaces ChromaDB with PostgreSQL pgvector for scalable multi-tenant architecture.
"""
from typing import List, Tuple, Optional, Dict
import os
import threading
import hashlib
import numpy as np
import logging
from database.db_helper import get_db

logger = logging.getLogger("contentai.rag")

_MODEL_SINGLETON = None
_MODEL_LOCK = threading.Lock()
EMBEDDING_DIM = 384


class RAGStore:
    """
    RAG Store using Supabase pgvector
    
    Key differences from ChromaDB version:
    - Per-user collections (isolated by user_id)
    - Persistent storage in PostgreSQL
    - Vector search via SQL functions
    - File metadata tracked separately
    """
    
    def __init__(self, user_id: str):
        """
        Initialize RAG store for specific user
        
        Args:
            user_id: Supabase user UUID
        """
        self.user_id = user_id
        self.db = get_db()
        logger.info(f"RAGStore initialized for user {user_id}")
    
    def _get_model(self):
        """Lazy load the embedding model"""
        global _MODEL_SINGLETON
        if _MODEL_SINGLETON is None:
            with _MODEL_LOCK:
                if _MODEL_SINGLETON is None:
                    logger.info("Loading SentenceTransformer model...")
                    from sentence_transformers import SentenceTransformer
                    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
                    _MODEL_SINGLETON = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2", device="cpu")
                    logger.info("SentenceTransformer model loaded")
        return _MODEL_SINGLETON

    def _embedding_backend(self) -> str:
        """Embedding backend: 'hash' (default, low-memory) or 'transformer'."""
        backend = (os.getenv("EMBEDDING_BACKEND", "transformer") or "transformer").strip().lower()
        if backend not in {"hash", "transformer"}:
            return "transformer"
        return backend

    def _hash_embedding(self, text: str) -> np.ndarray:
        """Deterministic low-memory embedding fallback (not semantic, but stable)."""
        digest = hashlib.sha256((text or "").encode("utf-8")).digest()
        seed = int.from_bytes(digest[:8], byteorder="big", signed=False)
        rng = np.random.default_rng(seed)
        vec = rng.standard_normal(EMBEDDING_DIM).astype(np.float32)
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec

    def _encode_texts(self, texts: List[str]) -> List[np.ndarray]:
        backend = self._embedding_backend()
        if backend == "transformer":
            try:
                model = self._get_model()
                encoded = model.encode(texts, show_progress_bar=False)
                if hasattr(encoded, "shape"):
                    return [np.asarray(row, dtype=np.float32) for row in encoded]
                return [np.asarray(row, dtype=np.float32) for row in encoded]
            except Exception as exc:
                logger.warning("Transformer embeddings unavailable, falling back to hash backend: %s", exc)

        return [self._hash_embedding(text) for text in texts]
    
    def build_from_documents(self, docs: List[Tuple[str, str, str]], file_id: str) -> bool:
        """
        Build embeddings from documents and store in pgvector
        
        Args:
            docs: List of (source, text, metadata_dict) tuples
            file_id: UUID of the KB file these chunks belong to
            
        Returns:
            bool: Success status
        """
        if not docs:
            logger.warning("No documents provided to build RAG store")
            return False
        
        try:
            logger.info(f"Generating embeddings for {len(docs)} chunks...")

            batch_size = 32
            total_inserted = 0

            for batch_start in range(0, len(docs), batch_size):
                batch_docs = docs[batch_start:batch_start + batch_size]
                texts = [text for _, text, _ in batch_docs]
                embeddings = self._encode_texts(texts)

                records = []
                for offset, (source, text, metadata) in enumerate(batch_docs):
                    emb = embeddings[offset]
                    records.append({
                        'user_id': self.user_id,
                        'file_id': file_id,
                        'chunk_text': text,
                        'chunk_index': batch_start + offset,
                        'embedding': emb.tolist(),
                        'metadata': {
                            'source': source,
                            **(metadata if isinstance(metadata, dict) else {})
                        }
                    })

                if not self.db.insert_embeddings(records):
                    logger.error("Failed to insert embeddings batch starting at index %d", batch_start)
                    return False

                total_inserted += len(records)

            # Update file record with chunk count
            self.db.update_kb_file(file_id, {
                'chunk_count': total_inserted,
                'upload_status': 'indexed',
                'processed_at': 'now()'
            })
            logger.info(f"Successfully built vector store with {total_inserted} chunks for file {file_id}")
            return True
                
        except Exception as e:
            logger.exception(f"Failed to build vector store: {e}")
            # Mark file as failed
            try:
                self.db.update_kb_file(file_id, {
                    'upload_status': 'failed',
                    'error_message': str(e)
                })
            except:
                pass
            return False
    
    def rebuild_all_embeddings(self, file_ids: Optional[List[str]] = None) -> bool:
        """
        Rebuild embeddings for user's KB files
        
        Args:
            file_ids: Optional list of specific file IDs to rebuild. If None, rebuilds all.
            
        Returns:
            bool: Success status
        """
        try:
            # Get files to rebuild
            if file_ids:
                files = [self.db.get_kb_file(fid) for fid in file_ids if self.db.get_kb_file(fid)]
            else:
                files = self.db.list_kb_files(self.user_id)
            
            if not files:
                logger.info("No files to rebuild")
                return True
            
            logger.info(f"Rebuilding embeddings for {len(files)} files...")
            
            # For each file, download from storage and re-process
            from pdf_processor import load_pdfs
            
            for file_record in files:
                try:
                    # Download file from storage
                    file_data = self.db.download_from_storage(file_record['storage_path'])
                    
                    # Save temporarily
                    temp_path = f"/tmp/{file_record['filename']}"
                    with open(temp_path, 'wb') as f:
                        f.write(file_data)
                    
                    # Extract text
                    docs = load_pdfs(temp_path)
                    
                    # Delete old embeddings
                    self.db.client.table('kb_embeddings').delete().eq('file_id', file_record['id']).execute()
                    
                    # Rebuild embeddings
                    self.build_from_documents(docs, file_record['id'])
                    
                    # Cleanup temp file
                    os.remove(temp_path)
                    
                except Exception as e:
                    logger.error(f"Failed to rebuild file {file_record['id']}: {e}")
                    continue
            
            logger.info("Rebuild complete")
            return True
            
        except Exception as e:
            logger.exception(f"Failed to rebuild embeddings: {e}")
            return False
    
    def similarity_search(self, query: str, k: int = 4, 
                         match_threshold: float = 0.7,
                         file_ids: Optional[List[str]] = None) -> List[Dict]:
        """
        Search for similar chunks using vector similarity
        
        Args:
            query: Search query text
            k: Number of results to return
            match_threshold: Minimum similarity threshold (0-1)
            file_ids: Optional list of file IDs to search within
            
        Returns:
            List of dicts with keys: id, file_id, chunk_text, similarity, metadata
        """
        try:
            # Generate query embedding
            query_embedding = self._encode_texts([query])[0].tolist()
            
            # Search using pgvector
            if file_ids:
                results = self.db.search_embeddings_by_files(
                    user_id=self.user_id,
                    query_embedding=query_embedding,
                    file_ids=file_ids,
                    match_threshold=match_threshold,
                    match_count=k
                )
            else:
                results = self.db.search_embeddings(
                    user_id=self.user_id,
                    query_embedding=query_embedding,
                    match_threshold=match_threshold,
                    match_count=k
                )
            
            # Format results to match old ChromaDB interface
            formatted_results = []
            for result in results:
                formatted_results.append({
                    'document': result['chunk_text'],
                    'metadata': result.get('metadata', {}),
                    'similarity': result.get('similarity', 0.0),
                    'distance': 1.0 - result.get('similarity', 0.0),  # Convert to distance
                    'file_id': result.get('file_id'),
                    'id': result.get('id')
                })
            
            logger.info(f"Found {len(formatted_results)} similar chunks for query")
            return formatted_results
            
        except Exception as e:
            logger.exception(f"Similarity search failed: {e}")
            return []
    
    def is_built(self) -> bool:
        """Check if user has any KB embeddings"""
        try:
            stats = self.db.get_kb_stats(self.user_id)
            return stats.get('total_chunks', 0) > 0
        except Exception as e:
            logger.exception(f"Failed to check if RAG is built: {e}")
            return False
    
    def get_document_count(self) -> int:
        """Get number of chunks in user's KB"""
        try:
            stats = self.db.get_kb_stats(self.user_id)
            return stats.get('total_chunks', 0)
        except Exception as e:
            logger.exception(f"Failed to get document count: {e}")
            return 0
    
    def get_file_count(self) -> int:
        """Get number of files in user's KB"""
        try:
            stats = self.db.get_kb_stats(self.user_id)
            return stats.get('total_files', 0)
        except Exception as e:
            logger.exception(f"Failed to get file count: {e}")
            return 0
    
    def persist(self) -> None:
        """No-op for compatibility (pgvector auto-persists)"""
        logger.info("PostgreSQL auto-persists data")
    
    def delete_file_embeddings(self, file_id: str) -> bool:
        """Delete all embeddings for a specific file"""
        try:
            self.db.client.table('kb_embeddings').delete().eq('file_id', file_id).execute()
            logger.info(f"Deleted embeddings for file {file_id}")
            return True
        except Exception as e:
            logger.exception(f"Failed to delete embeddings: {e}")
            return False


def create_rag_store(user_id: str) -> RAGStore:
    """Factory function to create RAG store for user"""
    return RAGStore(user_id=user_id)


if __name__ == "__main__":
    import dotenv
    import logging
    
    dotenv.load_dotenv()
    logging.basicConfig(level=logging.DEBUG)
    
    # Test with a sample user_id
    test_user_id = "00000000-0000-0000-0000-000000000000"
    store = RAGStore(user_id=test_user_id)
    print(f"RAGStore initialized for user {test_user_id}")
    print(f"Document count: {store.get_document_count()}")
    print(f"Is built: {store.is_built()}")
