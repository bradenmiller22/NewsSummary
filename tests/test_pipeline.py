from fastapi.testclient import TestClient

from app import pipeline
from app.models import UserProfile
from app.preferences.profile import load_profile, save_profile


def test_profile_roundtrip():
    save_profile(UserProfile(user_id=1, teams=["Iowa Hawkeyes"], topics=["technology"]))
    assert load_profile(1).teams == ["Iowa Hawkeyes"]


def test_daily_run_end_to_end():
    save_profile(UserProfile(user_id=1, topics=["technology"]))
    digests = pipeline.run_daily()
    assert len(digests) == 1
    assert digests[0].items, "digest should contain stories"
    assert digests[0].items[0].summary.citations, "summaries must carry citations"


def test_web_pages_load():
    from app.web.main import app
    client = TestClient(app)
    assert client.get("/preferences").status_code == 200
    assert client.get("/review").status_code == 200
