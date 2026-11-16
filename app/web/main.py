"""FastAPI app. Run: uvicorn app.web.main:app --reload"""
import json
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app import config, pipeline
from app.db import connect, init_db
from app.models import Digest
from app.preferences.profile import build_profile, load_profile, save_profile

HERE = Path(__file__).parent


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Daily Brief", lifespan=lifespan)
templates = Jinja2Templates(directory=HERE / "templates")
app.mount("/static", StaticFiles(directory=HERE / "static"), name="static")
(config.ROOT / "audio").mkdir(exist_ok=True)
app.mount("/audio", StaticFiles(directory=config.ROOT / "audio"), name="audio")

# Single demo user until auth is added.
USER_ID = 1


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    if not load_profile(USER_ID):
        return RedirectResponse("/preferences")
    with connect() as conn:
        row = conn.execute("SELECT digest_json FROM digests WHERE user_id = ? ORDER BY id DESC LIMIT 1",
                           (USER_ID,)).fetchone()
    digest = Digest.model_validate_json(row["digest_json"]) if row else None
    return templates.TemplateResponse(request, "index.html", {"digest": digest})


@app.get("/preferences", response_class=HTMLResponse)
def preferences_form(request: Request):
    return templates.TemplateResponse(request, "preferences.html", {"profile": load_profile(USER_ID)})


@app.post("/preferences")
def preferences_submit(location: str = Form(""), teams: str = Form(""), leagues: str = Form(""),
                       topics: str = Form(""), depth: str = Form("standard"),
                       leaning: str = Form("balanced"), audio: bool = Form(False)):
    split = lambda s: [x.strip() for x in s.split(",") if x.strip()]
    answers = {"location": location, "teams": split(teams), "leagues": split(leagues),
               "topics": split(topics), "depth": depth, "leaning": leaning, "audio": audio}
    save_profile(build_profile(USER_ID, answers))
    return RedirectResponse("/", status_code=303)


@app.post("/feedback")
def feedback(story_id: int = Form(...), value: int = Form(...)):
    with connect() as conn:
        conn.execute("INSERT INTO feedback (user_id, story_id, value) VALUES (?, ?, ?)",
                     (USER_ID, story_id, 1 if value > 0 else -1))
    return RedirectResponse("/", status_code=303)


@app.post("/run")
def run_now():
    """Dev convenience: trigger the daily pipeline from the UI."""
    pipeline.run_daily()
    return RedirectResponse("/", status_code=303)


@app.get("/review", response_class=HTMLResponse)
def review_queue(request: Request):
    with connect() as conn:
        rows = conn.execute(
            """SELECT r.id, r.unsupported_json, s.text, s.story_id
               FROM review_queue r JOIN summaries s ON s.id = r.summary_id
               WHERE r.resolved = 0 ORDER BY r.id""").fetchall()
    items = [{"id": r["id"], "text": r["text"], "story_id": r["story_id"],
              "claims": json.loads(r["unsupported_json"])} for r in rows]
    return templates.TemplateResponse(request, "review.html", {"items": items})


@app.post("/review/{item_id}")
def resolve(item_id: int, action: str = Form(...), note: str = Form("")):
    status = "published" if action == "approve" else "rejected"
    with connect() as conn:
        conn.execute("UPDATE review_queue SET resolved = 1, reviewer_note = ? WHERE id = ?", (note, item_id))
        conn.execute("""UPDATE summaries SET status = ?
                        WHERE id = (SELECT summary_id FROM review_queue WHERE id = ?)""", (status, item_id))
    return RedirectResponse("/review", status_code=303)
