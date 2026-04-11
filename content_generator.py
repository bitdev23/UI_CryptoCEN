"""Generate LinkedIn posts using RAG retrieval and AI providers."""
from typing import List, Dict, Any
import os
import logging
from datetime import datetime
import json
import re
from rag_system_pgvector import RAGStore
from ai_provider import AIProvider
import config

logger = logging.getLogger("velank.content_generator")


class ContentGenerator:
    def __init__(self, rag: RAGStore, ai: AIProvider, save_path: str = "data/posts.json"):
        self.rag = rag
        self.ai = ai
        self.save_path = save_path
        try:
            os.makedirs(os.path.dirname(self.save_path), exist_ok=True)
        except Exception:
            pass

    def build_prompt(self, theme: str, fmt: str, query: str, context_docs: List[dict]) -> str:
        # Compose prompt with retrieved context and brand info
        ctx_text = "\n---\n".join([d.get("document", "") for d in context_docs[:4]])
        # determine profile info
        profile_key = os.getenv("CONTENT_PROFILE", config.DEFAULT_PROFILE)
        profile = config.PROFILES.get(profile_key, config.PROFILES[config.DEFAULT_PROFILE])
        company_name = profile["company_info"]["name"]

        # Optionally fetch a short market snapshot (CoinGecko) to ground recent prices
        # But only if the query seems to be about trading/prices/market
        market_snippet = ""
        try:
            if os.getenv("ENABLE_MARKET_GROUNDING", "false").lower() in ("1", "true"):
                # Only add market data if query/theme relates to trading, prices, or market metrics
                market_related_keywords = ["price", "trading", "market", "volatility", "pump", "dump", "bull", "bear", "liquidity", "volume"]
                query_lower = (query + " " + theme).lower()
                include_market = any(kw in query_lower for kw in market_related_keywords)
                
                if include_market:
                    import requests
                    ids = os.getenv("GROUND_TOKENS", "bitcoin,ethereum")
                    r = requests.get(
                        f"https://api.coingecko.com/api/v3/simple/price?ids={ids}&vs_currencies=usd&include_24hr_change=true",
                        timeout=10,
                    )
                    if r.ok:
                        data = r.json()
                        parts = []
                        for tk in ids.split(","):
                            if tk in data:
                                p = data[tk]
                                parts.append(f"{tk.upper()}: ${p.get('usd'):,} ({p.get('usd_24h_change'):+.2f}% 24h)")
                        if parts:
                            market_snippet = "Recent market snapshot: " + "; ".join(parts) + "."
        except Exception:
            logger.exception("Market grounding fetch failed")

        prompt = (
            "You are a senior content strategist writing high-quality LinkedIn posts for professionals.\n"
            "Write clearly, naturally, and with practical value.\n"
            "\n"
            "POST RULES:\n"
            "- Do not use hashtags in the middle of sentences.\n"
            "- Do not mention internal document names, chapters, or knowledge-base references.\n"
            "- Do not invent facts, numbers, dates, or claims not supported by context.\n"
            "- Avoid generic AI/corporate buzzwords and overly promotional language.\n"
            "- Keep paragraphs short (1-2 sentences) for readability.\n"
            "\n"
            "VOICE:\n"
            "- Professional, useful, and direct.\n"
            "- Explain tradeoffs and practical implications where relevant.\n"
            "- End with a clear takeaway or engagement prompt.\n"
            "\n"
            "FORMAT:\n"
            "- Length: ~150-220 words.\n"
            "- Structure: Hook → 2-3 value paragraphs → concise CTA/takeaway → hashtags on final line only.\n"
            "\n"
            "CONTEXT — Background Knowledge (paraphrase naturally, never cite sections):\n"
            f"{ctx_text}\n"
            f"{market_snippet}\n"
            "\n"
            "Output plain LinkedIn post text only."
        )
        return prompt

    def generate_post(self, theme: str, fmt: str, query: str) -> Dict[str, Any]:
        docs = self.rag.similarity_search(query, k=4)
        prompt = self.build_prompt(theme, fmt, query, docs)
        logger.debug("Prompt length: %d", len(prompt))
        resp = self.ai.generate(prompt, max_tokens=800, temperature=0.5)
        text = resp.get("text", "").strip()
        # Post-process to remove stray markdown/asterisks and clean formatting
        try:
            # remove runs of asterisks inside text
            text = re.sub(r"\*{2,}", "", text)
            # strip leading/trailing asterisks/spaces on each line and remove empty lines
            lines = text.splitlines()
            cleaned = []
            for ln in lines:
                ln2 = re.sub(r"^[\s\*]+|[\s\*]+$", "", ln)
                if ln2:
                    cleaned.append(ln2)
            text = "\n".join(cleaned)
        except Exception:
            logger.exception("Post-processing cleanup failed")

        # improved hashtag extraction (find all hashtags anywhere in the text)
        hashtags = re.findall(r"#[-_A-Za-z0-9]+", text) if text else []
        post = {
            "theme": theme,
            "format": fmt,
            "query": query,
            "content": text,
            "hashtags": hashtags,
            "provider": resp.get("provider"),
            "created_at": datetime.utcnow().isoformat() + "Z",
        }
        self._save_post(post)
        return post

    def _save_post(self, post: Dict[str, Any]) -> None:
        try:
            data = []
            if os.path.exists(self.save_path):
                with open(self.save_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            data.append(post)
            with open(self.save_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            logger.info("Saved post to %s", self.save_path)
        except Exception:
            logger.exception("Failed to save post")


if __name__ == "__main__":
    import dotenv, logging
    dotenv.load_dotenv()
    logging.basicConfig(level=logging.DEBUG)
    user_id = os.getenv("TEST_USER_ID", "00000000-0000-0000-0000-000000000000")
    rag = RAGStore(user_id=user_id)
    ai = AIProvider()
    cg = ContentGenerator(rag, ai)
    post = cg.generate_post(theme="productivity tips", fmt="list", query="how virtual assistants improve productivity")
    print(post.get("content", ""))
