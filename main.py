"""Main scheduler and interactive CLI for ValtriLabs LinkedIn automation."""
import os
from dotenv import load_dotenv

# Load .env FIRST before any other imports that use os.getenv()
load_dotenv()

import logging
import schedule
import time
from datetime import datetime
import pytz
from utils import setup_logging, ensure_data_dirs
from pdf_processor import load_pdfs, chunk_text
from rag_system_pgvector import RAGStore
from ai_provider import AIProvider
from content_generator import ContentGenerator
from linkedin_poster import LinkedInPoster
import config

logger = setup_logging()


def resolve_user_id() -> str:
    user_id = os.getenv("TEST_USER_ID", "00000000-0000-0000-0000-000000000000")
    return user_id


def build_knowledge_base():
    logger.info("Building knowledge base from PDFs")
    docs = load_pdfs("data/pdfs")
    user_id = resolve_user_id()
    rag = RAGStore(user_id=user_id)
    docs_for_rag = []
    for source, text in docs:
        for idx, chunk in enumerate(chunk_text(text, chunk_size=1000, overlap=200)):
            docs_for_rag.append((source, chunk, {'chunk_number': idx + 1}))
    if docs_for_rag:
        file_record = rag.db.create_kb_file(user_id, {
            'filename': f'cli_build_{datetime.utcnow().strftime("%Y%m%d_%H%M%S")}.pdf',
            'file_size_bytes': sum(len(item[1]) for item in docs),
            'file_type': 'pdf',
            'storage_path': 'local/cli_build',
            'upload_status': 'processing'
        })
        rag.build_from_documents(docs_for_rag, file_record['id'])
    rag.persist()
    return rag


def create_and_post(rag: RAGStore, live: bool = False):
    ai = AIProvider()
    cg = ContentGenerator(rag, ai)
    # rotate theme/format
    import random
    profile_key = os.getenv("CONTENT_PROFILE", config.DEFAULT_PROFILE)
    profile = config.PROFILES.get(profile_key, config.PROFILES[config.DEFAULT_PROFILE])
    theme = random.choice(profile.get("content_themes", []))
    fmt = random.choice(config.POST_FORMATS)
    services = profile.get("company_info", {}).get("services", "")
    query = f"{theme} {services}"
    post = cg.generate_post(theme, fmt, query)
    poster = LinkedInPoster(test_mode=not live)
    try:
        res = poster.post(post['content'])
        logger.info("Posting result: %s", res)
    except Exception:
        logger.exception("Failed to post")


def schedule_daily(rag: RAGStore, hour: int, minute: int, tz_name: str, live: bool = False):
    tz = pytz.timezone(tz_name)
    def job():
        logger.info("Scheduled job running at %s", datetime.now(tz).isoformat())
        create_and_post(rag, live=live)

    schedule_time = f"{hour:02d}:{minute:02d}"
    schedule.every().day.at(schedule_time).do(job)
    logger.info("Scheduled daily posting at %s %s (local schedule time string)", schedule_time, tz_name)
    while True:
        schedule.run_pending()
        time.sleep(10)


def interactive():
    ensure_data_dirs()
    rag = RAGStore(user_id=resolve_user_id())
    print("ValtriLabs LinkedIn Automation — Interactive Menu")
    while True:
        print("Options:\n1) Build knowledge base from PDFs\n2) Run now (preview)\n3) Enable live posting and run now\n4) Start scheduler\n5) Exit")
        choice = input("Choose an option: ").strip()
        if choice == "1":
            rag = build_knowledge_base()
        elif choice == "2":
            create_and_post(rag, live=False)
        elif choice == "3":
            create_and_post(rag, live=True)
        elif choice == "4":
            hour = int(os.getenv("POST_TIME_HOUR", "11"))
            minute = int(os.getenv("POST_TIME_MINUTE", "0"))
            tz = os.getenv("TIMEZONE", "America/New_York")
            schedule_daily(rag, hour, minute, tz, live=(os.getenv("TEST_MODE", "true").lower() not in ("1","true")))
        elif choice == "5":
            print("Exiting")
            break
        else:
            print("Invalid choice")


if __name__ == "__main__":
    interactive()
