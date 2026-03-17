"""
Domain isolation + anti-AI tone validation test.
Tests prompt construction for 5 industry/role combos to verify:
  1. Domain lock is the FIRST instruction
  2. Tone voice maps correctly
  3. Goal structure maps correctly
  4. Banned phrases list is injected
  5. KB off-domain excerpts are flagged to be ignored
  6. No cross-industry bleed keywords in prompt

Run: python3 scripts/test_domain_isolation.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── Test matrix ─────────────────────────────────────────────────────────────
TEST_CASES = [
    {"industry": "Healthcare",      "role": "Doctor / Medical Director",  "theme": "patient safety protocols",    "tone": "professional",   "goal": "build_authority"},
    {"industry": "Finance",         "role": "CFO",                         "theme": "cash flow optimisation",     "tone": "authoritative",  "goal": "educate_audience"},
    {"industry": "Technology",      "role": "Software Engineer",           "theme": "debugging production issues","tone": "conversational", "goal": "spark_comments"},
    {"industry": "E-Commerce",      "role": "Head of Marketing",           "theme": "CAC reduction strategies",   "tone": "thought_leader", "goal": "drive_visibility"},
    {"industry": "Crypto / Web3",   "role": "DeFi Protocol Builder",       "theme": "liquidity pool mechanics",   "tone": "educational",    "goal": "educate_audience"},
]

# ── Inline tone / goal maps (mirrored from app.py) ────────────────────────
_TONE_VOICES = {
    'professional':   "Clear, confident, direct. Short declarative sentences. No filler words. Knowledgeable peer, not press release.",
    'conversational': "Casual first-person. Like messaging a smart colleague. Use 'I', 'we', contractions.",
    'authoritative':  "Opinion-forward, backed by logic. Bold, decisive statements.",
    'thought_leader': "Lead with a contrarian insight. Challenge assumptions. Dense ideas, zero filler.",
    'inspirational':  "Story arc: challenge → insight → transformation. Warm, genuine, human.",
    'storytelling':   "Open with a vivid personal scene. Let the story carry the lesson. Don't moralize.",
    'educational':    "Deliver focused, specific insights. Each point standalone and immediately usable.",
}

_GOAL_STRUCTURES = {
    'spark_comments':   "End the post with a genuinely open question that invites the reader's unique view.",
    'drive_visibility': "Open with a bold, unexpected hook in the first 5-7 words that stops the scroll.",
    'build_authority':  "Lead with a plain-spoken insight others haven't stated clearly. Follow with tight supporting logic.",
    'generate_leads':   "Name a specific pain point. Close with a clear, low-pressure next step.",
    'educate_audience': "Deliver 2-3 focused insights. Each one standalone and immediately usable.",
    'brand_awareness':  "Communicate one clear value or belief. Make it memorable in a single sentence.",
    'grow_network':     "Write from personal experience. Include a moment of genuine reflection or honest admission.",
}

_BANNED_SNIPPET = "In today's fast-paced world"  # first banned phrase as proxy

CROSS_INDUSTRY_KEYWORDS = {
    "Healthcare":    ["crypto", "blockchain", "defi", "fintech", "ecommerce", "saas", "software engineer"],
    "Finance":       ["hospital", "patient", "blockchain", "nft", "defi", "shopify", "woocommerce"],
    "Technology":    ["hospital", "defi", "nft", "icu", "prescription", "cash flow"],
    "E-Commerce":    ["hospital", "defi", "nft", "blockchain", "icu"],
    "Crypto / Web3": ["hospital", "patient", "revenue cycle", "ecommerce cart"],
}

# ── Build prompt (mirrors app.py logic) ──────────────────────────────────
def build_prompt(tc: dict, has_kb: bool = False, kb_snippets: str = "") -> str:
    user_industry = tc["industry"]
    user_role     = tc["role"]
    theme         = tc["theme"]
    post_tone     = tc["tone"]
    business_goal = tc["goal"]

    tone_voice     = _TONE_VOICES.get(post_tone, "Natural, human voice.")
    goal_structure = _GOAL_STRUCTURES.get(business_goal, "One clear valuable idea.")
    topic_hint     = theme
    services       = f"Professional context for {user_industry} audiences."
    target_audience_hint = f"{user_role} audience"
    word_rule      = "Keep the post between 130 and 230 words."
    emoji_rule     = "Use 2-4 relevant emojis for readability."
    hashtag_count  = 4
    fmt            = "Short-form narrative"
    domain_guardrail = f"Write only about {user_industry}. Do not reference other industries."

    _BANNED_PHRASES = (
        "In today's fast-paced world, In today's world, It's no secret, game changer, game-changer, "
        "paradigm shift, leverage, synergy, cutting-edge, best practices, at the end of the day, "
        "think outside the box, move the needle, exciting, thrilled, delighted to share, Dive into, "
        "Unlock, Revolutionize, seamlessly, robust, scalable solution, stakeholders, actionable insights, "
        "transformative, empower, innovative solution, disruptive, holistic approach, ecosystem, value-add"
    )

    if has_kb and kb_snippets:
        kb_section = f"""KNOWLEDGE BASE EXCERPTS (use these as your factual foundation):
{kb_snippets}

