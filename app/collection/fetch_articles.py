"""Fetch one page per configured news provider for the daily pipeline."""
import json
import logging
from urllib.parse import quote
from datetime import date, datetime, timedelta, timezone

import httpx
from dotenv import dotenv_values
from filelock import FileLock

from app import config
from app.collection import news_keys
from app.collection.interests import Search
from app.models import Article
from app.db import connect

logger = logging.getLogger(__name__)


def _articles(items, provider: str, date_field: str, url_field: str = "url") -> list[Article]:
    articles = []
    for item in items:
        if not isinstance(item, dict) or not item.get("title") or not item.get(url_field):
            continue
        categories = item.get("category") or []
        try:
            published = item.get(date_field)
            if isinstance(published, str) and published[-6:-5] == " ":
                published = datetime.strptime(published, "%Y-%m-%d %H:%M:%S %z")
            articles.append(Article(
                source=provider, url=item[url_field], title=item["title"],
                description=item.get("description") or "", content=item.get("content") or "",
                published_at=published or None,
                topic=("sports" if "sports" in categories else categories[0])
                      if isinstance(categories, list) and categories else "",
            ))
        except ValueError:
            logger.warning("Skipping an invalid article from %s", provider)
    return articles


def fetch_currentsapi(key: str, lang: str, country: str, search: Search | None = None) -> list[Article]:
    params = {"type": 1, "language": lang, "country": country.upper(), "page_size": 20}
    endpoint = "latest-news"
    if search:
        endpoint = "search"
        params["keywords"] = search.keyword
        if search.sports:
            params["category"] = "sports"
    response = httpx.get(
        f"https://api.currentsapi.services/v1/{endpoint}",
        headers={"Authorization": f"Bearer {key}"},
        params=params,
        timeout=20,
    )
    response.raise_for_status()
    return _articles(response.json()["news"], "currentsapi", "published")


def fetch_newsapi(key: str, lang: str, country: str, search: Search | None = None) -> list[Article]:
    endpoint = "top-headlines"
    params = {"country": country.lower(), "pageSize": 100}
    if search:
        if search.sports:
            params.update(category="sports", q=search.keyword)
        else:
            endpoint = "everything"
            since = datetime.now(timezone.utc) - timedelta(days=2)
            params = {"q": search.keyword, "language": lang, "from": since.date().isoformat(),
                      "sortBy": "publishedAt", "pageSize": 100}
    response = httpx.get(
        f"https://newsapi.org/v2/{endpoint}",
        headers={"X-Api-Key": key}, params=params,
        timeout=20,
    )
    response.raise_for_status()
    return _articles(response.json()["articles"], "newsapi", "publishedAt")


def fetch_newsdataio(key: str, lang: str, country: str, search: Search | None = None) -> list[Article]:
    params = {"country": country.lower(), "language": lang, "datatype": "news"}
    if search and search.state:
        place = f'"{search.keyword}"'
        if search.state != search.keyword:
            place += f' AND "{search.state}"'
        params["qInMeta"] = place
    elif search:
        params["q"] = search.keyword
        if search.sports:
            params["category"] = "sports"
    else:
        params["category"] = "top"
    response = httpx.get(
        "https://newsdata.io/api/1/latest",
        headers={"X-ACCESS-KEY": key},
        params=params,
        timeout=20,
    )
    response.raise_for_status()
    data = response.json()
    if data.get("status") != "success" or not isinstance(data.get("results"), list):
        raise ValueError("Unexpected NewsData.io response")
    articles = _articles(data["results"], "newsdataio", "pubDate", url_field="link")
    for article in articles:
        if article.content == "ONLY AVAILABLE IN PAID PLANS":
            article.content = ""
    return articles


def _daily_page(provider, fetch, key, lang, country, search):
    query = json.dumps([provider, lang, country, search.tag if search else "", bool(search and search.sports)])
    today = date.today().isoformat()
    # A scheduled job and the web Run button can share the same database.
    with FileLock(str(config.DATABASE_PATH) + ".news.lock"):
        with connect() as conn:
            conn.execute("DELETE FROM daily_news_pages WHERE day != ?", (today,))
            row = conn.execute("SELECT articles_json FROM daily_news_pages WHERE query = ?", (query,)).fetchone()
        if row:
            return [Article.model_validate(item) for item in json.loads(row["articles_json"])]
        page = fetch(key, lang, country, search)
        payload = json.dumps([a.model_dump(mode="json") for a in page])
        with connect() as conn:
            conn.execute("INSERT OR REPLACE INTO daily_news_pages VALUES (?, ?, ?)", (query, today, payload))
        return page


def fetch_articles(lang: str = "en", country: str = "us", *, searches=(), cache_daily=False) -> list[Article]:
    if config.OFFLINE_MODE:
        demo = [
            Article(source="demo", url=f"https://example.com/demo/{topic}/{i}",
                    title=f"Placeholder {topic} headline {i}", topic=topic,
                    description=f"Placeholder description for {topic} story {i}.",
                    content=f"Placeholder body text for {topic} story {i}.")
            for topic in config.NEWS_TOPICS for i in range(3)
        ]

        for search in dict.fromkeys(searches):
            demo.append(Article(source="demo", url=f"https://example.com/demo/search/{int(search.sports)}/{quote(search.tag, safe='')}",
                                title=f"Demo news about {search.keyword}",
                                topic="sports" if search.sports else ("" if search.state else search.keyword),
                                interests=[search.tag], general=False))
        return demo

    values = dotenv_values(config.ENV_PATH, interpolate=False)
    fetchers = {"currentsapi": fetch_currentsapi, "newsapi": fetch_newsapi, "newsdataio": fetch_newsdataio}
    active = {p: values[news_keys.KEY_NAMES[p]] for p in news_keys.PROVIDERS if values.get(news_keys.KEY_NAMES[p])}
    articles = {}
    for search in (None, *dict.fromkeys(searches)):
        for provider, key in list(active.items()):
            if search and search.state and provider != "newsdataio":
                continue
            try:
                fetch = fetchers[provider]
                page = (_daily_page(provider, fetch, key, lang, country, search) if cache_daily
                        else fetch(key, lang, country, search))
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code in (401, 403, 429):
                    del active[provider]
                logger.warning("Skipping %s request (HTTP %s)", provider, exc.response.status_code)
                continue
            except (httpx.HTTPError, ValueError, KeyError) as exc:
                logger.warning("Skipping %s after %s", provider, type(exc).__name__)
                continue
            for article in page:
                existing = articles.setdefault(article.url, article)
                if search:
                    if existing is article:
                        existing.general = False
                    if search.tag not in existing.interests:
                        existing.interests.append(search.tag)
                    if search.sports:
                        existing.topic = "sports"
    return list(articles.values())
