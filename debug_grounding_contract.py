#!/usr/bin/env python3
"""
Diagnostic script to debug grounding contract failures.

Run this to understand why KB retrieval is failing and what similarity scores are being produced.
"""
import os
import sys
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from rag_system_pgvector import RAGStore
from database.db_helper import get_db
from dotenv import load_dotenv

load_dotenv()

def diagnose_grounding(user_id: str, topic: str, industry: str = "", role: str = ""):
    """
    Diagnose why grounding contract might be failing.
    
    Prints detailed information about:
    - Query expansion results
    - Similarity search scores
    - Keyword search scores
    - Hybrid scoring
    - Grounding contract requirements vs actual results
    """
    print("\n" + "="*70)
    print("GROUNDING CONTRACT DIAGNOSTIC")
    print("="*70 + "\n")
    
    rag = RAGStore(user_id)
    
    # Check if KB is built
    if not rag.is_built():
        print("❌ Knowledge base not built. No embeddings found.")
        print("   Action: Upload and index KB files first.")
        return
    
    kb_stats = rag.db.get_kb_stats(user_id)
    print(f"KB Status: {kb_stats.get('total_chunks', 0)} chunks from {kb_stats.get('total_files', 0)} files")
    print()
    
    # Generate retrieval queries
    from app import _expand_retrieval_queries, _normalize_topic_text
    normalized_topic = _normalize_topic_text(topic)
    
    queries = _expand_retrieval_queries(
        normalized_topic or topic,
        industry,
        role,
        'general_engagement'  # default goal
    )
    
    print(f"Generated {len(queries)} retrieval queries:")
    for i, q in enumerate(queries, 1):
        print(f"  {i}. {q}")
    print()
    
    # Test different thresholds
    thresholds = [0.75, 0.60, 0.50, 0.40, 0.30]
    
    print("─" * 70)
    print("VECTOR SIMILARITY SEARCH (vary threshold)")
    print("─" * 70)
    print()
    
    vector_results_by_threshold = {}
    
    for threshold in thresholds:
        all_vector_hits = {}
        
        for query in queries[:2]:  # Just test first 2 queries
            try:
                hits = rag.similarity_search(query, k=6, match_threshold=threshold)
                for hit in hits:
                    cid = hit.get('id') or hit.get('document', '')[:80]
                    sim = float(hit.get('similarity', 0))
                    if cid not in all_vector_hits or sim > float(all_vector_hits[cid].get('similarity', 0)):
                        all_vector_hits[cid] = hit
            except Exception as e:
                print(f"  Error with threshold {threshold}: {e}")
        
        vector_results_by_threshold[threshold] = all_vector_hits
        
        if all_vector_hits:
            sims = sorted([float(h.get('similarity', 0)) for h in all_vector_hits.values()], reverse=True)
            avg_sim = sum(sims) / len(sims)
            print(f"Threshold {threshold}: {len(sims)} hits, avg_sim={avg_sim:.4f}, min={sims[-1]:.4f}, max={sims[0]:.4f}")
            print(f"  Top 3 similarities: {[f'{s:.4f}' for s in sims[:3]]}")
        else:
            print(f"Threshold {threshold}: 0 hits")
        
        print()
    
    print("─" * 70)
    print("HYBRID SEARCH (vector=0.75 + keyword=0.25, match_threshold=0.30)")
    print("─" * 70)
    print()
    
    all_hybrid_hits = {}
    
    for query in queries:
        try:
            hits = rag.hybrid_search(
                query, k=8,
                match_threshold=0.30,
                vector_weight=0.75,
                keyword_weight=0.25
            )
            for hit in hits:
                cid = hit.get('id') or hit.get('document', '')[:80]
                sim = float(hit.get('similarity', 0))
                if cid not in all_hybrid_hits or sim > float(all_hybrid_hits[cid].get('similarity', 0)):
                    all_hybrid_hits[cid] = hit
        except Exception as e:
            print(f"  Error with hybrid search: {e}")
    
    if all_hybrid_hits:
        sims = sorted([float(h.get('similarity', 0)) for h in all_hybrid_hits.values()], reverse=True)
        avg_sim = sum(sims) / len(sims)
        print(f"Found {len(sims)} hybrid hits")
        print(f"  Average similarity: {avg_sim:.4f}")
        print(f"  Min/Max: {sims[-1]:.4f} / {sims[0]:.4f}")
        print(f"  Top 5 scores: {[f'{s:.4f}' for s in sims[:5]]}")
        print()
        
        # Show details of top hits
        print("Top 3 hits (with source content):")
        for i, hit in enumerate(sorted(all_hybrid_hits.values(), key=lambda h: float(h.get('similarity', 0)), reverse=True)[:3], 1):
            sim = float(hit.get('similarity', 0))
            doc = hit.get('document', '')[:200]
            print(f"  {i}. Sim={sim:.4f}")
            print(f"     {doc}...")
            print()
    else:
        print("❌ No hybrid hits found!")
        print()
    
    print("─" * 70)
    print("GROUNDING CONTRACT EVALUATION")
    print("─" * 70)
    print()
    
    if all_hybrid_hits:
        sims = [float(h.get('similarity', 0)) for h in all_hybrid_hits.values()]
        avg_sim = sum(sims) / len(sims)
        hit_count = len(sims)
        
        # OLD thresholds
        print("Old Thresholds (before fix):")
        print(f"  Strict:   min_hits=2, min_avg_sim=0.56")
        strict_old = hit_count >= 2 and avg_sim >= 0.56
        balanced_old = hit_count >= 1 and avg_sim >= 0.42
        print(f"    Status: {'✅ PASS' if strict_old else '❌ FAIL'}")
        print(f"  Balanced: min_hits=1, min_avg_sim=0.42")
        print(f"    Status: {'✅ PASS' if balanced_old else '❌ FAIL'}")
        print()
        
        # NEW thresholds  
        print("New Thresholds (after fix):")
        print(f"  Strict:   min_hits=2, min_avg_sim=0.45")
        strict_new = hit_count >= 2 and avg_sim >= 0.45
        balanced_new = hit_count >= 1 and avg_sim >= 0.35
        print(f"    Status: {'✅ PASS' if strict_new else '❌ FAIL'}")
        print(f"  Balanced: min_hits=1, min_avg_sim=0.35")
        print(f"    Status: {'✅ PASS' if balanced_new else '❌ FAIL'}")
        print()
        
        print(f"Actual Results:")
        print(f"  Hits: {hit_count}")
        print(f"  Avg Similarity: {avg_sim:.4f}")
        print()
    else:
        print("❌ Cannot evaluate - no hits found")
        print()
        print("TROUBLESHOOTING:")
        print("1. Verify KB is indexed: Check KB management in dashboard")
        print("2. Check embedding model: Is EMBEDDING_MODEL env var correct?")
        print("3. Try manual keyword search:")
        print()
        for query in queries[:2]:
            keyword_hits = rag.keyword_search(query, k=3)
            if keyword_hits:
                print(f"   Query: '{query}'")
                print(f"   Found {len(keyword_hits)} keyword hits")
            else:
                print(f"   Query: '{query}' - No keyword hits")
        print()


if __name__ == '__main__':
    # Get user ID from environment or use test user
    user_id = os.getenv('TEST_USER_ID', '')
    
    if not user_id:
        print("Usage:")
        print("  TEST_USER_ID=<uuid> python debug_grounding_contract.py")
        print()
        print("Example:")
        print("  TEST_USER_ID=550e8400-e29b-41d4-a716-446655440000 python debug_grounding_contract.py")
        print()
        print("Or with specific topic:")
        print("  TEST_USER_ID=... python debug_grounding_contract.py <topic> <industry> <role>")
        sys.exit(1)
    
    topic = sys.argv[1] if len(sys.argv) > 1 else "6. Types of Crypto Assets"
    industry = sys.argv[2] if len(sys.argv) > 2 else "Crypto & Web3"
    role = sys.argv[3] if len(sys.argv) > 3 else ""
    
    diagnose_grounding(user_id, topic, industry, role)
