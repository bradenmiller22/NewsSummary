"""The daily run: wires every stage together. Shared file — keep it thin.

collect -> store -> cluster -> tag -> (per user) rank -> summarize -> fact-check
-> digest -> sports -> TTS -> save
"""
import json
from datetime import date

from app import config
from app.collection import espn, store
from app.collection.fetch_articles import fetch_articles
from app.collection.interests import league_code, profile_searches
from app.db import connect
from app.models import Article, Digest, DigestItem, UserProfile
from app.processing import cluster, tagging
from app.ranking import rank
from app.sports import highlights, recaps
from app.summarize import factcheck, summarizer
from app.tts import tts


def collect(profiles=()) -> list[Article]:
    searches = [search for profile in profiles for search in profile_searches(profile)]
    articles = fetch_articles(searches=searches, cache_daily=True)
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
    with connect() as conn:
        profiles = [UserProfile.model_validate_json(row["profile_json"]) for row in
                    conn.execute("SELECT profile_json FROM users ORDER BY id")]
    articles = collect(profiles)
    articles_by_id = {a.id: a for a in articles if a.id}

    stories = tagging.tag(cluster.cluster(articles), articles_by_id)
    with connect() as conn:
        for s in stories:
            cur = conn.execute("INSERT INTO stories (headline, tags_json, region, run_date) VALUES (?, ?, ?, ?)",
                               (s.headline, json.dumps(s.tags), s.region, date.today().isoformat()))
            s.id = cur.lastrowid
            conn.executemany("INSERT OR IGNORE INTO story_articles VALUES (?, ?)",
                             [(s.id, aid) for aid in s.article_ids])

    followed = {league_code(name) for p in profiles for name in p.leagues}
    # Team preferences are free text, so search all supported leagues for team-only follows.
    leagues = [league for league in config.SPORTS_LEAGUES
               if league in followed or any(p.teams for p in profiles)]
    games = [game for league in leagues for game in espn.fetch_scores(league)]

    digests = []
    for profile in profiles:
        uid = profile.user_id
        digest = build_digest(profile, stories, articles_by_id, games)
        with connect() as conn:
            conn.execute("INSERT INTO digests (user_id, digest_json) VALUES (?, ?)",
                         (uid, digest.model_dump_json()))
        digests.append(digest)
    return digests
