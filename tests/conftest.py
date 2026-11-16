import pytest

from app import config


@pytest.fixture(autouse=True)
def offline_temp_db(tmp_path, monkeypatch):
    """Every test runs offline against a throwaway database."""
    monkeypatch.setattr(config, "OFFLINE_MODE", True)
    monkeypatch.setattr(config, "DATABASE_PATH", tmp_path / "test.db")
    from app.db import init_db
    init_db()
