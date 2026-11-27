"""Shared search terms for one daily collection."""
from dataclasses import dataclass

from app.models import UserProfile


def normalized(text: str) -> str:
    return " ".join(text.split()).casefold()


LEAGUE_NAMES = {
    "nfl": "National Football League", "nba": "National Basketball Association",
    "mlb": "Major League Baseball", "ncaafb": "college football",
}


def league_code(name: str) -> str:
    name = normalized(name)
    aliases = {"ncaa football": "ncaafb", "ncaaf": "ncaafb", "fbs": "ncaafb"}
    return next((code for code, label in LEAGUE_NAMES.items() if normalized(label) == name),
                aliases.get(name, name))


@dataclass(frozen=True)
class Search:
    keyword: str
    sports: bool = False
    state: str = ""

    @property
    def tag(self) -> str:
        if not self.state:
            return self.keyword
        if self.keyword == self.state:
            return f"state:{self.state}"
        return f"local:{self.keyword}, {self.state}"


_STATE_CODES = """AL Alabama|AK Alaska|AZ Arizona|AR Arkansas|CA California|CO Colorado|CT Connecticut|
DE Delaware|DC District of Columbia|FL Florida|GA Georgia|HI Hawaii|ID Idaho|IL Illinois|IN Indiana|
IA Iowa|KS Kansas|KY Kentucky|LA Louisiana|ME Maine|MD Maryland|MA Massachusetts|MI Michigan|
MN Minnesota|MS Mississippi|MO Missouri|MT Montana|NE Nebraska|NV Nevada|NH New Hampshire|
NJ New Jersey|NM New Mexico|NY New York|NC North Carolina|ND North Dakota|OH Ohio|OK Oklahoma|
OR Oregon|PA Pennsylvania|RI Rhode Island|SC South Carolina|SD South Dakota|TN Tennessee|
TX Texas|UT Utah|VT Vermont|VA Virginia|WA Washington|WV West Virginia|WI Wisconsin|WY Wyoming"""
STATES = {}
for entry in _STATE_CODES.lower().split("|"):
    code, name = entry.strip().split(" ", 1)
    STATES[code] = STATES[name] = name


def regional_searches(location: str) -> list[Search]:
    """Accept a US state alone, or a city/region followed by its state."""
    area, _, suffix = normalized(location).rpartition(",")
    state = STATES.get(suffix.strip())
    if not state:
        return []
    searches = [Search(state, state=state)]
    area = area.strip()
    if (area and area != state and len(area) <= 70 and
            all(c.isalpha() or c in " .'-" for c in area)):
        searches.append(Search(area, state=state))
    return searches


def profile_searches(profile: UserProfile) -> list[Search]:
    searches = [Search(normalized(topic)) for topic in profile.topics]
    searches.extend(Search(normalized(team), True) for team in profile.teams)
    for league in profile.leagues:
        code = league_code(league)
        searches.append(Search("college football" if code == "ncaafb" else code, True))
    searches.extend(regional_searches(profile.location))
    return [search for search in searches if search.keyword]
