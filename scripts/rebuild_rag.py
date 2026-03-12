#!/usr/bin/env python
"""Rebuild RAG embeddings from PDFs/DOCX in data/pdfs."""
import os
import sys
import logging
from dotenv import load_dotenv

# Add parent directory to path so we can import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    from pdf_processor import load_pdfs, chunk_text
    from rag_system_pgvector import RAGStore
    
    logger.info("Loading PDFs/DOCX from data/pdfs...")
    docs = load_pdfs("data/pdfs")
    
    if not docs:
        logger.warning("No PDFs/DOCX found in data/pdfs")
        sys.exit(0)
    
    logger.info(f"Loaded {len(docs)} documents")

    user_id = os.getenv("TEST_USER_ID", "00000000-0000-0000-0000-000000000000")
    rag = RAGStore(user_id=user_id)

    # Delete old KB rows for this user, then rebuild
    for existing in rag.db.list_kb_files(user_id):
        rag.db.delete_kb_file(existing['id'])

    docs_for_rag = []
    for source, text in docs:
        for idx, chunk in enumerate(chunk_text(text, chunk_size=1000, overlap=200)):
            docs_for_rag.append((source, chunk, {'chunk_number': idx + 1}))

    logger.info("Building RAG embeddings...")
    file_record = rag.db.create_kb_file(user_id, {
        'filename': f'rebuild_{len(docs)}_docs.pdf',
        'file_size_bytes': sum(len(item[1]) for item in docs),
        'file_type': 'pdf',
        'storage_path': 'local/rebuild_rag',
        'upload_status': 'processing'
    })
    rag.build_from_documents(docs_for_rag, file_record['id'])
    rag.persist()
    
    logger.info("✓ RAG rebuilt successfully")
    
except Exception as e:
    logger.exception(f"Failed to rebuild RAG: {e}")
    sys.exit(1)
