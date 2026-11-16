"""Pick highlight videos from official league/team YouTube channels. Owner: Julian.

YouTube Data API search costs 100 quota units per call (proposal ref [3]),
so search once per relevant game, not per user.
"""
import httpx

from app import config
from app.models import GameResult, Highlight

SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"


def find_highlights(game: GameResult, max_results: int = 1) -> list[Highlight]:
    if config.OFFLINE_MODE or not config.YOUTUBE_API_KEY:
        return []
    params = {
        "part": "snippet",
        "q": f"{game.away} vs {game.home} highlights",
        "type": "video",
        "maxResults": max_results,
        "key": config.YOUTUBE_API_KEY,
        # TODO: restrict to official channels via channelId list per league
    }
    resp = httpx.get(SEARCH_URL, params=params, timeout=20)
    resp.raise_for_status()
    return [
        Highlight(title=i["snippet"]["title"],
                  url=f"https://www.youtube.com/watch?v={i['id']['videoId']}",
                  team=game.home)
        for i in resp.json().get("items", [])
    ]
