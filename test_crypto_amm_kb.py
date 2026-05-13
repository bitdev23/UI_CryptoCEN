#!/usr/bin/env python3
"""
Test script to verify KB retrieval and grounding for crypto/AMM topic.
This simulates what happens during generation with the new thresholds.
"""

import sys
import logging
from rag_system_pgvector import RAGStore

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Simulating grounding level constants from app.py
_GROUNDING_FULL = 'grounded'
_GROUNDING_PARTIAL = 'partial'
_GROUNDING_NONE = 'ungrounded'

def _classify_grounding_level(kb_hits: list, kb_used: bool, kb_mode: str) -> str:
    """Classify grounding level with IMPROVED thresholds"""
    if kb_mode == 'no_kb' or not kb_used or not kb_hits:
        return _GROUNDING_NONE

    similarities = [float(h.get('similarity', 0)) for h in kb_hits if h]
    if not similarities:
        return _GROUNDING_NONE

    avg_sim = sum(similarities) / len(similarities)
    high_conf_count = sum(1 for s in similarities if s >= 0.70)

    if high_conf_count >= 2 and avg_sim >= 0.70:
        return _GROUNDING_FULL
    elif len(similarities) >= 1 and avg_sim >= 0.55:
        return _GROUNDING_PARTIAL
    else:
        return _GROUNDING_NONE

def test_crypto_amm_retrieval(user_id: str):
    """Test KB retrieval specifically for crypto/AMM topic"""
    print(f"\n{'='*70}")
    print(f"Testing Crypto/AMM KB Retrieval")
    print(f"User ID: {user_id}")
    print(f"{'='*70}\n")
    
    try:
        rag = RAGStore(user_id=user_id)
        
        # Check if KB is built
        if not rag.is_built():
            print("❌ Knowledge base is not built. Upload and index a PDF first.")
            return
        
        doc_count = rag.get_document_count()
        print(f"✓ KB is built with {doc_count} chunks\n")
        
        # Test the exact queries that would be used
        test_cases = [
            {
                'name': 'AMM Exact',
                'query': 'how automated market makers AMMs work and what is the Constant Product Formula',
                'theme': 'how automated market makers AMMs work and what is the Constant Product Formula'
            },
            {
                'name': 'AMM + Crypto',
                'query': 'how automated market makers AMMs work and what is the Constant Product Formula in crypto',
                'theme': 'AMM Constant Product Formula'
            },
            {
                'name': 'Broad Crypto',
                'query': 'crypto automated market makers',
                'theme': 'AMM'
            },
        ]
        
        for test_case in test_cases:
            print(f"\n{'─'*70}")
            print(f"Test: {test_case['name']}")
            print(f"Query: {test_case['query']}")
            print(f"{'─'*70}")
            
            # Test with NEW (improved) thresholds
            hits = rag.hybrid_search(
                test_case['query'],
                k=6,
                match_threshold=0.50,  # NEW: lowered from 0.68
                vector_weight=0.75,    # NEW: adjusted from 0.7
                keyword_weight=0.25,   # NEW: adjusted from 0.3
            )
            
            print(f"\nHybrid search results: {len(hits)} hits")
            
            if not hits:
                print("❌ No hits found!")
                # Try with OLD thresholds for comparison
                old_hits = rag.hybrid_search(
                    test_case['query'],
                    k=6,
                    match_threshold=0.68,  # OLD threshold
                    vector_weight=0.7,
                    keyword_weight=0.3,
                )
                print(f"   (OLD thresholds would find: {len(old_hits)} hits)")
                continue
            
            # Show hit details
            for i, hit in enumerate(hits[:5], 1):
                sim = float(hit.get('similarity', 0))
                doc_preview = (hit.get('document', '')[:100]).replace('\n', ' ')
                print(f"  [{i}] Similarity: {sim:.4f} | {doc_preview}...")
            
            # Classify grounding level
            grounding = _classify_grounding_level(hits, True, 'use_kb')
            similarities = [float(h.get('similarity', 0)) for h in hits]
            avg_sim = sum(similarities) / len(similarities) if similarities else 0
            
            print(f"\n  Grounding Classification:")
            print(f"    - Hits: {len(similarities)}")
            print(f"    - Avg similarity: {avg_sim:.4f}")
            print(f"    - High-conf (≥0.70): {sum(1 for s in similarities if s >= 0.70)}")
            print(f"    - Result: {grounding.upper()}")
            
            if grounding == _GROUNDING_NONE:
                print(f"    ❌ Would use INSIGHT-ONLY mode (ignoring KB)")
            elif grounding == _GROUNDING_PARTIAL:
                print(f"    ✓ Would use PARTIAL mode (KB + opinion)")
            else:
                print(f"    ✓✓ Would use FULL mode (KB-grounded)")
        
        print(f"\n{'='*70}\n")
        
    except Exception as e:
        logger.error(f"Error during test: {e}", exc_info=True)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 test_crypto_amm_kb.py <user_id>")
        print("\nExample: python3 test_crypto_amm_kb.py f47ac10b-58cc-4372-a567-0e02b2c3d479")
        sys.exit(1)
    
    user_id = sys.argv[1]
    test_crypto_amm_retrieval(user_id)
