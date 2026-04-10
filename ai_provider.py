"""Unified AI provider interface with task-based routing and provider fallback."""
from typing import Optional, Dict, List, Any
import os
import logging
import time
import json
from collections import defaultdict
from threading import Lock

logger = logging.getLogger("velank.ai_provider")

# ── Rate Limit Tracking ───────────────────────────────────────────────────────
# Track request counts per provider to implement exponential backoff on 429 errors
_RATE_LIMIT_STATE = defaultdict(lambda: {"count": 0, "reset_at": 0})
_RATE_LIMIT_LOCK = Lock()


class AIProvider:
    TASK_DEFAULTS = {
        "generate": "generate",
        "evaluate": "evaluate",
        "rewrite": "rewrite",
        "repurpose": "repurpose",
        "style_clone": "style_clone",
        "analysis": "analysis",
    }

    DEFAULT_MODELS = {
        "google": {
            "generate": "gemini-2.5-flash",
            "evaluate": "gemini-2.5-flash",
            "rewrite": "gemini-2.5-flash",
            "repurpose": "gemini-2.5-flash",
            "style_clone": "gemini-2.5-flash",
            "analysis": "gemini-2.5-flash",
        },
        "openai": {
            "generate": "gpt-4o-mini",
            "evaluate": "gpt-4o-mini",
            "rewrite": "gpt-4o-mini",
            "repurpose": "gpt-4o-mini",
            "style_clone": "gpt-4o-mini",
            "analysis": "gpt-4o-mini",
        },
        "claude": {
            "generate": "claude-sonnet-4-20250514",
            "evaluate": "claude-sonnet-4-20250514",
            "rewrite": "claude-sonnet-4-20250514",
            "repurpose": "claude-sonnet-4-20250514",
            "style_clone": "claude-sonnet-4-20250514",
            "analysis": "claude-sonnet-4-20250514",
        },
        "deepseek": {
            "generate": "deepseek-chat",
            "evaluate": "deepseek-chat",
            "rewrite": "deepseek-chat",
            "repurpose": "deepseek-chat",
            "style_clone": "deepseek-chat",
            "analysis": "deepseek-chat",
        },
        "xai": {
            "generate": "grok-2-latest",
            "evaluate": "grok-2-latest",
            "rewrite": "grok-2-latest",
            "repurpose": "grok-2-latest",
            "style_clone": "grok-2-latest",
            "analysis": "grok-2-latest",
        },
    }

    PROVIDER_ALIAS = {
        "anthropic": "claude",
        "claude": "claude",
        "openai": "openai",
        "google": "google",
        "gemini": "google",
        "deepseek": "deepseek",
        "xai": "xai",
        "grok": "xai",
    }

    def __init__(self, provider: Optional[str] = None, api_keys: Optional[Dict[str, str]] = None):
        raw_provider = (provider or os.getenv("AI_PROVIDER", "google")).lower().strip()
        self.provider = self.PROVIDER_ALIAS.get(raw_provider, raw_provider)
        self.api_keys = api_keys or {}
        self.request_timeout_sec = float((os.getenv("AI_REQUEST_TIMEOUT_SEC") or "45").strip() or 45)
        logger.info(
            "AI provider set to: %s (raw=%s, env=%s, param=%s)",
            self.provider,
            raw_provider,
            os.getenv("AI_PROVIDER", "NOT_SET"),
            provider,
        )
        self._clients: Dict[str, Any] = {}

    def _normalize_provider(self, provider: str) -> str:
        return self.PROVIDER_ALIAS.get((provider or "").strip().lower(), (provider or "").strip().lower())

    def _env_model_key(self, provider: str, task: str) -> str:
        return f"MODEL_{provider.upper()}_{task.upper()}"

    def _fallback_chain(self, task: str) -> List[str]:
        task_name = self.TASK_DEFAULTS.get(task, "generate")
        raw_chain = os.getenv(f"MODEL_FALLBACKS_{task_name.upper()}", "").strip()
        if raw_chain:
            chain = [self._normalize_provider(item) for item in raw_chain.split(',') if item.strip()]
        else:
            default_raw = os.getenv("MODEL_FALLBACKS_DEFAULT", "").strip()
            chain = [self._normalize_provider(item) for item in default_raw.split(',') if item.strip()] if default_raw else []

        ordered = [self.provider] + chain
        deduped = []
        seen = set()
        for item in ordered:
            if not item or item in seen:
                continue
            seen.add(item)
            deduped.append(item)
        return deduped or [self.provider]

    def _resolve_model(self, provider: str, task: str, model_override: Optional[str] = None) -> str:
        if model_override:
            return model_override

        task_name = self.TASK_DEFAULTS.get(task, "generate")
        env_key = self._env_model_key(provider, task_name)
        env_model = os.getenv(env_key, "").strip()
        if env_model:
            return env_model

        try:
            raw_task_map = os.getenv("MODEL_TASK_MAP_JSON", "").strip()
            if raw_task_map:
                parsed = json.loads(raw_task_map)
                model_from_map = ((parsed.get(provider) or {}).get(task_name) or "").strip()
                if model_from_map:
                    return model_from_map
        except Exception:
            logger.warning("Invalid MODEL_TASK_MAP_JSON; ignoring")

        provider_defaults = self.DEFAULT_MODELS.get(provider, {})
        return provider_defaults.get(task_name, provider_defaults.get("generate", ""))

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
        self._clients["claude"] = Anthropic(api_key=key, timeout=self.request_timeout_sec)

    def _init_openai(self):
        try:
            from openai import OpenAI
        except Exception:
            logger.exception("openai SDK not installed")
            raise
        key = self._get_api_key("OPENAI_API_KEY")
        if not key:
            raise RuntimeError("OPENAI_API_KEY not set")
        self._clients["openai"] = OpenAI(api_key=key, timeout=self.request_timeout_sec)

    def _init_deepseek(self):
        try:
            from openai import OpenAI
        except Exception:
            logger.exception("openai SDK not installed (required for deepseek compatibility)")
            raise
        key = self._get_api_key("DEEPSEEK_API_KEY")
        if not key:
            raise RuntimeError("DEEPSEEK_API_KEY not set")
        base_url = (os.getenv("DEEPSEEK_BASE_URL") or "https://api.deepseek.com").strip().rstrip('/')
        self._clients["deepseek"] = OpenAI(api_key=key, base_url=base_url, timeout=self.request_timeout_sec)

    def _init_xai(self):
        try:
            from openai import OpenAI
        except Exception:
            logger.exception("openai SDK not installed (required for xAI compatibility)")
            raise
        key = self._get_api_key("XAI_API_KEY")
        if not key:
            raise RuntimeError("XAI_API_KEY not set")
        base_url = (os.getenv("XAI_BASE_URL") or "https://api.x.ai/v1").strip().rstrip('/')
        self._clients["xai"] = OpenAI(api_key=key, base_url=base_url, timeout=self.request_timeout_sec)

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
        self._clients["google"] = gai

    def _ensure_client(self, provider: str):
        normalized = self._normalize_provider(provider)
        if self._clients.get(normalized):
            return
        try:
            if normalized == "claude":
                self._init_anthropic()
            elif normalized == "openai":
                self._init_openai()
            elif normalized == "google":
                self._init_google()
            elif normalized == "deepseek":
                self._init_deepseek()
            elif normalized == "xai":
                self._init_xai()
            else:
                raise ValueError(f"Unsupported provider: {normalized}")
        except Exception as e:
            logger.warning("Failed to init %s provider: %s", normalized, e)
            raise

    def _generate_openai_compatible(self, provider: str, prompt: str, model: str, max_tokens: int, temperature: float) -> Dict[str, Any]:
        client = self._clients[provider]
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=temperature,
            timeout=self.request_timeout_sec,
        )
        text = ""
        try:
            text = (resp.choices[0].message.content or "").strip()
        except Exception:
            text = ""

        usage = getattr(resp, "usage", None)
        prompt_tokens = int(getattr(usage, "prompt_tokens", 0) or 0) if usage else 0
        completion_tokens = int(getattr(usage, "completion_tokens", 0) or 0) if usage else 0

        return {
            "text": text,
            "provider": provider,
            "model": model,
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
            }
        }

    def _generate_claude(self, prompt: str, model: str, max_tokens: int, temperature: float) -> Dict[str, Any]:
        client = self._clients["claude"]
        resp = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
        )
        text = ""
        try:
            if resp.content and len(resp.content) > 0:
                text = (getattr(resp.content[0], "text", "") or "").strip()
        except Exception:
            text = ""

        usage = getattr(resp, "usage", None)
        input_tokens = int(getattr(usage, "input_tokens", 0) or 0) if usage else 0
        output_tokens = int(getattr(usage, "output_tokens", 0) or 0) if usage else 0

        return {
            "text": text,
            "provider": "claude",
            "model": model,
            "usage": {
                "prompt_tokens": input_tokens,
                "completion_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
            }
        }

    def _generate_google(self, prompt: str, model: str, max_tokens: int, temperature: float) -> Dict[str, Any]:
        client = self._clients["google"]
        generative_model = client.GenerativeModel(model)
        resp = generative_model.generate_content(
            contents=prompt,
            generation_config={
                "temperature": temperature,
                "max_output_tokens": max_tokens,
            },
        )

        text = (getattr(resp, "text", "") or "").strip()
        prompt_tokens = 0
        completion_tokens = 0
        try:
            usage = getattr(resp, "usage_metadata", None)
            prompt_tokens = int(getattr(usage, "prompt_token_count", 0) or 0)
            completion_tokens = int(getattr(usage, "candidates_token_count", 0) or 0)
        except Exception:
            prompt_tokens = 0
            completion_tokens = 0

        return {
            "text": text,
            "provider": "google",
            "model": model,
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
            }
        }

    def _estimate_usage_if_missing(self, result: Dict[str, Any], prompt: str) -> None:
        usage = result.get("usage") or {}
        if usage.get("total_tokens", 0) > 0:
            return
        prompt_tokens = int(round(max(1, len(prompt.split()) * 1.35)))
        output_tokens = int(round(max(1, len((result.get("text") or "").split()) * 1.35)))
        result["usage"] = {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": output_tokens,
            "total_tokens": prompt_tokens + output_tokens,
            "estimated": True,
        }

    def generate(
        self,
        prompt: str,
        max_tokens: int = 512,
        temperature: float = 0.2,
        task: str = "generate",
        model: Optional[str] = None,
        provider: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate text with task-aware model routing and provider fallback."""
        task_name = self.TASK_DEFAULTS.get(task, "generate")
        override_provider = self._normalize_provider(provider) if provider else None
        provider_chain = [override_provider] if override_provider else self._fallback_chain(task_name)

        last_error = None
        for provider_name in provider_chain:
            if not provider_name:
                continue
            resolved_model = self._resolve_model(provider_name, task_name, model_override=model)
            if not resolved_model:
                last_error = RuntimeError(f"No model resolved for provider={provider_name}, task={task_name}")
                continue

            started = time.time()
            try:
                self._ensure_client(provider_name)
                if provider_name in {"openai", "deepseek", "xai"}:
                    payload = self._generate_openai_compatible(provider_name, prompt, resolved_model, max_tokens, temperature)
                elif provider_name == "claude":
                    payload = self._generate_claude(prompt, resolved_model, max_tokens, temperature)
                elif provider_name == "google":
                    payload = self._generate_google(prompt, resolved_model, max_tokens, temperature)
                else:
                    raise RuntimeError(f"Unsupported provider at generation time: {provider_name}")

                self._estimate_usage_if_missing(payload, prompt)
                payload["task"] = task_name
                payload["latency_ms"] = int((time.time() - started) * 1000)
                return payload
            except Exception as exc:
                # Detect rate limit errors (429) and implement exponential backoff
                error_str = str(exc).lower()
                is_rate_limit = (
                    "429" in error_str 
                    or "rate limit" in error_str 
                    or "too many requests" in error_str
                    or "quota" in error_str
                )
                
                if is_rate_limit:
                    with _RATE_LIMIT_LOCK:
                        state = _RATE_LIMIT_STATE[provider_name]
                        state["count"] += 1
                    
                    # Exponential backoff: 0.1s, 0.2s, 0.4s, 0.8s, 1.6s
                    backoff_sec = min(1.6, 0.1 * (2 ** (state["count"] - 1)))
                    logger.warning(
                        "Rate limit detected on %s; backing off %.2fs and trying next provider. (attempt %d)",
                        provider_name,
                        backoff_sec,
                        state["count"],
                    )
                    time.sleep(backoff_sec)
                    # Don't break chain, just move to next provider
                else:
                    # Regular error, log and continue to fallback
                    logger.warning(
                        "AI generation failed provider=%s model=%s task=%s; trying next fallback. error=%s",
                        provider_name,
                        resolved_model,
                        task_name,
                        exc,
                    )
                
                last_error = exc

        logger.exception("AI generation failed across provider chain for task=%s", task_name)
        raise last_error or RuntimeError("AI generation failed")


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
