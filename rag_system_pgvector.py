"""
RAG system using Supabase pgvector and sentence-transformers embeddings.
Replaces ChromaDB with PostgreSQL pgvector for scalable multi-tenant architecture.
"""
from typing import List, Tuple, Optional, Dict
import os
import re
import threading
import hashlib
import numpy as np
import logging
from database.db_helper import get_db

logger = logging.getLogger("contentai.rag")

_MODEL_SINGLETON = None
_MODEL_LOCK = threading.Lock()

# ── Configurable embedding model ──────────────────────────────────────────────
# Change these env vars when upgrading to a larger model (e.g. all-mpnet-base-v2).
# After changing, you MUST rebuild all KB embeddings for every user.
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM", "384"))

# ── Stop words for keyword search ─────────────────────────────────────────────
_KEYWORD_STOP_WORDS = frozenset({
    'a', 'an', 'the', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
    'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'shall',
    'should', 'may', 'might', 'must', 'can', 'could', 'about', 'above',
    'after', 'again', 'against', 'all', 'am', 'and', 'any', 'as', 'at',
    'because', 'before', 'below', 'between', 'both', 'but', 'by', 'down',
    'during', 'each', 'few', 'for', 'from', 'further', 'get', 'got',
    'he', 'her', 'here', 'hers', 'herself', 'him', 'himself', 'his',
    'how', 'i', 'if', 'in', 'into', 'it', 'its', 'itself', 'just',
    'me', 'more', 'most', 'my', 'myself', 'no', 'nor', 'not', 'now',
    'of', 'off', 'on', 'once', 'only', 'or', 'other', 'our', 'ours',
    'ourselves', 'out', 'over', 'own', 'same', 'she', 'so', 'some',
    'such', 'than', 'that', 'their', 'theirs', 'them', 'themselves',
    'then', 'there', 'these', 'they', 'this', 'those', 'through', 'to',
    'too', 'under', 'until', 'up', 'us', 'very', 'we', 'what', 'when',
    'where', 'which', 'while', 'who', 'whom', 'why', 'with', 'you',
    'your', 'yours', 'yourself', 'yourselves',
})


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
        """Lazy load the embedding model (model name from EMBEDDING_MODEL env var)"""
        global _MODEL_SINGLETON
        if _MODEL_SINGLETON is None:
            with _MODEL_LOCK:
                if _MODEL_SINGLETON is None:
                    logger.info("Loading SentenceTransformer model: %s", EMBEDDING_MODEL)
                    from sentence_transformers import SentenceTransformer
                    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
                    _MODEL_SINGLETON = SentenceTransformer(EMBEDDING_MODEL, device="cpu")
                    logger.info("SentenceTransformer model loaded: %s (dim=%d)", EMBEDDING_MODEL, EMBEDDING_DIM)
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

    # ─────────────────────────────────────────────────────────────────────────
    # Keyword Search (BM25-proxy via SQL ILIKE)
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    @staticmethod
    def _extract_keywords(text: str, max_keywords: int = 6) -> List[str]:
        """Extract meaningful keywords from text, removing stop words.

        Only [a-zA-Z0-9] tokens are kept, which implicitly sanitises against
        PostgREST operator injection (%, _, ., (, ), etc.).
        """
        tokens = re.findall(r'[a-zA-Z0-9]+', (text or '').lower())
        keywords = [t for t in tokens if t not in _KEYWORD_STOP_WORDS and len(t) >= 3]
        # Deduplicate while preserving order
        seen = set()
        unique = []
        for kw in keywords:
            if kw not in seen:
                seen.add(kw)
                unique.append(kw)
        return unique[:max_keywords]

    @staticmethod
    def _sanitize_ilike_value(val: str) -> str:
        """Escape characters that have special meaning in SQL LIKE / PostgREST ILIKE."""
        return val.replace('%', '').replace('_', '').replace('\\', '')

    def keyword_search(self, query: str, k: int = 6,
                       file_ids: Optional[List[str]] = None) -> List[Dict]:
        """Search KB chunks using keyword matching (SQL ILIKE).

        Returns results in the same format as similarity_search, with a
        pseudo-similarity score computed from keyword hit density.
        """
        keywords = self._extract_keywords(query)
        if not keywords:
            return []

        try:
            # Build OR condition: chunk_text ILIKE %kw1% OR chunk_text ILIKE %kw2% ...
            conditions = ','.join(
                f'chunk_text.ilike.%{self._sanitize_ilike_value(kw)}%' for kw in keywords
            )
            q = (self.db.client.table('kb_embeddings')
                 .select('id, file_id, chunk_text, metadata')
                 .eq('user_id', self.user_id)
                 .or_(conditions)
                 .limit(k * 2))  # Fetch extra, we'll score and trim

            if file_ids:
                q = q.in_('file_id', file_ids)

            result = q.execute()
            rows = result.data if result.data else []

            # Score each row by keyword density
            formatted = []
            for row in rows:
                text_lower = (row.get('chunk_text') or '').lower()
                hits = sum(1 for kw in keywords if kw in text_lower)
                # Pseudo-similarity: fraction of keywords matched (0..1)
                kw_score = hits / len(keywords) if keywords else 0.0
                if kw_score <= 0:
                    continue
                formatted.append({
                    'document': row.get('chunk_text', ''),
                    'metadata': row.get('metadata') or {},
                    'similarity': round(kw_score * 0.85, 4),  # Cap at 0.85 to avoid dominating vector
                    'distance': round(1.0 - kw_score * 0.85, 4),
                    'file_id': row.get('file_id'),
                    'id': row.get('id'),
                    '_source': 'keyword',
                })

            # Sort by score descending, return top k
            formatted.sort(key=lambda h: h['similarity'], reverse=True)
            logger.info("Keyword search found %d hits for %d keywords", len(formatted[:k]), len(keywords))
            return formatted[:k]

        except Exception as e:
            logger.warning("Keyword search failed: %s — returning empty", e)
            return []

    def hybrid_search(self, query: str, k: int = 4,
                      match_threshold: float = 0.7,
                      file_ids: Optional[List[str]] = None,
                      vector_weight: float = 0.7,
                      keyword_weight: float = 0.3) -> List[Dict]:
        """Hybrid search combining vector similarity + keyword matching.

        Results are merged, deduplicated by chunk id, and scored with
        a weighted combination: vector_weight * vector_sim + keyword_weight * kw_sim.
        """
        # Run both searches in sequence (can't parallelise Supabase calls easily)
        vector_hits = self.similarity_search(
            query, k=k, match_threshold=match_threshold, file_ids=file_ids
        )
        keyword_hits = self.keyword_search(query, k=k, file_ids=file_ids)

        # Merge by chunk id
        merged = {}
        for hit in vector_hits:
            cid = hit.get('id') or hit.get('document', '')[:80]
            merged[cid] = {
                **hit,
                '_vector_sim': float(hit.get('similarity', 0)),
                '_keyword_sim': 0.0,
                '_source': 'vector',
            }

        for hit in keyword_hits:
            cid = hit.get('id') or hit.get('document', '')[:80]
            if cid in merged:
                # Already found by vector — boost with keyword score
                merged[cid]['_keyword_sim'] = float(hit.get('similarity', 0))
                merged[cid]['_source'] = 'both'
            else:
                merged[cid] = {
                    **hit,
                    '_vector_sim': 0.0,
                    '_keyword_sim': float(hit.get('similarity', 0)),
                    '_source': 'keyword',
                }

        # Compute hybrid score
        for cid, hit in merged.items():
            hybrid = (vector_weight * hit['_vector_sim'] +
                      keyword_weight * hit['_keyword_sim'])
            hit['similarity'] = round(hybrid, 4)
            hit['distance'] = round(1.0 - hybrid, 4)

        ranked = sorted(merged.values(), key=lambda h: h['similarity'], reverse=True)
        logger.info("Hybrid search: %d vector + %d keyword → %d merged results",
                     len(vector_hits), len(keyword_hits), len(ranked[:k]))
        return ranked[:k]

    # ─────────────────────────────────────────────────────────────────────────
    # Chunk Quality Scoring
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def score_chunk_quality(chunk_text: str) -> float:
        """Score a chunk's information quality on a 0-1 scale.

        Low scores indicate: headers, footers, table-of-contents,
        very short fragments, boilerplate, or non-informative text.
        """
        text = (chunk_text or '').strip()
        if not text:
            return 0.0

        score = 1.0
        word_count = len(text.split())

        # Penalise very short chunks
        if word_count < 10:
            score *= 0.2
        elif word_count < 20:
            score *= 0.5
        elif word_count < 40:
            score *= 0.75

        # Penalise chunks that are mostly numbers / special chars (tables, TOC)
        alpha_ratio = sum(1 for c in text if c.isalpha()) / max(len(text), 1)
        if alpha_ratio < 0.4:
            score *= 0.3

        # Penalise chunks that look like table-of-contents or page headers
        lines = text.split('\n')
        if len(lines) > 2:
            short_lines = sum(1 for l in lines if len(l.strip()) < 15)
            if short_lines / len(lines) > 0.7:
                score *= 0.3  # Mostly very short lines = TOC or list

        # Penalise boilerplate patterns
        lower = text.lower()
        boilerplate_markers = [
            'table of contents', 'page ', 'copyright', 'all rights reserved',
            'confidential', 'disclaimer', '...', '___', '---',
            'header', 'footer', 'appendix', 'references',
        ]
        boilerplate_hits = sum(1 for m in boilerplate_markers if m in lower)
        if boilerplate_hits >= 2:
            score *= 0.3
        elif boilerplate_hits == 1:
            score *= 0.6

        # Bonus for chunks with complete sentences
        sentence_endings = sum(1 for c in text if c in '.!?')
        if sentence_endings >= 2 and word_count >= 30:
            score = min(score * 1.1, 1.0)

        return round(max(0.0, min(1.0, score)), 3)


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
