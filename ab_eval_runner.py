#!/usr/bin/env python3
"""Run A/B model evaluation on 300 LinkedIn-generation prompts.

Usage:
  python ab_eval_runner.py --prompts 300 --providers google,openai,claude
  python ab_eval_runner.py --prompts 300 --providers google,deepseek,xai --output-dir benchmarks/results

Environment overrides:
  AB_PRICE_JSON='{"google":{"input_per_million":0.35,"output_per_million":1.05}}'
  MODEL_GOOGLE_GENERATE=gemini-2.5-flash
  MODEL_DEEPSEEK_GENERATE=deepseek-chat
  MODEL_XAI_GENERATE=grok-2-latest
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import random
import re
import statistics
import sys
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Any

try:
    from dotenv import load_dotenv
except Exception:
    load_dotenv = None

if load_dotenv:
    load_dotenv(dotenv_path=Path(__file__).resolve().parent / '.env', override=True)

from ai_provider import AIProvider


def words_count(text: str) -> int:
    return len(re.findall(r"\b[\w'-]+\b", text or ""))


def post_contract_heuristics(body: str, theme: str, goal_key: str) -> dict:
    text = str(body or "").strip()
    if not text:
        return {
            "score": 0,
            "clarity": 0,
            "novelty": 0,
            "specificity": 0,
            "hook": 0,
            "cta": 0,
            "issues": ["Empty output"],
        }

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    first_line = paragraphs[0].split("\n")[0].strip() if paragraphs else text[:120]
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
    avg_sentence_len = (sum(words_count(s) for s in sentences) / len(sentences)) if sentences else words_count(text)

    lower_text = text.lower()
    lower_first = first_line.lower()
    theme_tokens = [token for token in re.findall(r"[a-zA-Z0-9]+", str(theme or "").lower()) if len(token) >= 4]
    hook_topic_match = any(token in lower_first for token in theme_tokens[:6]) if theme_tokens else True
    hook_length_ok = len(first_line) <= 120

    cta_markers = [
        "what's your take", "what do you think", "curious", "share your", "drop a comment",
        "let me know", "agree or disagree", "thoughts?", "have you seen", "would you"
    ]
    has_cta = any(marker in lower_text for marker in cta_markers) or text.endswith("?")

    numbers_count = len(re.findall(r"\b\d+(?:\.\d+)?%?\b", text))
    specificity_terms = len(re.findall(r"\b[A-Z]{2,}\b", text)) + numbers_count

    banned_generic = [
        "in today's fast-paced world", "game changer", "paradigm shift", "cutting-edge", "synergy",
        "move the needle", "best practices", "robust", "transformative"
    ]
    banned_hits = sum(1 for phrase in banned_generic if phrase in lower_text)

    clarity = max(0, min(100, int(round(100 - max(0, avg_sentence_len - 18) * 3.4))))
    novelty = max(0, min(100, 76 - (banned_hits * 12) + (8 if "but" in lower_text or "however" in lower_text else 0)))
    specificity = max(0, min(100, 44 + min(40, specificity_terms * 7)))
    hook = max(0, min(100, (55 if hook_length_ok else 25) + (35 if hook_topic_match else 0)))
    cta = 88 if has_cta else 32
    if goal_key in {"spark_comments", "grow_network"} and not text.endswith("?"):
        cta = min(cta, 55)

    score = int(round((clarity * 0.24) + (novelty * 0.2) + (specificity * 0.2) + (hook * 0.2) + (cta * 0.16)))
    return {
        "score": max(0, min(100, score)),
        "clarity": clarity,
        "novelty": novelty,
        "specificity": specificity,
        "hook": hook,
        "cta": cta,
        "issues": [],
    }


DEFAULT_PRICES = {
    "google": {"input_per_million": 0.35, "output_per_million": 1.05},
    "openai": {"input_per_million": 0.60, "output_per_million": 2.40},
    "claude": {"input_per_million": 3.00, "output_per_million": 15.00},
    "deepseek": {"input_per_million": 0.27, "output_per_million": 1.10},
    "xai": {"input_per_million": 2.00, "output_per_million": 10.00},
}


def load_price_table() -> Dict[str, Dict[str, float]]:
    raw = (os.getenv("AB_PRICE_JSON") or "").strip()
    if not raw:
        return DEFAULT_PRICES
    try:
        parsed = json.loads(raw)
        merged = {**DEFAULT_PRICES}
        for provider, row in parsed.items():
            if not isinstance(row, dict):
                continue
            merged[provider] = {
                "input_per_million": float(row.get("input_per_million", DEFAULT_PRICES.get(provider, {}).get("input_per_million", 0.0))),
                "output_per_million": float(row.get("output_per_million", DEFAULT_PRICES.get(provider, {}).get("output_per_million", 0.0))),
            }
        return merged
    except Exception:
        return DEFAULT_PRICES


def estimate_cost_usd(provider: str, usage: dict, price_table: dict) -> float:
    row = price_table.get(provider, {})
    in_price = float(row.get("input_per_million", 0.0))
    out_price = float(row.get("output_per_million", 0.0))
    prompt_tokens = int((usage or {}).get("prompt_tokens", 0) or 0)
    completion_tokens = int((usage or {}).get("completion_tokens", 0) or 0)
    return (prompt_tokens / 1_000_000) * in_price + (completion_tokens / 1_000_000) * out_price


@dataclass
class PromptSpec:
    id: str
    industry: str
    role: str
    tone: str
    goal_key: str
    topic: str


def build_prompt_pool(target_count: int, seed: int) -> List[PromptSpec]:
    random.seed(seed)

    industries = ["SaaS", "GenAI", "Web3", "E-commerce", "Supply Chain", "FinTech", "Healthcare"]
    roles = ["CEO", "CTO", "Marketing Lead", "Ops Leader", "Product Manager", "Sales Lead"]
    tones = ["professional", "conversational", "authoritative", "contrarian", "storytelling", "educational"]
    goals = ["spark_comments", "build_authority", "educate_audience", "generate_leads", "grow_network", "brand_awareness"]
    topics = [
        "hiring strategy", "onboarding", "product launch", "retention", "pricing", "demand forecasting",
        "customer onboarding", "AI workflow", "team productivity", "technical debt", "go-to-market", "ops automation",
        "market trend", "cost optimization", "community growth", "compliance", "quality control", "founder lessons",
    ]

    combinations: List[PromptSpec] = []
    idx = 1
    for industry in industries:
        for role in roles:
            for tone in tones:
                for goal in goals:
                    topic = random.choice(topics)
                    combinations.append(PromptSpec(
                        id=f"p_{idx:04d}",
                        industry=industry,
                        role=role,
                        tone=tone,
                        goal_key=goal,
                        topic=topic,
                    ))
                    idx += 1

    random.shuffle(combinations)
    return combinations[:target_count]


def build_generation_prompt(spec: PromptSpec) -> str:
    return f"""Write a LinkedIn post.

