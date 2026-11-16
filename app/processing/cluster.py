"""Group articles about the same event into Stories. Owner: Braden.

Plan: embed title + description with BGE-M3, then group articles whose cosine
similarity is above a threshold (start ~0.8, tune on real data).
"""
from app.models import Article, Story


def cluster(articles: list[Article]) -> list[Story]:
    # TODO: replace with embedding-based clustering.
    # Placeholder: every article is its own story.
    return [
        Story(id=i, headline=a.title, article_ids=[a.id] if a.id else [], tags=[a.topic])
        for i, a in enumerate(articles, start=1)
    ]
