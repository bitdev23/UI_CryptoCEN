"""Configuration for Mantraj AI LinkedIn automation."""
from typing import List, Dict

# PROFILES dict removed — was dead code only used by archived content_generator.py.
# The web app uses per-user industry/role/tone settings from the dashboard.

POST_FORMATS: List[str] = [
    "educational",
    "question",
    "story",
    "list",
    "myth-busting",
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