Context:
- Industry: {spec.industry}
- Role: {spec.role}
- Tone: {spec.tone}
- Goal: {spec.goal_key}
- Topic: {spec.topic}

Hard rules:
- 130-210 words
- Hook under 120 chars
- 2-3 short paragraphs
- End with one CTA/question
- No hashtags in body
- Avoid generic buzzwords

Output only the final post text."""


def summarize_rows(rows: List[dict], provider: str) -> dict:
    subset = [r for r in rows if r.get("provider") == provider]
    if not subset:
        return {"provider": provider, "count": 0}
    return {
        "provider": provider,
        "count": len(subset),
        "avg_score": round(statistics.mean(r.get("quality_score", 0) for r in subset), 2),
        "p50_score": round(statistics.median(r.get("quality_score", 0) for r in subset), 2),
        "avg_latency_ms": round(statistics.mean(r.get("latency_ms", 0) for r in subset), 1),
        "avg_cost_usd": round(statistics.mean(r.get("cost_usd", 0.0) for r in subset), 6),
        "total_cost_usd": round(sum(r.get("cost_usd", 0.0) for r in subset), 4),
        "error_rate": round(sum(1 for r in subset if not r.get("ok")) / len(subset), 4),
    }


def run_eval(prompts: List[PromptSpec], providers: List[str], output_dir: Path, dry_run: bool) -> Tuple[List[dict], List[dict]]:
    price_table = load_price_table()
    rows: List[dict] = []

    for i, spec in enumerate(prompts, start=1):
        prompt = build_generation_prompt(spec)
        for provider in providers:
            entry = {
                "prompt_id": spec.id,
                "provider": provider,
                "ok": False,
                "quality_score": 0,
                "latency_ms": 0,
                "cost_usd": 0.0,
                "error": "",
                "industry": spec.industry,
                "role": spec.role,
                "tone": spec.tone,
                "goal_key": spec.goal_key,
                "topic": spec.topic,
            }

            if dry_run:
                entry["ok"] = True
                entry["error"] = "dry-run"
                rows.append(entry)
                continue

            try:
                ai = AIProvider(provider=provider)
                result = ai.generate(
                    prompt,
                    max_tokens=420,
                    temperature=0.35,
                    task="generate",
                    provider=provider,
                )
                text = (result.get("text") or "").strip()
                quality = post_contract_heuristics(text, spec.topic, spec.goal_key)
                usage = result.get("usage") or {}
                cost = estimate_cost_usd(provider, usage, price_table)

                entry.update({
                    "ok": True,
                    "model": result.get("model", ""),
                    "latency_ms": int(result.get("latency_ms", 0) or 0),
                    "quality_score": int(quality.get("score", 0) or 0),
                    "clarity": int(quality.get("clarity", 0) or 0),
                    "novelty": int(quality.get("novelty", 0) or 0),
                    "specificity": int(quality.get("specificity", 0) or 0),
                    "hook": int(quality.get("hook", 0) or 0),
                    "cta": int(quality.get("cta", 0) or 0),
                    "prompt_tokens": int(usage.get("prompt_tokens", 0) or 0),
                    "completion_tokens": int(usage.get("completion_tokens", 0) or 0),
                    "total_tokens": int(usage.get("total_tokens", 0) or 0),
                    "cost_usd": round(cost, 8),
                    "text_preview": text[:220],
                })
            except Exception as exc:
                entry["error"] = str(exc)

            rows.append(entry)

        if i % 20 == 0:
            print(f"Processed {i}/{len(prompts)} prompts...")

    summary = [summarize_rows(rows, provider) for provider in providers]

    output_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    json_path = output_dir / f"ab_eval_rows_{ts}.json"
    csv_path = output_dir / f"ab_eval_rows_{ts}.csv"
    summary_path = output_dir / f"ab_eval_summary_{ts}.json"

    with open(json_path, "w", encoding="utf-8") as fh:
        json.dump(rows, fh, indent=2, ensure_ascii=False)

    headers = sorted({key for row in rows for key in row.keys()})
    with open(csv_path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)

    with open(summary_path, "w", encoding="utf-8") as fh:
        json.dump({"summary": summary}, fh, indent=2)

    print(f"Saved rows JSON: {json_path}")
    print(f"Saved rows CSV : {csv_path}")
    print(f"Saved summary  : {summary_path}")

    return rows, summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Run model A/B eval for LinkedIn generation")
    parser.add_argument("--prompts", type=int, default=300, help="Number of prompts to test")
    parser.add_argument("--providers", type=str, default="google,openai,claude", help="Comma-separated providers")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--output-dir", type=str, default="benchmarks/results", help="Output directory")
    parser.add_argument("--dry-run", action="store_true", help="Skip live provider calls")
    args = parser.parse_args()

    providers = [p.strip().lower() for p in args.providers.split(",") if p.strip()]
    if not providers:
        print("No providers specified")
        return 1

    prompts = build_prompt_pool(args.prompts, args.seed)
    print(f"Generated prompt pool: {len(prompts)} prompts")
    print(f"Providers: {providers}")
    print(f"Dry-run: {args.dry_run}")

    _, summary = run_eval(prompts, providers, Path(args.output_dir), args.dry_run)

    print("\n=== Summary ===")
    for row in summary:
        print(json.dumps(row, ensure_ascii=False))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
