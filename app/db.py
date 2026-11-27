"""SQLite storage. Owner: Eric.

Plain sqlite3 to keep setup at zero; swap for SQLAlchemy/Postgres later if needed.
"""
import sqlite3
from contextlib import contextmanager

from app import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS daily_news_pages (
    query TEXT PRIMARY KEY,
    day TEXT NOT NULL,
    articles_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS users (
    id           INTEGER PRIMARY KEY,
    name         TEXT,
    profile_json TEXT NOT NULL,           -- UserProfile as JSON
    created_at   TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS articles (
    id           INTEGER PRIMARY KEY,
    source       TEXT NOT NULL,
    url          TEXT NOT NULL UNIQUE,     -- dedupe on URL
    title        TEXT NOT NULL,
    description  TEXT,
    content      TEXT,
    topic        TEXT,
    published_at TEXT,
    fetched_at   TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS stories (
    id         INTEGER PRIMARY KEY,
    headline   TEXT NOT NULL,
    tags_json  TEXT DEFAULT '[]',
    region     TEXT,
    run_date   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS story_articles (
    story_id   INTEGER REFERENCES stories(id),
    article_id INTEGER REFERENCES articles(id),
    PRIMARY KEY (story_id, article_id)
);

CREATE TABLE IF NOT EXISTS summaries (
    id             INTEGER PRIMARY KEY,
    story_id       INTEGER REFERENCES stories(id),
    depth          TEXT NOT NULL,
    text           TEXT NOT NULL,
    citations_json TEXT DEFAULT '[]',
    status         TEXT DEFAULT 'pending',  -- pending | published | review | rejected
    created_at     TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS review_queue (
    id               INTEGER PRIMARY KEY,
    summary_id       INTEGER REFERENCES summaries(id),
    unsupported_json TEXT NOT NULL,
    resolved         INTEGER DEFAULT 0,
    reviewer_note    TEXT
);

CREATE TABLE IF NOT EXISTS feedback (
    id         INTEGER PRIMARY KEY,
    user_id    INTEGER REFERENCES users(id),
    story_id   INTEGER REFERENCES stories(id),
    value      INTEGER NOT NULL,            -- +1 like, -1 dislike
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS digests (
    id          INTEGER PRIMARY KEY,
    user_id     INTEGER REFERENCES users(id),
    digest_json TEXT NOT NULL,
    created_at  TEXT DEFAULT CURRENT_TIMESTAMP
);
"""


@contextmanager
def connect():
    config.DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with connect() as conn:
        conn.executescript(SCHEMA)
