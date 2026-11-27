"""The daily run: wires every stage together. Shared file — keep it thin.

collect -> store -> cluster -> tag -> (per user) rank -> summarize -> fact-check
-> digest -> sports -> TTS -> save
"""
import json
from datetime import date

from app import config
from app.collection import rss, sports, store
from app.collection.fetch_articles import fetch_articles
from app.db import connect
from app.models import Article, Digest, DigestItem, UserProfile
from app.preferences.profile import load_profile
from app.processing import cluster, tagging
from app.ranking import rank
from app.sports import highlights, recaps
from app.summarize import factcheck, summarizer
from app.tts import tts


def collect() -> list[Article]:
    articles = fetch_articles()
    for feed in config.RSS_FEEDS:
        articles += rss.fetch_feed(feed)
    return store.save_articles(articles)


def build_digest(profile: UserProfile, stories, articles_by_id, games) -> Digest:
    digest = Digest(user_id=profile.user_id)

    for ranked in rank.rank(stories, profile):
        story = ranked.story
        sources = [articles_by_id[i] for i in story.article_ids if i in articles_by_id]
        summary = summarizer.summarize(story, sources, profile)
        result = factcheck.check_summary(summary, sources)

        with connect() as conn:
            cur = conn.execute(
                "INSERT INTO summaries (story_id, depth, text, citations_json, status) VALUES (?, ?, ?, ?, ?)",
                (story.id, summary.depth.value, summary.text,
                 json.dumps([c.model_dump() for c in summary.citations]),
                 "published" if result.passed else "review"),
            )
            summary_id = cur.lastrowid
        if not result.passed:
            factcheck.send_to_review(summary_id, result)
            continue  # flagged summaries are held back from the digest

        digest.items.append(DigestItem(story_id=story.id or 0, headline=story.headline,
                                       summary=summary, factcheck=result))

    for game in recaps.relevant_games(games, profile):
        digest.game_recaps.append(recaps.recap(game))
        digest.highlights += highlights.find_highlights(game)

    if profile.audio:
        digest.audio_path = tts.synthesize(digest)
    return digest


def run_daily() -> list[Digest]:
    articles = collect()
    articles_by_id = {a.id: a for a in articles if a.id}

    stories = tagging.tag(cluster.cluster(articles), articles_by_id)
    with connect() as conn:
        for s in stories:
            cur = conn.execute("INSERT INTO stories (headline, tags_json, region, run_date) VALUES (?, ?, ?, ?)",
                               (s.headline, json.dumps(s.tags), s.region, date.today().isoformat()))
            s.id = cur.lastrowid
            conn.executemany("INSERT OR IGNORE INTO story_articles VALUES (?, ?)",
                             [(s.id, aid) for aid in s.article_ids])

    games = [g for league in config.SPORTS_LEAGUES for g in sports.fetch_scores(league)]

    with connect() as conn:
        user_ids = [r["id"] for r in conn.execute("SELECT id FROM users")]

    digests = []
    for uid in user_ids:
        profile = load_profile(uid)
        if not profile:
            continue
        digest = build_digest(profile, stories, articles_by_id, games)
        with connect() as conn:
            conn.execute("INSERT INTO digests (user_id, digest_json) VALUES (?, ?)",
                         (uid, digest.model_dump_json()))
        digests.append(digest)
    return digests
