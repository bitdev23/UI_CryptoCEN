#!/usr/bin/env python3
"""
Export real generated posts from your app for benchmark validation.

This script reads posts from your local data store or database and
exports them as benchmark inputs.

Usage:
  # Export recent posts for testing
  python export_real_generations.py --limit 31

  # Export specific posts by ID
  python export_real_generations.py --post-ids crypto_demo,real_estate_demo

  # Export from Supabase (if configured)
  python export_real_generations.py --from-supabase --limit 31
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta


def load_posts_from_json(limit: int = 31) -> Dict[str, str]:
    """Load posts from local JSON file (data/posts.json)."""
    posts_file = Path("data/posts.json")
    if not posts_file.exists():
        print(f"⚠️  Posts file not found: {posts_file}")
        return {}

    try:
        with posts_file.open("r", encoding="utf-8") as f:
            posts = json.load(f)
            if not isinstance(posts, list):
                posts = posts.get("posts", [])

        # Map posts to case_id -> content
        # Using post topic/industry as identifier if available
        outputs: Dict[str, str] = {}
        for i, post in enumerate(posts[-limit:]):  # Get recent N posts
            post_id = post.get("id") or f"post_{i}"
            content = post.get("content") or post.get("text") or post.get("post")
            if content:
                outputs[str(post_id)] = str(content).strip()

        print(f"✅ Loaded {len(outputs)} posts from {posts_file}")
        return outputs
    except Exception as e:
        print(f"❌ Error loading posts from JSON: {e}")
        return {}


def load_posts_from_supabase(limit: int = 31) -> Dict[str, str]:
    """Load posts from Supabase database."""
    try:
        from database.db_helper import get_db

        db = get_db()
        # Query recent posts from system_logs or posts table
        # This is an example - adjust based on your schema
        try:
            posts = db.query(
                f"SELECT id, content, topic, industry FROM posts ORDER BY created_at DESC LIMIT {limit}"
            )
        except Exception:
            # Fallback: try system_logs
            posts = db.query(
                f"SELECT id, metadata FROM system_logs WHERE type='post_generated' ORDER BY created_at DESC LIMIT {limit}"
            )
            posts = [
                {
                    "id": p.get("id", f"log_{i}"),
                    "content": (p.get("metadata") or {}).get("content", ""),
                }
                for i, p in enumerate(posts)
            ]

        outputs: Dict[str, str] = {}
        for post in posts:
            post_id = post.get("id") or "unknown"
            content = post.get("content") or post.get("text")
            if content:
                outputs[str(post_id)] = str(content).strip()

        print(f"✅ Loaded {len(outputs)} posts from Supabase")
        return outputs
    except Exception as e:
        print(f"⚠️  Could not load from Supabase: {e}")
        return {}


def map_to_benchmark_cases(posts: Dict[str, str]) -> Dict[str, str]:
    """
    Map generic posts to specific benchmark cases by analyzing content.

    This matches posts to case IDs based on keywords in the content.
    """
    case_keywords = {
        "crypto_types_strict": ["utility tokens", "security tokens", "stablecoins"],
        "crypto_defi_strategy": ["defi", "yield", "farming", "liquidity"],
        "crypto_btc_market": ["bitcoin", "btc", "market", "cycle"],
        "saas_pricing_balanced": ["pricing", "plg", "activation", "retention"],
        "saas_customer_retention": ["churn", "retention", "onboarding"],
        "saas_team_scaling": ["team", "scaling", "engineering"],
        "healthcare_ops_creative": ["patient", "scheduling", "no-show"],
        "healthcare_staff_retention": ["nurse", "staff", "retention"],
        "healthcare_patient_experience": ["patient", "digital", "experience"],
        "real_estate_roi_intro": ["real estate", "roi", "neighborhood"],
        "real_estate_investment": ["investment", "real estate", "market"],
        "real_estate_remote_work": ["remote", "commercial", "real estate"],
        "ecommerce_conversion": ["checkout", "conversion", "ecommerce"],
        "ecommerce_personalization": ["personalization", "aov", "recommendation"],
        "ecommerce_retention": ["loyalty", "retention", "repeat"],
        "fintech_compliance": ["compliance", "regulatory", "fintech"],
        "fintech_api_integration": ["api", "payment", "integration"],
        "mfg_supply_chain": ["supply chain", "manufacturing", "optimization"],
        "mfg_lean_ops": ["lean", "manufacturing", "waste"],
        "media_content_strategy": ["content", "audience", "strategy"],
        "media_monetization": ["monetization", "revenue", "diversify"],
        "b2b_sales_process": ["sales", "enablement", "cycle"],
        "b2b_account_management": ["account management", "enterprise", "growth"],
        "nonprofit_fundraising": ["donor", "fundraising", "engagement"],
        "nonprofit_operations": ["nonprofit", "impact", "scaling"],
        "edtech_engagement": ["student", "engagement", "learning"],
        "edtech_outcomes": ["learning", "outcomes", "data"],
        "travel_personalization": ["personalization", "guest", "hospitality"],
        "travel_sustainability": ["sustainability", "tourism", "environment"],
        "enterprise_security_strict": ["security", "zero-trust", "enterprise"],
        "enterprise_cloud_migration": ["cloud", "migration", "strategy"],
    }

    mapped: Dict[str, str] = {}
    for post_id, content in posts.items():
        content_lower = content.lower()
        for case_id, keywords in case_keywords.items():
            if any(kw.lower() in content_lower for kw in keywords):
                mapped[case_id] = content
                break

    print(f"✅ Mapped {len(mapped)} posts to benchmark cases")
    return mapped


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export real generated posts for benchmark validation"
    )
    parser.add_argument(
        "--limit", type=int, default=31, help="Number of recent posts to export"
    )
    parser.add_argument(
        "--post-ids",
        type=str,
        help="Comma-separated post IDs to export (overrides --limit)",
    )
    parser.add_argument(
        "--from-supabase",
        action="store_true",
        help="Load from Supabase instead of local JSON",
    )
    parser.add_argument(
        "--output",
        default="benchmarks/results/latest_generation_outputs.json",
        help="Output file path",
    )
    parser.add_argument(
        "--auto-map",
        action="store_true",
        default=True,
        help="Automatically map posts to benchmark cases (default: True)",
    )
    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("EXPORTING REAL GENERATION OUTPUTS FOR BENCHMARK")
    print("=" * 60 + "\n")

    # Load posts
    if args.from_supabase:
        posts = load_posts_from_supabase(args.limit)
    else:
        posts = load_posts_from_json(args.limit)

    if not posts:
        print("❌ No posts found to export")
        return

    # Map to benchmark cases if auto-map enabled
    if args.auto_map and len(posts) < 31:
        outputs = map_to_benchmark_cases(posts)
    else:
        outputs = posts

    if not outputs:
        print("❌ Could not map any posts to benchmark cases")
        return

    # Save outputs
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(outputs, f, indent=2, ensure_ascii=False)

    print(f"✅ Exported {len(outputs)} posts to {output_path}\n")
    print("=" * 60)
    print("Next steps:")
    print(f"  git add {args.output}")
    print(f"  git commit -m 'Add real generation outputs for CI validation'")
    print("  git push origin main")
    print("\nGitHub CI will automatically validate these outputs against")
    print("the benchmark suite and show the quality report.")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
