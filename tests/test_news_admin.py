import httpx
import pytest
from dotenv import dotenv_values
from fastapi.testclient import TestClient

from app import config
from app.collection import fetch_articles, news_keys
from app.web.main import app


@pytest.fixture
def admin(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "ADMIN_PASSWORD", "test-password")
    monkeypatch.setattr(config, "ENV_PATH", tmp_path / ".env")
    config.ENV_PATH.write_text("OTHER=keep\n", encoding="utf-8")
    monkeypatch.setattr(news_keys, "PROVIDERS", ("newsapi", "currentsapi", "newsdataio"))
    with TestClient(app, headers={"Origin": "http://testserver"}) as client:
        client.auth = ("admin", "test-password")
        yield client


def test_replace_key(admin):
    assert "newsapi" not in news_keys.configured_providers()
    for provider, key in [("newsapi", "first-secret"), ("currentsapi", "other-secret"),
                          ("newsapi", "replacement-secret")]:
        response = admin.post(f"/admin/keys/{provider}", data={"api_key": key})
        assert response.status_code == 200
        assert f"Key saved for <strong>{provider}</strong>" in response.text
        assert key not in response.text
        assert dotenv_values(config.ENV_PATH)[news_keys.KEY_NAMES[provider]] == key
    assert dotenv_values(config.ENV_PATH) == {
        "OTHER": "keep", "NEWSAPI_API_KEY": "replacement-secret", "CURRENTSAPI_API_KEY": "other-secret"
    }


def test_rejected_updates(admin, monkeypatch):
    url = "/admin/keys/newsapi"
    assert admin.post(url, data={"api_key": "  "}).status_code == 400
    assert admin.post("/admin/keys/other", data={"api_key": "key"}).status_code == 404
    assert admin.post(url, data={"api_key": "key"}, headers={"Origin": "https://other.example"}).status_code == 403
    admin.auth = None
    assert admin.get("/admin").status_code == 401
    assert admin.post(url, data={"api_key": "key"}).status_code == 401
    monkeypatch.setattr(config, "ADMIN_PASSWORD", "")
    assert admin.get("/admin").status_code == 503
    assert "newsapi" not in news_keys.configured_providers()


def test_live_collection_reads_rotated_keys(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "ENV_PATH", tmp_path / ".env")
    monkeypatch.setattr(config, "OFFLINE_MODE", False)
    monkeypatch.setattr(news_keys, "PROVIDERS", ("newsapi", "currentsapi"))
    seen = []

    def fake_get(url, *, headers, params, timeout):
        assert "apiKey" not in params
        request = httpx.Request("GET", url)
        if "newsapi.org" in url:
            return httpx.Response(429, request=request)
        seen.append(headers["Authorization"])
        item = {"title": "New story", "url": "https://example.com/story",
                "published": "2026-11-26 14:00:00 +0000", "category": ["business"]}
        return httpx.Response(200, json={"news": [item]}, request=request)

    monkeypatch.setattr(httpx, "get", fake_get)
    for key in ["first", "replacement"]:
        news_keys.save_news_key("currentsapi", key)
        if key == "replacement":
            news_keys.save_news_key("newsapi", "other")
        articles = fetch_articles.fetch_articles()
        assert len(articles) == 1
        assert articles[0].topic == "business"
        assert articles[0].published_at.year == 2026
    assert seen == ["Bearer first", "Bearer replacement"]


def test_newsapi_top_headlines(monkeypatch):
    def fake_get(url, *, headers, params, timeout):
        assert headers == {"X-Api-Key": "test-key"}
        assert params == {"country": "us", "pageSize": 100}
        item = {"title": "Headline", "url": "https://example.com/news",
                "publishedAt": "2026-11-26T14:00:00Z", "description": None}
        return httpx.Response(200, json={"articles": [item]}, request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx, "get", fake_get)
    article, = fetch_articles.fetch_newsapi("test-key", "en", "US")
    assert article.source == "newsapi"
    assert article.description == ""
    assert article.published_at.hour == 14


def test_newsdataio_admin_to_storage(admin, monkeypatch):
    from app import pipeline
    from app.db import connect

    monkeypatch.setattr(config, "OFFLINE_MODE", False)
    page = admin.get("/admin")
    assert "/admin/keys/newsdataio" in page.text
    result = admin.post("/admin/keys/newsdataio", data={"api_key": "test-newsdata-key"})
    assert result.status_code == 200
    assert "test-newsdata-key" not in result.text

    def fake_get(url, *, headers, params, timeout):
        assert url == "https://newsdata.io/api/1/latest"
        assert headers == {"X-ACCESS-KEY": "test-newsdata-key"}
        assert params == {"country": "us", "language": "en", "category": "top", "datatype": "news"}
        item = {"link": "https://example.org/story", "title": "City approves budget",
                "pubDate": "2026-11-25 17:30:00", "category": ["politics", "top"],
                "description": "The council voted Wednesday.", "content": "ONLY AVAILABLE IN PAID PLANS"}
        return httpx.Response(200, json={"status": "success", "results": [item]}, request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx, "get", fake_get)
    article, = pipeline.collect()
    assert article.id is not None
    with connect() as conn:
        stored = conn.execute("SELECT * FROM articles WHERE id = ?", (article.id,)).fetchone()
    assert stored["source"] == "newsdataio"
    assert stored["url"] == "https://example.org/story"
    assert stored["topic"] == "politics"
    assert stored["published_at"].startswith("2026-11-25T17:30:00")
    assert stored["content"] == ""

@pytest.mark.parametrize("provider", ["openai", "anthropic"])
def test_admin_rotates_model_credentials(admin, monkeypatch, provider):
    import sys
    from types import SimpleNamespace
    from app import llm

    constructor = "OpenAI" if provider == "openai" else "Anthropic"
    monkeypatch.setitem(sys.modules, provider, SimpleNamespace(**{constructor: lambda *, api_key: api_key}))
    for key in ["first-model-secret", "second-model-secret"]:
        response = admin.post(f"/admin/keys/{provider}", data={"api_key": key})
        assert response.status_code == 200 and key not in response.text
        assert getattr(llm, provider + "_client")() == key
