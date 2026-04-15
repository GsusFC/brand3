"""Configuration for Brand3 Scoring."""

import os
import json
from pathlib import Path

# Try loading .env file
env_file = Path(__file__).parent.parent / ".env"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())

# API Keys
FIRECRAWL_API_KEY = os.environ.get("FIRECRAWL_API_KEY", "")
EXA_API_KEY = os.environ.get("EXA_API_KEY", "")

# Single LLM provider. Defaults to Google AI Studio (OpenAI-compatible),
# but any OpenAI-compatible endpoint works by overriding BRAND3_LLM_BASE_URL
# + BRAND3_LLM_API_KEY. Accepts common Google/OpenRouter env names as fallback.
BRAND3_LLM_API_KEY = (
    os.environ.get("BRAND3_LLM_API_KEY")
    or os.environ.get("GEMINI_API_KEY")
    or os.environ.get("GOOGLE_API_KEY")
    or os.environ.get("OPENROUTER_API_KEY", "")
)

# Scoring defaults
DEFAULT_NUM_EXA_RESULTS = 10
MAX_WEB_SCRAPE_CHARS = 50000
MAX_COMPETITORS = 5
MAX_COMPETITOR_SCRAPE_CHARS = 30000
BRAND3_DB_PATH = os.environ.get(
    "BRAND3_DB_PATH",
    str(Path(__file__).parent.parent / "data" / "brand3.sqlite3"),
)
BRAND3_CACHE_TTL_HOURS = int(os.environ.get("BRAND3_CACHE_TTL_HOURS", "24"))
BRAND3_NICHE_AUTO_APPLY_MIN_CONFIDENCE = float(
    os.environ.get("BRAND3_NICHE_AUTO_APPLY_MIN_CONFIDENCE", "0.65")
)
BRAND3_PROMOTION_MAX_COMPOSITE_DROP = float(
    os.environ.get("BRAND3_PROMOTION_MAX_COMPOSITE_DROP", "0")
)
BRAND3_PROMOTION_MAX_DIMENSION_DROPS = {
    "coherencia": 5.0,
    "presencia": 5.0,
    "percepcion": 5.0,
    "diferenciacion": 5.0,
    "vitalidad": 5.0,
}
_promotion_dimension_drops = os.environ.get("BRAND3_PROMOTION_MAX_DIMENSION_DROPS")
if _promotion_dimension_drops:
    try:
        BRAND3_PROMOTION_MAX_DIMENSION_DROPS.update(json.loads(_promotion_dimension_drops))
    except json.JSONDecodeError:
        pass

# LLM config (text + vision share the same provider by default)
LLM_BASE_URL = os.environ.get(
    "BRAND3_LLM_BASE_URL",
    "https://generativelanguage.googleapis.com/v1beta/openai",
)
LLM_MODEL = os.environ.get("BRAND3_LLM_MODEL", "gemini-2.5-flash")
VISION_MODEL = os.environ.get("BRAND3_VISION_MODEL", LLM_MODEL)
