"""Manage the provider keys that the admin page may write to .env."""
import os
import shutil
from pathlib import Path
from tempfile import NamedTemporaryFile

from dotenv import dotenv_values, set_key
from filelock import FileLock

from app import config

KEY_NAMES = {"newsapi": "NEWSAPI_API_KEY", "currentsapi": "CURRENTSAPI_API_KEY"}
PROVIDERS = tuple(dict.fromkeys(
    name.strip().lower() for name in config.NEWS_PROVIDERS
    if name.strip().lower() in KEY_NAMES
))


def configured_providers() -> set[str]:
    values = dotenv_values(config.ENV_PATH, interpolate=False)
    return {name for name in PROVIDERS if values.get(KEY_NAMES[name])}


def save_news_key(provider: str, key: str) -> None:
    if provider not in PROVIDERS:
        raise ValueError("Unknown news provider")
    key = key.strip()
    if not key or len(key) > 4096 or not key.isascii() or not key.isprintable() or " " in key:
        raise ValueError("Enter an API key of up to 4096 ASCII characters without whitespace.")
    # dotenv single-quoted strings decode escaped backslashes as well as quotes.
    with FileLock(str(config.ENV_PATH) + ".lock", timeout=5):
        # Stage beside the destination so readers see either complete version,
        # including on Windows where older dotenv versions copy over an existing file.
        with NamedTemporaryFile(dir=config.ENV_PATH.parent, delete=False) as temp:
            staged = Path(temp.name)
        try:
            if config.ENV_PATH.exists():
                shutil.copy2(config.ENV_PATH, staged)
            set_key(staged, KEY_NAMES[provider], key.replace("\\", "\\\\"), quote_mode="always")
            os.replace(staged, config.ENV_PATH)
        finally:
            staged.unlink(missing_ok=True)
