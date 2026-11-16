"""GNews API collector. Owner: Eric.

Docs: https://gnews.io/docs — free plan has a daily request cap, so fetch each
topic once per run and store results; never call GNews from the web request path.
"""
from datetime import datetime

import httpx

from app import config
from app.models import Article

BASE_URL = "https://gnews.io/api/v4/top-headlines"


def fetch_topic(topic: str, max_results: int = 10, lang: str = "en", country: str = "us") -> list[Article]:
    if config.OFFLINE_MODE or not config.GNEWS_API_KEY:
        return _fake(topic)

    params = {
        "category": topic,
        "lang": lang,
        "country": country,
        "max": max_results,
        "apikey": config.GNEWS_API_KEY,
    }
    resp = httpx.get(BASE_URL, params=params, timeout=20)
    resp.raise_for_status()

    articles = []
    for item in resp.json().get("articles", []):
        articles.append(Article(
            source="gnews",
            url=item["url"],
            title=item["title"],
            description=item.get("description", ""),
            content=item.get("content", ""),
            published_at=datetime.fromisoformat(item["publishedAt"].replace("Z", "+00:00")),
            topic=topic,
        ))
    return articles


def _fake(topic: str) -> list[Article]:
    return [
        Article(
            source="gnews",
            url=f"https://example.com/{topic}/{i}",
            title=f"Placeholder {topic} headline {i}",
            description=f"Placeholder description for {topic} story {i}.",
            content=f"Placeholder body text for {topic} story {i}.",
            topic=topic,
        )
        for i in range(3)
    ]