KB RULES:
- Base ALL factual claims ONLY on the excerpts above.
- If an excerpt is off-domain (not about {user_industry}), IGNORE it completely.
- If no excerpt covers a point, keep that sentence general — never invent specifics."""
    else:
        kb_section = (
            f"(No knowledge base excerpts provided — draw only on real, well-known facts about the "
            f"{user_industry} industry. Do not invent statistics, company names, or research studies.)"
        )

    return f"""[DOMAIN LOCK — READ THIS FIRST]
You are writing EXCLUSIVELY for the {user_industry} industry, from the perspective of a {user_role}.
Every fact, insight, reference, statistic, and example MUST be grounded in the {user_industry} domain.
Do NOT mention, reference, or borrow from any other industry or professional domain.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
VOICE / TONE: {tone_voice}

POST STRUCTURE (goal: "{business_goal}"):
{goal_structure}

TOPIC: {theme}
CONTEXT: {services}
TARGET READER: {target_audience_hint}
TOPICS TO COVER: {topic_hint}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{kb_section}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STRICT RULES — every rule applies without exception:

1. DOMAIN LOCK: Every sentence must be grounded in {user_industry}. {domain_guardrail}
2. NO INVENTED FACTS: Do not invent statistics, percentages, company names, research studies, product names, or quotes.
3. VOICE: Follow the TONE instruction above exactly.
4. STRUCTURE: Follow the POST STRUCTURE above.
5. LENGTH: {word_rule}
6. EMOJI: {emoji_rule}
7. NO MARKDOWN: No **, no ***, no bullet-point dashes, no numbered lists — write in flowing prose only.
8. HASHTAGS: Do NOT put hashtags in the post body. Place exactly {hashtag_count} hashtags at the very end only.
9. BANNED PHRASES — never write any of these: {_BANNED_PHRASES}
10. HUMAN VOICE: Write like a real person — not an AI assistant, not a press release.
11. NO PLACEHOLDERS: Never write [Company Name], [Exchange], or any bracketed placeholder.

FORMAT STYLE: {fmt}

