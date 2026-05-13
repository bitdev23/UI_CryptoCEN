#!/usr/bin/env python3
"""
Diagnostic tool to test KB search and grounding for a specific user.
Helps debug why generated posts aren't using knowledge base content.
"""

import sys
import logging
from rag_system_pgvector import RAGStore
from database.db_helper import get_db

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_kb_for_user(user_id: str):
    """Test KB retrieval for a specific user"""
    print(f"\n{'='*70}")
    print(f"Testing KB Search for User: {user_id}")
    print(f"{'='*70}\n")
    
    try:
        db = get_db()
        rag = RAGStore(user_id=user_id)
        
        # 1. Check if user has any KB files
        print("1. Checking KB Files...")
        kb_files = db.list_kb_files(user_id)
        print(f"   Total files uploaded: {len(kb_files)}")
        
        for file_info in kb_files:
            file_id = file_info.get('id')
            file_name = file_info.get('filename')
            chunk_count = file_info.get('chunk_count', 0)
            status = file_info.get('upload_status')
            print(f"   - {file_name} (ID: {file_id[:8]}..., Status: {status}, Chunks: {chunk_count})")
        
        if not kb_files:
            print("   ❌ No KB files found. Upload a PDF first.")
            return
        
        # 2. Check if embeddings are built
        print("\n2. Checking if embeddings are built...")
        stats = db.get_kb_stats(user_id)
        total_chunks = stats.get('total_chunks', 0)
        print(f"   Total chunks indexed: {total_chunks}")
        
        if total_chunks == 0:
            print("   ❌ No chunks indexed. KB is not built yet.")
            return
        
        is_built = rag.is_built()
        print(f"   KB is_built(): {is_built}")
        
        # 3. Test hybrid search with multiple queries
        print("\n3. Testing Hybrid Search with Sample Queries...")
        test_queries = [
            "automated market makers AMMs",
            "constant product formula",
            "how AMMs work",
            "DeFi yield",
            "crypto knowledge base content",
        ]
        
        for query in test_queries:
            print(f"\n   Query: '{query}'")
            
            # Test vector search
            vector_hits = rag.similarity_search(query, k=3, match_threshold=0.6)
            print(f"   Vector hits: {len(vector_hits)}")
            for i, hit in enumerate(vector_hits, 1):
                sim = float(hit.get('similarity', 0))
                doc_preview = hit.get('document', '')[:100].replace('\n', ' ')
                print(f"     [{i}] Similarity: {sim:.4f} | {doc_preview}...")
            
            # Test keyword search
            keyword_hits = rag.keyword_search(query, k=3)
            print(f"   Keyword hits: {len(keyword_hits)}")
            for i, hit in enumerate(keyword_hits, 1):
                sim = float(hit.get('similarity', 0))
                doc_preview = hit.get('document', '')[:100].replace('\n', ' ')
                print(f"     [{i}] Similarity: {sim:.4f} | {doc_preview}...")
            
            # Test hybrid search
            hybrid_hits = rag.hybrid_search(query, k=3, match_threshold=0.60, vector_weight=0.7, keyword_weight=0.3)
            print(f"   Hybrid hits: {len(hybrid_hits)}")
            for i, hit in enumerate(hybrid_hits, 1):
                sim = float(hit.get('similarity', 0))
                doc_preview = hit.get('document', '')[:100].replace('\n', ' ')
                print(f"     [{i}] Similarity: {sim:.4f} | {doc_preview}...")
        
        # 4. Test grounding classification
        print("\n4. Testing Grounding Classification...")
        from app import _classify_grounding_level
        
        # Simulate a search with sample hits
        sample_query = "automated market makers AMMs"
        hits = rag.hybrid_search(sample_query, k=5, match_threshold=0.60, vector_weight=0.7, keyword_weight=0.3)
        
        if hits:
            grounding = _classify_grounding_level(hits, True, 'use_kb')
            similarities = [float(h.get('similarity', 0)) for h in hits]
            avg_sim = sum(similarities) / len(similarities) if similarities else 0
            
            print(f"   Sample query: '{sample_query}'")
            print(f"   Hits found: {len(hits)}")
            print(f"   Avg similarity: {avg_sim:.4f}")
            print(f"   Grounding level: {grounding}")
            print(f"   Similarities: {[f'{s:.4f}' for s in similarities]}")
        
        # 5. Check thresholds
        print("\n5. Grounding Thresholds in Code...")
        print(f"   FULL grounding:    avg_sim >= 0.77 AND 2+ hits with sim >= 0.78")
        print(f"   PARTIAL grounding: 1+ hits AND avg_sim >= 0.68")
        print(f"   NONE grounding:    avg_sim < 0.68 OR no hits")
        
        if hits:
            high_conf = sum(1 for s in similarities if s >= 0.78)
            print(f"\n   Your scores:")
            print(f"   - High confidence hits (>=0.78): {high_conf}")
            print(f"   - Avg similarity: {avg_sim:.4f}")
            print(f"   → Classification: {grounding}")
        
        print(f"\n{'='*70}\n")
        
    except Exception as e:
        logger.error(f"Error during KB test: {e}", exc_info=True)
        return

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python test_kb_search.py <user_id>")
        print("\nExample: python test_kb_search.py user@example.com")
        sys.exit(1)
    
    user_id = sys.argv[1]
    test_kb_for_user(user_id)
