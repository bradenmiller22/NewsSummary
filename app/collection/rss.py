"""RSS collector for local/state outlets. Owner: Eric."""
import feedparser

from app.models import Article


def fetch_feed(url: str, topic: str = "local") -> list[Article]:
    feed = feedparser.parse(url)
    return [
        Article(
            source=f"rss:{feed.feed.get('title', url)}",
            url=entry.link,
            title=entry.title,
            description=entry.get("summary", ""),
            topic=topic,
        )
        for entry in feed.entries
    ]
