"""PromptBuilder — centralises all prompt templates for LinkedIn post generation.

Extracted from app.py (P2-25) to keep the monolith smaller and make prompt
engineering changes easier to review in isolation.
"""

from __future__ import annotations


# ── Constants ─────────────────────────────────────────────────────────────────

BANNED_PHRASES = (
    "In today's fast-paced world, In today's world, It's no secret, game changer, game-changer, "
    "paradigm shift, leverage, synergy, cutting-edge, best practices, at the end of the day, "
    "think outside the box, move the needle, exciting, thrilled, delighted to share, I am proud to share, "
    "Dive into, Unlock, Revolutionize, seamlessly, robust, scalable solution, stakeholders, "
    "actionable insights, transformative, empower, journey, innovative solution, disruptive, "
    "holistic approach, ecosystem, value-add, going forward, circle back, take this to the next level"
)

TONE_VOICES = {
    'professional':   "Clear, confident, direct. Short declarative sentences. No filler words. Sound like a knowledgeable peer, not a press release.",
    'conversational': "Casual first-person. Like messaging a smart colleague. Use 'I', 'we', contractions. Short sentences. Real talk, not corporate jargon.",
    'authoritative':  "Opinion-forward, backed by logic. Make bold, decisive statements. Confident — not arrogant, but certain.",
    'contrarian':     "Challenge conventional wisdom with evidence-backed arguments. Lead with what most people get wrong. Make the reader rethink their assumptions.",
    'storytelling':   "Open with a vivid personal scene or moment. Let the story carry the lesson naturally. Don't moralize — let the reader draw their own conclusion.",
    'educational':    "Deliver focused, specific insights. Each point standalone and immediately usable. Teach, don't preach.",
    'crypto_native':  "On-chain evidence over narrative. Skeptical of hype, respectful of mechanism. Cite protocols, metrics, and observable on-chain patterns. "
                      "Sound like someone who has actually run the numbers — not a marketer. Plain sentences, technical precision without jargon overload. "
                      "Distrust vaporware framing; honour concrete deployed code.",
}

TONE_TEMPLATES = {
    'professional': (
        "- Hook pattern: sharp professional insight in one line.\n"
        "- Body movement: problem -> practical implication -> concrete action.\n"
        "- Sentence rhythm: mostly short declarative lines.\n"
        "- Lexicon: precise business language, zero hype."
    ),
    'conversational': (
        "- Hook pattern: candid first-person observation.\n"
        "- Body movement: what I noticed -> why it matters -> what I changed.\n"
        "- Sentence rhythm: short, natural, chat-like cadence.\n"
        "- Lexicon: simple language, contractions allowed."
    ),
    'authoritative': (
        "- Hook pattern: decisive claim with strong angle.\n"
        "- Body movement: clear position -> evidence -> implication.\n"
        "- Sentence rhythm: compact, assertive statements.\n"
        "- Lexicon: expert terminology only where useful."
    ),
    'contrarian': (
        "- Hook pattern: what most people get wrong about the topic.\n"
        "- Body movement: challenge assumption -> explain why -> offer better frame.\n"
        "- Sentence rhythm: sharp, provocative, but reasoned.\n"
        "- Lexicon: direct language; avoid outrage framing."
    ),
    'storytelling': (
        "- Hook pattern: specific scene or moment in first line.\n"
        "- Body movement: scene -> tension -> lesson -> takeaway.\n"
        "- Sentence rhythm: mixed sentence lengths with narrative flow.\n"
        "- Lexicon: concrete sensory details over abstractions."
    ),
    'educational': (
        "- Hook pattern: clear promise of practical learning.\n"
        "- Body movement: 2-3 teachable points with real examples.\n"
        "- Sentence rhythm: concise, scannable, high-signal lines.\n"
        "- Lexicon: instructional verbs and actionable phrasing."
    ),
    'crypto_native': (
        "- Hook pattern: on-chain observation or protocol-specific claim backed by a number or mechanism.\n"
        "- Body movement: observable pattern -> why the mechanism produces it -> what it signals.\n"
        "- Sentence rhythm: terse and precise; use white space to let data breathe.\n"
        "- Lexicon: protocol names, TVL/gas/active-address metrics, on-chain verbs (deployed, executed, settled). "
        "Never use 'disruptive', 'paradigm shift', or WAGMI-style hype."
    ),
}

