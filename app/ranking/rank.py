"""Rank stories for a user. Owner: Braden.

score = w_sim * cos(profile_embedding, story_embedding)
      + w_team * (story mentions a favorite team)
      + w_topic * (story tag in user topics)
      + w_fb * feedback_bias(user, story tags)
"""
from app import config
from app.models import RankedStory, Story, UserProfile

WEIGHTS = {"sim": 1.0, "team": 0.5, "topic": 0.3, "feedback": 0.2}


def rank(stories: list[Story], profile: UserProfile, limit: int = config.STORIES_PER_DIGEST) -> list[RankedStory]:
    ranked = []
    for s in stories:
        score = 0.0
        # TODO: embedding similarity
        if any(t in profile.topics for t in s.tags):
            score += WEIGHTS["topic"]
        if any(team.lower() in s.headline.lower() for team in profile.teams):
            score += WEIGHTS["team"]
        # TODO: feedback bias from the feedback table
        ranked.append(RankedStory(story=s, score=score))
    ranked.sort(key=lambda r: r.score, reverse=True)
    return ranked[:limit]
