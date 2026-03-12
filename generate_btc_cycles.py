"""Generate BTC cycle educational drafts using RAG and AI provider."""
import os
import dotenv
from rag_system_pgvector import RAGStore
from ai_provider import AIProvider

dotenv.load_dotenv()

def main():
    user_id = os.getenv("TEST_USER_ID", "00000000-0000-0000-0000-000000000000")
    rag = RAGStore(user_id=user_id)
    ai = AIProvider()

    # query the corpus for BTC-related context
    query = "bitcoin BTC halving cycles drawdown historical 2009 2012 2016 2020 2024"
    docs = rag.similarity_search(query, k=6)
    ctx = "\n---\n".join([d.get('document','') for d in docs])

    prompt = f"""
You are an expert crypto researcher writing a data-driven, technical LinkedIn post about Bitcoin price cycles since 2009.
Requirements:
- Lead with a single concrete insight about BTC cycles (first 1-2 lines).
- Include a concise historical table (year of cycle peak, approximate peak price, subsequent drawdown %) for major cycles (2011, 2013, 2017, 2021, 2024 where applicable).
- Explain differences in retail vs institutional behaviour during cycles (entry/exit timing, leverage use, sentiment indicators).
- Tie technical drivers: halvings, miner economics, macro liquidity, derivatives leverage, liquidations.
- Provide actionable takeaway for traders or product leaders (execution, risk sizing, custody considerations).
- Tone: educational, non-marketing, evidence-first.
- Length: ~250-400 words.
Context data (use where appropriate to ground claims):\n{ctx}

Produce the post only, end with 4-6 relevant hashtags.
"""

    print("Generating BTC cycles draft...\n")
    out = ai.generate(prompt, max_tokens=800, temperature=0.2)
    text = out.get('text','').strip()
    print(text)

if __name__ == '__main__':
    main()
