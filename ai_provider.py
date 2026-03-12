"""Unified AI provider interface for Claude, OpenAI, and Google Gemini."""
from typing import Optional, Dict
import os
import logging
import time

logger = logging.getLogger("valtrilabs.ai_provider")


class AIProvider:
    def __init__(self, provider: Optional[str] = None, api_keys: Optional[Dict[str, str]] = None):
        raw_provider = (provider or os.getenv("AI_PROVIDER", "google")).lower().strip()
        provider_aliases = {
            "anthropic": "claude",
            "claude": "claude",
            "openai": "openai",
            "google": "google",
            "gemini": "google",
        }
        self.provider = provider_aliases.get(raw_provider, raw_provider)
        self.api_keys = api_keys or {}
        logger.info(
            "AI provider set to: %s (raw=%s, env=%s, param=%s)",
            self.provider,
            raw_provider,
            os.getenv("AI_PROVIDER", "NOT_SET"),
            provider,
        )
        # lazy imports
        self._client = None

    def _get_api_key(self, key_name: str) -> str:
        return (self.api_keys.get(key_name) or os.getenv(key_name) or '').strip()

    def _init_anthropic(self):
        try:
            from anthropic import Anthropic
        except Exception:
            logger.exception("anthropic SDK not installed")
            raise
        key = self._get_api_key("ANTHROPIC_API_KEY")
        if not key:
            raise RuntimeError("ANTHROPIC_API_KEY not set")
        self._client = Anthropic(api_key=key)

    def _init_openai(self):
        try:
            from openai import OpenAI
        except Exception:
            logger.exception("openai SDK not installed")
            raise
        key = self._get_api_key("OPENAI_API_KEY")
        if not key:
            raise RuntimeError("OPENAI_API_KEY not set")
        self._client = OpenAI(api_key=key)

    def _init_google(self):
        try:
            import google.generativeai as gai
        except Exception:
            logger.exception("google generative SDK not installed")
            raise
        key = self._get_api_key("GOOGLE_API_KEY")
        if not key:
            raise RuntimeError("GOOGLE_API_KEY not set")
        gai.configure(api_key=key)
        # Prefer the new client.models.generate_content API when available
        self._client = gai

    def _ensure_client(self):
        if self._client:
            return
        try:
            if self.provider == "claude":
                self._init_anthropic()
            elif self.provider == "openai":
                self._init_openai()
            elif self.provider in ("google", "gemini"):
                self._init_google()
            else:
                raise ValueError(f"Unsupported provider: {self.provider}")
        except Exception as e:
            logger.warning("Failed to init %s provider: %s. Falling back to Google.", self.provider, e)
            # Fall back to Google
            self.provider = "google"
            self._init_google()

    def generate(self, prompt: str, max_tokens: int = 512, temperature: float = 0.2) -> Dict[str, str]:
        """Generate text from selected provider; returns dict with 'text' and metadata."""
        self._ensure_client()
        try:
            if self.provider == "claude":
                # Use Messages API (new)
                resp = self._client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=max_tokens,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=temperature,
                )
                text = resp.content[0].text
                return {"text": text, "provider": "claude"}
            elif self.provider == "openai":
                resp = self._client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
                text = resp.choices[0].message.content
                return {"text": text, "provider": "openai"}
            else:
                # Google Gemini - attempt to use client.models.generate_content (gemini-2.5-flash)
                try:
                    # client.models.generate_content signature may vary between SDK versions
                    client = self._client
                    if hasattr(client, "client") and hasattr(client.client, "models") and hasattr(client.client.models, "generate_content"):
                        # Newer google-genai client interface
                        resp = client.client.models.generate_content(
                            model="gemini-2.5-flash",
                            input=[{"content": prompt}],
                            temperature=temperature,
                            max_output_tokens=max_tokens,
                        )
                        # Extract text from response (best-effort)
                        text = ""
                        try:
                            # Some SDK versions return .outputs[0].content[0].text
                            outputs = getattr(resp, "outputs", None) or resp.get("outputs") if isinstance(resp, dict) else None
                            if outputs:
                                first = outputs[0]
                                # content may be a list of dicts
                                contents = first.get("content") if isinstance(first, dict) else getattr(first, "content", None)
                                if isinstance(contents, list) and contents:
                                    text = contents[0].get("text") if isinstance(contents[0], dict) else getattr(contents[0], "text", "")
                            # fallback for dict-like response
                            if not text and isinstance(resp, dict):
                                text = resp.get("candidates", [])[0].get("content", "") if resp.get("candidates") else ""
                        except Exception:
                            try:
                                text = getattr(resp, "text", "") or resp.get("text", "")
                            except Exception:
                                text = ""
                        return {"text": text or "", "provider": "google"}
                    else:
                        # Fallback to older GenerativeModel usage (use gemini-2.5-flash if available)
                        from google.generativeai import GenerativeModel
                        model = GenerativeModel("gemini-2.5-flash")
                        resp = model.generate_content(contents=prompt)
                        text = resp.text if resp and getattr(resp, "text", None) else (resp.get("text") if isinstance(resp, dict) else "")
                        return {"text": text, "provider": "google"}
                except Exception:
                    logger.exception("Google generation failed, falling back")
                    raise
        except Exception:
            logger.exception("AI generation failed for provider %s", self.provider)
            raise


if __name__ == "__main__":
    import dotenv, logging
    dotenv.load_dotenv()
    logging.basicConfig(level=logging.DEBUG)
    api = AIProvider()
    try:
        out = api.generate("Write a short LinkedIn post about virtual assistants.")
        print(out.get("text", ""))
    except Exception as e:
        print("Generation failed:", e)
