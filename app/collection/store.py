"""Save collected articles. Owner: Eric."""
from app.db import connect
from app.models import Article


def save_articles(articles: list[Article]) -> list[Article]:
    """Insert new articles (URL is unique, so repeats are skipped). Returns articles with ids."""
    saved = []
    with connect() as conn:
        for a in articles:
            conn.execute(
                """INSERT OR IGNORE INTO articles
                   (source, url, title, description, content, topic, published_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (a.source, a.url, a.title, a.description, a.content, a.topic,
                 a.published_at.isoformat() if a.published_at else None),
            )
            row = conn.execute("SELECT id FROM articles WHERE url = ?", (a.url,)).fetchone()
            saved.append(a.model_copy(update={"id": row["id"]}))
    return saved
