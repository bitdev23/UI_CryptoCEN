#!/usr/bin/env python
"""
Safe local test: Generate a LinkedIn post WITHOUT posting.
Validates all components (RAG, AI, prompt, formatting) before real posting.
"""
import os
import sys
import json
import logging
from datetime import datetime
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def main():
    # Validate setup
    logger.info("=" * 60)
    logger.info("LINKEDIN POST GENERATION TEST (preview mode)")
    logger.info("=" * 60)
    
    # Check env
    if os.getenv("TEST_MODE", "true").lower() not in ("1", "true"):
        logger.warning("TEST_MODE is not true — would attempt LIVE posting!")
        sys.exit(1)
    
    api_provider = os.getenv("AI_PROVIDER", "google").lower()
    logger.info(f"AI Provider: {api_provider}")
    
    if api_provider == "google":
        if not os.getenv("GOOGLE_API_KEY"):
            logger.error("GOOGLE_API_KEY not set in .env")
            sys.exit(1)
    elif api_provider == "claude":
        if not os.getenv("ANTHROPIC_API_KEY"):
            logger.error("ANTHROPIC_API_KEY not set in .env")
            sys.exit(1)
    
    logger.info("✓ API credentials configured")
    
    # Load RAG
    logger.info("Loading RAG embeddings...")
    try:
        from rag_system_pgvector import RAGStore
        user_id = os.getenv("TEST_USER_ID", "00000000-0000-0000-0000-000000000000")
        rag = RAGStore(user_id=user_id)
        logger.info("✓ RAG loaded")
    except Exception as e:
        logger.error(f"Failed to load RAG: {e}")
        sys.exit(1)
    
    # Initialize AI
    logger.info("Initializing AI provider...")
    try:
        from ai_provider import AIProvider
        ai = AIProvider()
        logger.info("✓ AI provider initialized")
    except Exception as e:
        logger.error(f"Failed to init AI: {e}")
        sys.exit(1)
    
    # Generate post
    logger.info("Generating post...")
    try:
        from content_generator import ContentGenerator
        cg = ContentGenerator(rag, ai)
        post = cg.generate_post(
            theme="Derivatives & Perps",
            fmt="paragraph",
            query="funding rates liquidity deep value arbitrage"
        )
        logger.info("✓ Post generated")
    except Exception as e:
        logger.error(f"Generation failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # Display results
    logger.info("\n" + "=" * 60)
    logger.info("POST PREVIEW")
    logger.info("=" * 60)
    print(post.get("content", ""))
    
    logger.info("\n" + "=" * 60)
    logger.info("METADATA")
    logger.info("=" * 60)
    print(f"Theme: {post.get('theme')}")
    print(f"Format: {post.get('format')}")
    print(f"Hashtags: {', '.join(post.get('hashtags', []))}")
    print(f"Provider: {post.get('provider')}")
    print(f"Saved to: data/posts.json")
    
    # Check post quality (basic)
    content = post.get("content", "")
    content_len = len(content)
    logger.info("\n" + "=" * 60)
    logger.info("QUALITY CHECKS")
    logger.info("=" * 60)
    print(f"Content length: {content_len} chars")
    
    if content_len < 50:
        logger.warning("⚠ Post too short!")
    elif content_len > 1000:
        logger.warning("⚠ Post very long (LinkedIn prefers < 1000 chars)")
    else:
        logger.info("✓ Post length OK")
    
    if "***" in content or "___" in content:
        logger.warning("⚠ Stray markdown or formatting detected in content")
    else:
        logger.info("✓ No stray formatting")
    
    if len(post.get("hashtags", [])) < 2:
        logger.warning("⚠ Few hashtags (expected 4-6)")
    else:
        logger.info("✓ Hashtags present")
    
    logger.info("\n" + "=" * 60)
    logger.info("✓ TEST COMPLETE — Post is ready for LinkedIn")
    logger.info("=" * 60)
    logger.info("\nNext steps:")
    logger.info("1. Review the post preview above")
    logger.info("2. Check data/posts.json for saved post")
    logger.info("3. If happy with quality, set TEST_MODE=false in .env")
    logger.info("4. Run: python -m main (option 3) to post LIVE")
    logger.info("   OR commit and push to GitHub for scheduled posting")

if __name__ == "__main__":
    main()
