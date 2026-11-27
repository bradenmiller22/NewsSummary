"""Data types passed between pipeline stages. Change these in their own PR."""
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class Depth(str, Enum):
    brief = "brief"        # 1-2 sentences
    standard = "standard"  # short paragraph
    deep = "deep"          # several paragraphs


class UserProfile(BaseModel):
    user_id: int
    location: str = ""                 # e.g. "Iowa City, IA"
    teams: list[str] = []              # e.g. ["Iowa Hawkeyes", "Chicago Cubs"]
    leagues: list[str] = []            # e.g. ["ncaafb", "mlb"]
    topics: list[str] = []             # e.g. ["technology", "local politics"]
    depth: Depth = Depth.standard
    leaning: str = "balanced"          # desired leaning of sources
    audio: bool = False


class Article(BaseModel):
    id: int | None = None
    source: str                        # "newsapi", "currentsapi", "newsdataio", ...
    url: str
    title: str
    description: str = ""
    content: str = ""
    published_at: datetime | None = None
    topic: str = ""
    interests: list[str] = []
    general: bool = True


class Story(BaseModel):
    """A cluster of articles about the same event."""
    id: int | None = None
    headline: str
    article_ids: list[int] = []
    tags: list[str] = []               # topic / region / team tags
    general: bool = True
    region: str = ""                   # "international" | "national" | "state" | "local"


class GameResult(BaseModel):
    league: str
    home: str
    away: str
    home_score: int | None = None
    away_score: int | None = None
    status: str = ""                   # "final", "in progress", ...
    box_score: dict = {}


class RankedStory(BaseModel):
    story: Story
    score: float


class Citation(BaseModel):
    article_id: int
    url: str
    title: str


class Summary(BaseModel):
    story_id: int
    depth: Depth
    text: str
    citations: list[Citation] = []


class FactCheckResult(BaseModel):
    passed: bool
    unsupported_claims: list[str] = []


class Highlight(BaseModel):
    title: str
    url: str
    team: str = ""


class DigestItem(BaseModel):
    story_id: int
    headline: str
    summary: Summary
    factcheck: FactCheckResult


class Digest(BaseModel):
    user_id: int
    created_at: datetime = Field(default_factory=datetime.now)
    items: list[DigestItem] = []
    sports_story_ids: list[int] = []
    standings: list[str] = []
    game_recaps: list[str] = []
    highlights: list[Highlight] = []
    audio_path: str | None = None
