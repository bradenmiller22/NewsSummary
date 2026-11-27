"""Central settings. Every stage reads config from here, never from os.environ directly."""
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT / ".env"
load_dotenv(ENV_PATH)


def _get(name: str, default: str = "") -> str:
    return os.getenv(name, default)


# API keys
ADMIN_PASSWORD = _get("ADMIN_PASSWORD")
NEWS_PROVIDERS = _get("NEWS_PROVIDERS", "newsapi, currentsapi").split(",")
ANTHROPIC_API_KEY = _get("ANTHROPIC_API_KEY")
OPENAI_API_KEY = _get("OPENAI_API_KEY")

YOUTUBE_API_KEY = _get("YOUTUBE_API_KEY")
ELEVENLABS_API_KEY = _get("ELEVENLABS_API_KEY")

# Models
PROFILE_MODEL = _get("PROFILE_MODEL", "claude-haiku-5-5")
SUMMARIZER_MODEL = _get("SUMMARIZER_MODEL", "claude-sonnet-5-5")
HIGHLIGHTS_MODEL = _get("HIGHLIGHTS_MODEL", "claude-haiku-5-5")
FACTCHECK_MODEL = _get("FACTCHECK_MODEL", "gpt-6")
TTS_MODEL = _get("TTS_MODEL", "gpt-4o-mini-tts")
EMBEDDING_MODEL = _get("EMBEDDING_MODEL", "BAAI/bge-m3")

# App
DATABASE_PATH = ROOT / _get("DATABASE_PATH", "data/daily_brief.db")
STORIES_PER_DIGEST = int(_get("STORIES_PER_DIGEST", "15"))
OFFLINE_MODE = _get("OFFLINE_MODE", "1") == "1"

# Feeds / topics collected each day (4-5 topics per proposal)
NEWS_TOPICS = ["world", "nation", "business", "technology", "sports"]
RSS_FEEDS: list[str] = [
    # TODO(Eric): add local / state feeds, e.g. Iowa outlets
]
SPORTS_LEAGUES = ["nfl", "nba", "mlb", "ncaafb"]