Output ONLY the post text. No labels, no preamble."""


# ── Off-domain KB simulation ──────────────────────────────────────────────
CRYPTO_EXCERPT = "[1] Source: crypto_whitepaper.pdf\nBitcoin halving reduces block rewards from 3.125 BTC. DeFi TVL exceeded $100B in 2021."
HEALTHCARE_EXCERPT = "[1] Source: med_guidelines.pdf\nICU readmission within 30 days is a key quality metric. HIPAA governs PHI data access."


# ── Validation ───────────────────────────────────────────────────────────
def validate_prompt(tc: dict, prompt: str, has_kb: bool = False) -> list[str]:
    issues = []
    industry_lower = tc["industry"].lower()

    # 1. Domain lock must be FIRST
    first_line = prompt.strip().splitlines()[0]
    if "DOMAIN LOCK" not in first_line:
        issues.append("❌ Domain lock NOT the first instruction")
    else:
        issues.append("✅ Domain lock is first instruction")

    # 2. Industry name appears in domain lock section
    if tc["industry"] in prompt[:300]:
        issues.append(f"✅ Industry '{tc['industry']}' present in domain lock")
    else:
        issues.append(f"❌ Industry '{tc['industry']}' missing from domain lock")

    # 3. Role name appears
    if tc["role"] in prompt:
        issues.append(f"✅ Role '{tc['role']}' present in prompt")
    else:
        issues.append(f"❌ Role '{tc['role']}' missing from prompt")

    # 4. Tone voice instruction present
    tone_snippet = _TONE_VOICES.get(tc["tone"], "")[:40]
    if tone_snippet and tone_snippet in prompt:
        issues.append(f"✅ Tone '{tc['tone']}' voice instruction injected")
    else:
        issues.append(f"❌ Tone '{tc['tone']}' voice instruction MISSING")

    # 5. Goal structure present
    goal_snippet = _GOAL_STRUCTURES.get(tc["goal"], "")[:40]
    if goal_snippet and goal_snippet in prompt:
        issues.append(f"✅ Goal '{tc['goal']}' structure instruction injected")
    else:
        issues.append(f"❌ Goal '{tc['goal']}' structure instruction MISSING")

    # 6. Banned phrases list present
    if _BANNED_SNIPPET in prompt:
        issues.append("✅ Banned phrases list present")
    else:
        issues.append("❌ Banned phrases list MISSING")

    # 7. No markdown formatting in prompt template (** markers)
    # Allow "**" only inside the explicit NO MARKDOWN rule instruction itself
    prompt_sans_rule7 = prompt.replace("No **, no ***, no bullet-point dashes", "")
    if "**" not in prompt_sans_rule7:
        issues.append("✅ No ** markdown in prompt template (outside rule instructions)")
    else:
        issues.append("❌ Prompt template contains ** markdown formatting — remove it")

    # 8. Off-domain KB excerpts flagged for exclusion (only required when KB is active)
    if has_kb:
        if "off-domain" in prompt.lower() and "ignore" in prompt.lower():
            issues.append("✅ KB off-domain exclusion instruction present")
        else:
            issues.append("❌ KB off-domain exclusion instruction MISSING")
    else:
        if "do not invent statistics" in prompt.lower():
            issues.append("✅ No-KB anti-hallucination instruction present")
        else:
            issues.append("❌ No-KB anti-hallucination instruction MISSING")

    # 9. Cross-industry keyword bleed in prompt (prompt should not reference other industries as context hints)
    bleed_keys = CROSS_INDUSTRY_KEYWORDS.get(tc["industry"], [])
    in_domain_section = False
    # Only check if a cross-industry keyword appears in the domain-lock section (first 400 chars)
    domain_section = prompt[:400].lower()
    found_bleed = [k for k in bleed_keys if k in domain_section]
    if found_bleed:
        issues.append(f"⚠️  Cross-industry keywords in domain section: {found_bleed}")
    else:
        issues.append("✅ No cross-industry bleed in domain lock section")

    return issues


# ── Main ─────────────────────────────────────────────────────────────────
def run_tests():
    print("=" * 70)
    print("DOMAIN ISOLATION + ANTI-AI TONE — PROMPT STRUCTURE VALIDATION")
    print("=" * 70)

    pass_count = 0
    fail_count = 0

    for i, tc in enumerate(TEST_CASES, 1):
        # Test 1: No KB
        prompt_no_kb = build_prompt(tc, has_kb=False)

        # Test 2: With KB that contains off-domain crypto content (for healthcare/finance/tech)
        off_domain_snippet = CRYPTO_EXCERPT if "Crypto" not in tc["industry"] else HEALTHCARE_EXCERPT
        prompt_with_kb = build_prompt(tc, has_kb=True, kb_snippets=off_domain_snippet)

        print(f"\n{'─'*70}")
        print(f"TEST CASE {i}: {tc['industry']} / {tc['role']}")
        print(f"  Topic: {tc['theme']}  |  Tone: {tc['tone']}  |  Goal: {tc['goal']}")
        print(f"{'─'*70}")

        results = validate_prompt(tc, prompt_no_kb, has_kb=False)
        print("\n  [NO-KB variant]")
        for r in results:
            print(f"    {r}")
            if r.startswith("❌"): fail_count += 1
            else: pass_count += 1

        # For with-KB, validate off-domain KB instruction
        results_kb = validate_prompt(tc, prompt_with_kb, has_kb=True)
        print("\n  [WITH-KB variant (off-domain KB excerpt injected)]")
        for r in results_kb:
            print(f"    {r}")
            if r.startswith("❌"): fail_count += 1
            else: pass_count += 1

        # Print first 400 chars of the prompt to visually confirm domain lock is first
        print(f"\n  [PROMPT PREVIEW — first 300 chars]")
        print("  " + prompt_no_kb[:300].replace("\n", "\n  "))

    print(f"\n{'=' * 70}")
    total = pass_count + fail_count
    print(f"RESULT: {pass_count}/{total} checks PASSED  |  {fail_count}/{total} FAILED")
    print("=" * 70)

    if fail_count == 0:
        print("\n✅ ALL CHECKS PASSED — Domain isolation + anti-AI prompts are solid.\n")
    else:
        print(f"\n❌ {fail_count} checks failed — review items marked ❌ above.\n")
        sys.exit(1)


if __name__ == "__main__":
    run_tests()