GOAL_STRUCTURES = {
    'spark_comments': (
        "Hook formulas — pick the best fit for the topic:\n"
        '  • "Hot take on [topic]: [specific controversial but defensible position]. Disagree?"\n'
        '  • "[Uncomfortable question about the topic most people avoid asking.]"\n'
        '  • "[Specific observation from your domain]. Does this match what you\'re seeing?"\n'
        "Structure: Bold hook → 2 short paragraphs of substance → end with a genuinely open question "
        "that invites different viewpoints. Question must NOT be yes/no."
    ),
    'drive_visibility': (
        "Hook formulas — pick the best fit for the topic:\n"
        '  • "Most [people/teams/protocols] get [topic] wrong. Here\'s the part nobody explains."\n'
        '  • "[Number] [time period] in [industry]. The [topic] insight that changed how I think about [X]:"\n'
        '  • "Everyone\'s talking about [surface angle on topic]. Nobody\'s asking the right question."\n'
        "Structure: Hook must land in first 5-7 words and stop the scroll. Body delivers on the hook's "
        "promise with specifics. Close with one sharp implication or reflection sentence."
    ),
    'build_authority': (
        "Hook formulas — pick the best fit for the topic:\n"
        '  • "The reason [widely-held belief about topic] doesn\'t hold up: [one specific reason]."\n'
        '  • "[Counterintuitive claim about topic] — and here\'s the evidence."\n'
        '  • "Stop measuring [obvious thing related to topic]. [Specific alternative] is what moves [real outcome]."\n'
        "Structure: Lead with a plain-spoken insight others haven't stated clearly. "
        "Follow with tight supporting logic or one concrete mechanism. No vague generalities."
    ),
    'generate_leads': (
        "Hook formulas — pick the best fit for the topic:\n"
        '  • "Here\'s the [topic] problem most [specific role/team] face but rarely say out loud:"\n'
        '  • "The hidden cost of [common thing in the domain]: [specific pain point]."\n'
        '  • "[Relatable scenario related to topic]. If this describes your situation, read on."\n'
        "Structure: Name a specific, recognisable pain the target audience faces. "
        "Body shows you understand the problem deeply. Close with a clear, low-pressure next step — "
        "not a pitch, a pointer."
    ),
    'educate_audience': (
        "Hook formulas — pick the best fit for the topic:\n"
        '  • "[Topic], actually explained: [one reframing sentence that cuts through jargon]."\n'
        '  • "[Topic] is misunderstood. Here\'s what you need to know:"\n'
        '  • "Everything that actually matters about [topic] — in [N] points:"\n'
        "Structure: Deliver 2-3 focused insights. Each must be standalone and immediately usable. "
        "Prefer numbered or dashed lines. Avoid vague takeaways — every point must be actionable or surprising."
    ),
    'brand_awareness': (
        "Hook formulas — pick the best fit for the topic:\n"
        '  • "[Strong belief statement about what you stand for in your domain]."\n'
        '  • "We built [thing] for one reason: [honest, specific statement of why]."\n'
        '  • "[Specific principle or value you hold]. That\'s the bar we hold ourselves to."\n'
        "Structure: Communicate one clear value or belief tied to the topic. "
        "Make it memorable in a single sentence. Body earns the belief with a concrete example or story. "
        "Do not close with a hard sell."
    ),
    'grow_network': (
        "Hook formulas — pick the best fit for the topic:\n"
        '  • "Two years ago I thought [X about topic]. I was completely wrong."\n'
        '  • "The moment [topic insight] clicked for me:"\n'
        '  • "An honest admission about [topic] that took me too long to figure out:"\n'
        "Structure: Write from genuine personal experience. Include a specific moment of reflection "
        "or an honest admission. The lesson should feel earned, not tacked on."
    ),
}


# ── Grounding level labels (must match app.py constants) ──────────────────────

GROUNDING_FULL = 'grounded'
GROUNDING_PARTIAL = 'partial'
GROUNDING_NONE = 'ungrounded'


# ── PromptBuilder class ───────────────────────────────────────────────────────

