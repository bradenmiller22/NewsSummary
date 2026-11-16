"""Short game recaps for the user's teams. Owner: Julian."""
from app.models import GameResult, UserProfile


def relevant_games(games: list[GameResult], profile: UserProfile) -> list[GameResult]:
    teams = {t.lower() for t in profile.teams}
    return [g for g in games if g.home.lower() in teams or g.away.lower() in teams] or games[:3]


def recap(game: GameResult) -> str:
    # TODO: LLM recap from box score (fact-check it too).
    return f"{game.away} {game.away_score} @ {game.home} {game.home_score} ({game.status})"
