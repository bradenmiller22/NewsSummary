import httpx

from app import config, pipeline
from app.collection import news_keys, espn
from app.models import UserProfile
from app.sports import recaps


def test_shared_interest_queries_cache_and_merge(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "OFFLINE_MODE", False)
    monkeypatch.setattr(config, "ENV_PATH", tmp_path / ".env")
    monkeypatch.setattr(news_keys, "PROVIDERS", ("newsdataio",))
    news_keys.save_news_key("newsdataio", "test")
    requests = []

    def get(url, *, headers, params, timeout):
        requests.append(params.copy())
        item = {"title": "A shared headline", "link": "https://example.org/shared"}
        return httpx.Response(200, json={"status": "success", "results": [item]}, request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx, "get", get)
    profiles = [UserProfile(user_id=1, topics=["Technology"], leagues=["MLB"], teams=["Chicago Cubs"]),
                UserProfile(user_id=2, topics=[" technology "], leagues=["Major League Baseball"])]
    for _ in range(2):
        article, = pipeline.collect(profiles)
        assert article.general and article.id
        assert set(article.interests) == {"technology", "mlb", "chicago cubs"}
    assert [p.get("q") for p in requests] == [None, "technology", "chicago cubs", "mlb"]
    assert [p.get("category") for p in requests] == ["top", None, "sports", "sports"]


def test_espn_scores_and_standings(monkeypatch):
    monkeypatch.setattr(config, "OFFLINE_MODE", False)
    team = {"displayName": "Iowa Hawkeyes"}
    game = {"status": {"type": {"completed": True}}, "competitions": [{"competitors": [
        {"homeAway": "away", "score": "24", "team": team},
        {"homeAway": "home", "score": "17", "team": {"displayName": "Opponent"}}]}]}

    def get(url, *, params, timeout):
        if url.endswith("/scoreboard"):
            assert params["groups"] == 80 and "dates" in params
            data = {"events": [game, {"status": {"type": {"completed": False}}, "competitions": [{}]}]}
        else:
            assert "/apis/v2/" in url
            data = {"children": [{"name": "Big Ten", "standings": {"entries": [
                {"team": team, "stats": [{"name": "wins", "displayValue": "8"},
                                         {"name": "losses", "displayValue": "3"}]}]}}]}
        return httpx.Response(200, json=data, request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx, "get", get)
    profile = UserProfile(user_id=1, teams=["Iowa Hawkeyes"])
    game, = recaps.relevant_games(espn.fetch_scores("ncaafb"), profile)
    assert game.away_score == 24
    rows = espn.fetch_standings("ncaafb")
    (team_name, line), = rows
    assert team_name == profile.teams[0]
    assert "Iowa Hawkeyes (8-3)" in line


def test_run_button_generates_digest():
    from fastapi.testclient import TestClient
    from app.web.main import app
    from app.db import connect

    with TestClient(app) as client:
        client.post("/preferences", data={"teams": "Chicago Cubs"})
        response = client.post("/run", follow_redirects=False)
        assert response.status_code == 303 and response.headers["location"] == "/"
        assert client.get("/").status_code == 200
    with connect() as conn:
        assert conn.execute("SELECT COUNT(*) FROM digests WHERE user_id = 1").fetchone()[0] == 1


def test_regional_queries_shared_and_labeled_by_place(tmp_path, monkeypatch):
    from app.collection.interests import regional_searches

    assert regional_searches(" IA ") == regional_searches("Iowa")
    assert not regional_searches("")
    assert not regional_searches("London, England")
    monkeypatch.setattr(config, "OFFLINE_MODE", False)
    monkeypatch.setattr(config, "ENV_PATH", tmp_path / ".env")
    monkeypatch.setattr(news_keys, "PROVIDERS", ("newsdataio",))
    news_keys.save_news_key("newsdataio", "test")
    queries = []

    def get(url, *, headers, params, timeout):
        query = params.get("qInMeta", "general")
        queries.append(query)
        item = {"title": query, "link": f"https://example.org/story/{len(queries)}"}
        return httpx.Response(200, json={"status": "success", "results": [item]}, request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx, "get", get)
    city = UserProfile(user_id=1, location="Iowa City, IA")
    county = UserProfile(user_id=2, location="Linn County, Iowa")
    for _ in range(2):
        articles = pipeline.collect([city, county])
    assert queries == ["general", '"iowa"', '"iowa city" AND "iowa"', '"linn county" AND "iowa"']
    assert [a.interests for a in articles] == [
        [], ["state:iowa"], ["local:iowa city, iowa"], ["local:linn county, iowa"]
    ]