class PromptBuilder:
    """Assembles the primary generation prompt and auxiliary prompts.

    Usage::

        pb = PromptBuilder()
        prompt = pb.build_generation_prompt(
            user_industry='Fintech', user_role='CTO', theme='API security',
            ...
        )
    """

    # ------------------------------------------------------------------
    # Primary generation prompt
    # ------------------------------------------------------------------

    @staticmethod
    def resolve_tone(post_tone: str) -> tuple[str, str]:
        """Return (tone_voice, tone_template) for the given tone key."""
        key = (post_tone or '').lower()
        voice = TONE_VOICES.get(key, "Natural, human voice. Short sentences. No corporate fluff.")
        tmpl = TONE_TEMPLATES.get(key, TONE_TEMPLATES['professional'])
        return voice, tmpl

    @staticmethod
    def resolve_goal_structure(goal_key: str) -> str:
        return GOAL_STRUCTURES.get(goal_key, "Deliver one clear, valuable idea. Make it skimmable and worth the reader's time.")

    @staticmethod
    def resolve_style_clone_rules(style_clone_active: bool, style_clone_strict: bool) -> dict:
        """Return voice/structure/format/compliance rule strings."""
        if style_clone_strict:
            return {
                'voice': 'Follow the STYLE CLONE fingerprint exactly — it overrides tone guidance.',
                'structure': 'Follow the structural pattern in the STYLE CLONE block above.',
                'format': 'STYLE CLONE format rules take priority. Lists/single-line breaks are allowed when present in style clone references.',
                'compliance': '14. STYLE CLONE COMPLIANCE: The output MUST be stylistically indistinguishable from the reference posts provided above. If in doubt, re-read the references.',
            }
        elif style_clone_active:
            return {
                'voice': 'Blend the STYLE CLONE fingerprint with role and post-goal constraints. Keep role perspective primary.',
                'structure': 'Use STYLE CLONE cadence, but keep the goal-driven structure above.',
                'format': 'Prefer prose readability; style-clone line-break rhythm is allowed when it improves authenticity.',
                'compliance': '14. STYLE CLONE COMPLIANCE: Mirror the personal cadence and phrasing patterns while preserving role, domain, and goal clarity.',
            }
        else:
            return {
                'voice': 'Follow the TONE instruction above exactly.',
                'structure': 'Follow the POST STRUCTURE above.',
                'format': 'No **, no ***, no bullet-point dashes, no numbered lists — write in flowing prose only.',
                'compliance': '',
            }

    @staticmethod
    def build_generation_prompt(
        *,
        user_industry: str,
        user_role: str,
        theme: str,
        services: str,
        target_audience_hint: str,
        topic_hint: str,
        business_goal: str,
        tone_voice: str,
        tone_template: str,
        goal_structure: str,
        instruction_pack_text: str,
        style_instruction: str,
        kb_section: str,
        domain_guardrail: str,
        word_rule: str,
        emoji_rule: str,
        hashtag_count: int,
        fmt: str,
        grounding_level: str,
        voice_rule_text: str,
        structure_rule_text: str,
        format_rule_text: str,
        style_clone_compliance_rule: str,
    ) -> str:
        """Build the main LinkedIn post generation prompt."""

        return f"""[DOMAIN LOCK — READ THIS FIRST]
You are writing EXCLUSIVELY for the {user_industry} industry, from the perspective of a {user_role}.
Every fact, insight, reference, statistic, and example MUST be grounded in the {user_industry} domain.
Do NOT mention, reference, or borrow from any other industry or professional domain.

{f'''━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ROLE × INDUSTRY × GOAL PLAYBOOK (follow these closely — they define HOW you write):

{instruction_pack_text}
''' if instruction_pack_text else ''}
{style_instruction}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
VOICE / TONE: {tone_voice}

TONE EXECUTION TEMPLATE (follow exactly):
{tone_template}

POST STRUCTURE (goal: "{business_goal or 'general engagement'}"):
{goal_structure}

TOPIC — the post is about this specific subject (do not drift from it):
{theme}

BACKGROUND CONTEXT (use only as supporting colour; the post stays on the TOPIC above):
{services}

WHO WILL READ THIS (do NOT copy this into the post — it is context only):
{target_audience_hint}

OPTIONAL SUBTOPICS TO WEAVE IN:
{topic_hint}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{kb_section}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STRICT RULES — every rule applies without exception:

1. DOMAIN LOCK: Every sentence must be grounded in {user_industry}. {domain_guardrail}
2. NO INVENTED FACTS: Do not invent statistics, percentages, company names, research studies, product names, or quotes.
3. VOICE: {voice_rule_text}
4. STRUCTURE: {structure_rule_text}
5. LENGTH: {word_rule}
6. EMOJI: {emoji_rule}
7. FORMAT: {format_rule_text}
8. HASHTAGS: Do NOT put hashtags in the post body. Place exactly {hashtag_count} hashtags at the very end, after the body.
9. BANNED PHRASES — never write any of these: {BANNED_PHRASES}
10. HUMAN VOICE: Write like a real person would talk or write — not like an AI assistant, not like a press release, not like a corporate newsletter.
11. NO PLACEHOLDERS: Never write [Company Name], [Exchange], or any bracketed placeholder.
12. TOPIC ANCHOR + HOOK: The very first sentence MUST be directly about "{theme}" AND must be under 120 characters. Short, punchy, curiosity-driven. Do not open with a generic industry question or a hook about your role/team. The post is about the topic, not about you.
13. NO PROMPT ECHO: Never copy or paraphrase any instruction label from this prompt into the post. Do not use the reader description (WHO WILL READ THIS) as post copy.
14. OUTPUT CONTRACT: Structure must be: (a) Hook line, (b) 2-3 short body paragraphs, (c) final CTA/question line aligned to goal. Keep each paragraph 1-2 sentences.
15. QUALITY CONTRACT: Include at least one concrete detail (specific scenario, metric range, or named mechanism). Avoid vague generic claims.
16. GROUNDING MODE: {
    'GROUNDED — all factual claims must trace to KB excerpts above. If a point is not in the excerpts, phrase it as opinion.' if grounding_level == GROUNDING_FULL else
    'PARTIAL — some KB excerpts available. Supported points can be specific; unsupported points must use insight-only framing (no invented facts).' if grounding_level == GROUNDING_PARTIAL else
    'INSIGHT-ONLY — no KB evidence available. Every statement must be defensible as opinion, observation, or widely-accepted wisdom. Zero invented facts.'
}
{style_clone_compliance_rule}

FORMAT STYLE: {fmt}

Output ONLY the post text. No labels, no "Here is your post:", no preamble."""

    # ------------------------------------------------------------------
    # Retry / revision prompt
    # ------------------------------------------------------------------

    @staticmethod
    def build_retry_prompt(
        original_prompt: str,
        score: int,
        issues: list[str],
    ) -> str:
        feedback_issues = issues or [
            'Improve hook specificity and topic anchoring',
            'Increase clarity and concrete detail',
            'Strengthen CTA quality',
        ]
        return f"""{original_prompt}

REVISION PASS (DRAFT 2) — IMPROVE QUALITY:
- Previous draft score: {score}/100
- Fix these issues first: {'; '.join(feedback_issues[:4])}
- Keep domain lock, same topic, same goal, same tone template.
- Hook must be sharper and clearly topic-anchored.
- CTA must be specific and naturally invite response.
- Keep concrete and practical; avoid generic statements.

Output ONLY the revised post text."""

    # ------------------------------------------------------------------
    # Evaluation prompt
    # ------------------------------------------------------------------

    @staticmethod
    def build_evaluation_prompt(body: str, theme: str, goal_key: str) -> str:
        short_body = str(body or '').strip()[:1800]
        return f"""Score this LinkedIn post quickly.
Return ONLY strict JSON with integer fields 0-100:
{{"clarity":0,"novelty":0,"specificity":0,"hook":0,"cta":0,"overall":0,"issues":["..."]}}

Topic: {theme}
Goal key: {goal_key}
Post:
{short_body}
"""

    # ------------------------------------------------------------------
    # Claim-verification prompt
    # ------------------------------------------------------------------

    @staticmethod
    def build_verification_prompt(post_text: str, kb_context: str) -> str:
        return f"""You are a fact-checking assistant. Compare the LinkedIn post below against the knowledge base excerpts.

TASK: Identify any sentence in the post that makes a SPECIFIC factual claim (statistic, percentage, company name, product name, research study, named person, specific date) that is NOT supported by the excerpts below.

KNOWLEDGE BASE EXCERPTS:
{kb_context[:3000]}

POST TO VERIFY:
{post_text}

Return ONLY strict JSON (no markdown fences):
{{"has_issues": true/false, "ungrounded_claims": ["sentence 1", "sentence 2"], "rewrite_instructions": "brief guidance on how to fix"}}

If all claims are grounded or the post only contains opinions/observations, return:
{{"has_issues": false, "ungrounded_claims": [], "rewrite_instructions": ""}}"""

    # ------------------------------------------------------------------
    # Ungrounded-claim rewrite prompt
    # ------------------------------------------------------------------

    @staticmethod
    def build_rewrite_prompt(
        post_text: str,
        ungrounded_claims: list[str],
        rewrite_instructions: str,
        user_industry: str,
        user_role: str,
        kb_context: str,
    ) -> str:
        claims_list = '\n'.join(f'- {c}' for c in ungrounded_claims[:5])
        guidance = rewrite_instructions or ''

        return f"""Rewrite the LinkedIn post below to fix grounding issues.

PROBLEM: The following sentences make specific factual claims that are NOT supported by the knowledge base:
{claims_list}

{f'GUIDANCE: {guidance}' if guidance else ''}

RULES FOR REWRITE:
1. Keep the overall post structure, tone, and length the same.
2. For each problematic sentence, convert it from a hard factual claim to an insight/opinion:
   - Replace invented statistics with qualitative observations ("many teams find…", "a growing number of…")
   - Replace invented company/product names with general references ("leading platforms", "several tools in the space")
   - Replace invented research citations with experiential framing ("in my experience", "what I've seen work")
3. Keep all sentences that ARE grounded — do not change what works.
4. Stay in {user_industry} domain, {user_role} perspective.
5. Do NOT add hashtags or preamble. Output ONLY the rewritten post body.

ORIGINAL POST:
{post_text}

{f'AVAILABLE KB CONTEXT (for reference):{chr(10)}{kb_context[:1500]}' if kb_context else ''}"""

    # ------------------------------------------------------------------
    # Grounding-level prompt section
    # ------------------------------------------------------------------

    @staticmethod
    def build_grounding_rules(grounding_level: str, user_industry: str, kb_context: str) -> str:
        """Return the KB section to embed in the generation prompt."""
        if grounding_level == GROUNDING_FULL:
            return f"""KNOWLEDGE BASE EXCERPTS — YOUR ONLY SOURCE OF TRUTH:
{kb_context}

GROUNDING RULES (STRICT — GROUNDED MODE):
- Every factual claim, statistic, company name, product name, or specific example MUST come from the excerpts above.
- If you want to make a point that is NOT covered in the excerpts, phrase it as a general observation or opinion — never as a fact.
- Use phrases like "based on [topic from excerpt]" to root your points in real evidence.
- If an excerpt is off-domain (not about {user_industry}), IGNORE it completely.
- NEVER invent statistics, percentages, research studies, company names, or quotes."""

        elif grounding_level == GROUNDING_PARTIAL:
            return f"""KNOWLEDGE BASE EXCERPTS (partial match — use with care):
{kb_context}

GROUNDING RULES (PARTIAL-CONFIDENCE MODE):
- You have SOME relevant KB excerpts but coverage is incomplete.
- For points covered by excerpts: make specific claims grounded in the excerpt content.
- For points NOT covered by excerpts: use INSIGHT-ONLY framing — patterns, trade-offs, principles, and rhetorical questions. Do NOT present them as facts.
- Use hedging language for unsupported claims: "in my experience", "a common pattern", "many teams find that".
- NEVER invent statistics, percentages, research studies, company names, product names, or quotes.
- If an excerpt is off-domain (not about {user_industry}), IGNORE it completely."""

        else:  # UNGROUNDED
            return f"""(No relevant knowledge base content matched this topic.)

GROUNDING RULES (INSIGHT-ONLY MODE — NO KB AVAILABLE):
- You have NO factual evidence from the user's knowledge base for this topic.
- Write ONLY from general principles, widely-known industry patterns, and professional opinion.
- Frame every point as a perspective, observation, or question — NOT as a factual claim.
- Use language like: "I've seen teams struggle with…", "One pattern that keeps showing up…", "The question worth asking is…"
- Absolutely ZERO invented statistics, percentages, company names, product names, research studies, or quotes.
- Do NOT name specific companies, tools, or products unless they are universally known household names in {user_industry}.
- Keep every statement defensible as opinion or widely-accepted wisdom."""
