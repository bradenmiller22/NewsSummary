"""Sports scores collector. Owner: Eric (fetching) / Julian (recaps use this).

TODO(Eric): pick a free scores API (see proposal ref [11]) and implement fetch_scores.
"""
from app import config
from app.models import GameResult


def fetch_scores(league: str) -> list[GameResult]:
    if config.OFFLINE_MODE:
        return [GameResult(league=league, home="Home Team", away="Away Team",
                           home_score=24, away_score=17, status="final")]
    raise NotImplementedError("Choose a scores API and implement")
