"""Turn free-form preference answers into a structured UserProfile (Claude Haiku 5.5). Owner: Julian."""
import json

from app import config, llm
from app.db import connect
from app.models import UserProfile

SYSTEM = """Convert the user's answers into JSON matching this schema exactly:
{"location": str, "teams": [str], "leagues": [str], "topics": [str],
 "depth": "brief"|"standard"|"deep", "leaning": str, "audio": bool}
Use official team names. Respond with JSON only."""


def build_profile(user_id: int, form_answers: dict) -> UserProfile:
    if config.OFFLINE_MODE:
        return UserProfile(user_id=user_id, **{k: v for k, v in form_answers.items()
                                                if k in UserProfile.model_fields and v})
    raw = llm.claude(json.dumps(form_answers), model=config.PROFILE_MODEL, system=SYSTEM)
    data = json.loads(raw.strip().removeprefix("```json").removesuffix("```"))
    return UserProfile(user_id=user_id, **data)


def save_profile(profile: UserProfile, name: str = "") -> int:
    with connect() as conn:
        cur = conn.execute(
            "INSERT OR REPLACE INTO users (id, name, profile_json) VALUES (?, ?, ?)",
            (profile.user_id or None, name, profile.model_dump_json()),
        )
        return cur.lastrowid


def load_profile(user_id: int) -> UserProfile | None:
    with connect() as conn:
        row = conn.execute("SELECT profile_json FROM users WHERE id = ?", (user_id,)).fetchone()
    return UserProfile.model_validate_json(row["profile_json"]) if row else None
