"""ESPN scores for the morning brief and current conference/division standings."""
import logging
from datetime import date, timedelta

import httpx

from app import config
from app.models import GameResult

logger = logging.getLogger(__name__)
PATHS = {"nfl": "football/nfl", "nba": "basketball/nba", "mlb": "baseball/mlb",
         "ncaafb": "football/college-football"}


def _espn(league, resource, params):
    prefix = "apis/v2" if resource == "standings" else "apis/site/v2"
    url = f"https://site.api.espn.com/{prefix}/sports/{PATHS[league]}/{resource}"
    try:
        response = httpx.get(url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        return data if isinstance(data, dict) else {}
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("ESPN %s %s unavailable (%s)", league, resource, type(exc).__name__)
        return {}


def fetch_scores(league: str) -> list[GameResult]:
    if league not in PATHS:
        return []
    if config.OFFLINE_MODE:
        return [GameResult(league=league, home="Home Team", away="Away Team",
                           home_score=24, away_score=17, status="final")]
    yesterday = date.today() - timedelta(days=1)
    params = {"dates": yesterday.strftime("%Y%m%d"), "limit": 200}
    if league == "ncaafb":
        params["groups"] = 80  # FBS, including unranked teams
    games = []
    for event in _espn(league, "scoreboard", params).get("events", []):
        for match in event.get("competitions", []):
            if not match.get("status", event.get("status", {})).get("type", {}).get("completed"):
                continue
            sides = {side.get("homeAway"): side for side in match.get("competitors", [])}
            try:
                home, away = sides["home"], sides["away"]
                games.append(GameResult(league=league, home=home["team"]["displayName"],
                                        away=away["team"]["displayName"], home_score=int(home["score"]),
                                        away_score=int(away["score"]), status="final"))
            except (KeyError, TypeError, ValueError):
                continue
    return games


def fetch_standings(league: str) -> list[tuple[str, str]]:
    if league not in PATHS or config.OFFLINE_MODE:
        return []
    rows = []
    def read_group(group):
        label = group.get("name") or league.upper()
        for index, entry in enumerate(group.get("standings", {}).get("entries", []), 1):
            team = entry.get("team", {}).get("displayName")
            if not team:
                continue
            stats = {s.get("name"): s.get("displayValue") for s in entry.get("stats", [])}
            record = stats.get("overall") or stats.get("summary")
            if not record and stats.get("wins") and stats.get("losses"):
                record = f"{stats['wins']}-{stats['losses']}"
                if stats.get("ties") and stats["ties"] != "0":
                    record += f"-{stats['ties']}"
            place = stats.get("playoffSeed") or stats.get("rank") or str(index)
            rows.append((team, f"{league.upper()} · {label} · {place}. {team}" + (f" ({record})" if record else "")))
        for child in group.get("children", []):
            read_group(child)
    read_group(_espn(league, "standings", {}))
    return rows
