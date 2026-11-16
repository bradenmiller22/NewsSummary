"""Tag stories with topic / region / team. Owner: Braden.

Candidate tools from proposal: BGE-M3 embeddings or Gemini 3.5 Flash-Lite.
"""
from app.models import Article, Story

REGIONS = ["international", "national", "state", "local"]


def tag(stories: list[Story], articles: dict[int, Article]) -> list[Story]:
    # TODO: LLM or embedding-based tagging. Return JSON tags per story.
    for s in stories:
        if not s.region:
            s.region = "national"
    return stories
