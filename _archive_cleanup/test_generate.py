from dotenv import load_dotenv
load_dotenv()
import os
from rag_system_pgvector import RAGStore
from ai_provider import AIProvider
from content_generator import ContentGenerator

user_id = os.getenv("TEST_USER_ID", "00000000-0000-0000-0000-000000000000")
rag = RAGStore(user_id=user_id)
ai = AIProvider()    # uses AI_PROVIDER from .env
cg = ContentGenerator(rag, ai)

post = cg.generate_post(
    theme="Derivatives & Perps",
    fmt="paragraph",
    query="funding rates funding arbitrage recent"
)
print("-----POST PREVIEW-----")
print(post["content"])
print("\n-----HASHTAGS-----\n", post["hashtags"])