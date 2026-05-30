"""Configuration for Mantraj AI LinkedIn automation."""
from typing import List, Dict

# PROFILES dict removed — was dead code only used by archived content_generator.py.
# The web app uses per-user industry/role/tone settings from the dashboard.

POST_FORMATS: List[str] = [
    # Each entry is an execution template, not just a label.
    # The LLM receives this verbatim in the prompt as FORMAT STYLE.
    "breakdown — Bold premise in the first sentence. Exactly 3 numbered points (1. / 2. / 3.), each a single concrete line with a specific detail. Close with one implication or challenge question.",
    "contrarian — First sentence states the conventional view clearly. Second sentence challenges it with a specific reason. Body explains what actually works. Close with the corrected mental model.",
    "story — Open with a specific scene, moment, or turning point (real or illustrative). Let the narrative carry the lesson naturally — do not state the moral in the middle. Single-sentence payoff at the end.",
    "insight-list — 4 to 6 standalone insights, each on its own line starting with a dash or bullet. No preamble, no filler. Each insight must be a complete thought. Close with one tight sentence that ties them together.",
    "myth-busting — Name one widely-held belief about the topic (use 'The myth: ...'). Debunk it with one specific mechanism or data point. State the corrected frame explicitly. Close with the real implication.",
    "before-after — Describe a recognisable mistake or starting-state in 1-2 sentences. Then the turning point or better approach in 2-3 sentences. Close with the transferable lesson. Make the contrast vivid and concrete.",
    "question-first — Open with an uncomfortable or thought-provoking question about the topic. Answer it directly in 2 short paragraphs. End with a follow-up question that invites debate or reflection.",
    "data-angle — Lead with a specific metric, ratio, or measurable observation from the domain. Explain what it reveals in plain language. Draw one sharp, unexpected conclusion. Keep it under 200 words total.",
]

BRAND_VOICE: Dict[str, str] = {
    "tone": "Professional, approachable, and helpful",
    "dos": "Short paragraphs, actionable tips, clear CTAs, human examples",
    "donts": "Overly salesy language, long dense paragraphs, vague claims",
}

LINKEDIN_BEST_PRACTICES: Dict[str, int] = {
    "min_length": 150,
    "max_length": 300,
}

DEFAULT_SCHEDULE = {"hour": 11, "minute": 0}

# Default profile key to use. Can be overridden by env var CONTENT_PROFILE
DEFAULT_PROFILE = "velank"


DEFAULT_SCHEDULE = {"hour": 11, "minute": 0}
