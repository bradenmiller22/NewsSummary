"""Fetch one page per configured news provider for the daily pipeline."""
import logging
from datetime import datetime

import httpx
from dotenv import dotenv_values

from app import config
from app.collection import news_keys
from app.models import Article

logger = logging.getLogger(__name__)


def _articles(items, provider: str, date_field: str) -> list[Article]:
    articles = []
    for item in items:
        if not isinstance(item, dict) or not item.get("title") or not item.get("url"):
            continue
        categories = item.get("category") or []
        try:
            published = item.get(date_field)
            if isinstance(published, str) and published[-6:-5] == " ":
                published = datetime.strptime(published, "%Y-%m-%d %H:%M:%S %z")
            articles.append(Article(
                source=provider, url=item["url"], title=item["title"],
                description=item.get("description") or "", content=item.get("content") or "",
                published_at=published or None,
                topic=categories[0] if isinstance(categories, list) and categories else "",
            ))
        except ValueError:
            logger.warning("Skipping an invalid article from %s", provider)
    return articles


def fetch_currentsapi(key: str, lang: str, country: str) -> list[Article]:
    response = httpx.get(
        "https://api.currentsapi.services/v1/latest-news",
        headers={"Authorization": f"Bearer {key}"},
        params={"type": 1, "language": lang, "country": country.upper(), "page_size": 20},
        timeout=20,
    )
    response.raise_for_status()
    return _articles(response.json()["news"], "currentsapi", "published")


def fetch_newsapi(key: str, lang: str, country: str) -> list[Article]:
    # NewsAPI top-headlines accepts country but has no language filter.
    response = httpx.get(
        "https://newsapi.org/v2/top-headlines",
        headers={"X-Api-Key": key}, params={"country": country.lower(), "pageSize": 100},
        timeout=20,
    )
    response.raise_for_status()
    return _articles(response.json()["articles"], "newsapi", "publishedAt")


def fetch_articles(lang: str = "en", country: str = "us") -> list[Article]:
    if config.OFFLINE_MODE:
        return [
            Article(source="demo", url=f"https://example.com/demo/{topic}/{i}",
                    title=f"Placeholder {topic} headline {i}", topic=topic,
                    description=f"Placeholder description for {topic} story {i}.",
                    content=f"Placeholder body text for {topic} story {i}.")
            for topic in config.NEWS_TOPICS for i in range(3)
        ]

    articles = []

    values = dotenv_values(config.ENV_PATH, interpolate=False)
    fetchers = {"currentsapi": fetch_currentsapi, "newsapi": fetch_newsapi}
    for provider in news_keys.PROVIDERS:
        key = values.get(news_keys.KEY_NAMES[provider])
        if key:
            try:
                articles.extend(fetchers[provider](key, lang, country))
            except (httpx.HTTPError, ValueError, KeyError) as exc:
                logger.warning("Skipping %s after %s", provider, type(exc).__name__)
    return articles
