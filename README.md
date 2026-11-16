# Daily Brief – Personalized News Summary

ECE:5230 Generative AI and Tools · Team 07 · Braden Miller, Eric Lucas, Julian Quintero

A personalized daily news + sports digest. Each morning the pipeline collects
articles and scores, clusters and ranks them against each user's profile,
summarizes them with citations, fact-checks every summary with a second model
from a different provider, and serves the result as a web page (with optional
audio).

## Pipeline

```
preferences form ──LLM──▶ profile.json
                                │
GNews / RSS / sports APIs ──▶ collection ──▶ processing (dedupe, cluster, tag)
                                                 │
                                   ranking (embeddings + weights + feedback)
                                                 │
                                   summarizer (Claude Sonnet 5.5, cited)
                                                 │
                                   fact-check (OpenAI) ──fail──▶ review queue
                                                 │ pass
                                   digest (web UI) ──▶ TTS audio (optional)
                                                 │
                                   like / dislike ──▶ tomorrow's ranking
```

## Repo layout

| Path | What lives there | Owner |
|---|---|---|
| `app/collection/` | GNews, RSS, sports score fetchers | Eric |
| `app/db.py`, `scripts/run_daily.py` | SQLite schema, scheduler entry point | Eric |
| `app/processing/` | Dedupe, story clustering, topic tagging | Braden |
| `app/ranking/` | Profile ↔ story relevance ranking + feedback | Braden |
| `app/summarize/` | Summarizer + fact-checker + review queue | Braden |
| `app/web/` | FastAPI app and templates | Braden |
| `app/preferences/` | Preference form → JSON profile (LLM) | Julian |
| `app/sports/` | Game recaps, YouTube highlight selection | Julian |
| `app/tts/` | Text-to-speech for the digest | Julian |
| `experiments/factcheck_feasibility/` | The 10-pair fact-check test from the proposal | Everyone |
| `tests/` | Pytest tests | Everyone |

Shared pieces: `app/config.py` (settings/env), `app/llm.py` (model clients),
`app/models.py` (data types passed between stages), `app/pipeline.py`
(the daily run that wires every stage together).

## Getting started

```bash
git clone <repo-url> && cd daily-brief
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # then fill in your API keys
python scripts/init_db.py          # creates data/daily_brief.db
uvicorn app.web.main:app --reload  # http://127.0.0.1:8000
```

Run the daily pipeline once by hand:

```bash
python scripts/run_daily.py
```

Run tests:

```bash
pytest
```

Every stage is a stub that returns placeholder data, so the whole pipeline
runs end to end from day one. Replace the `TODO`s in your area and the rest of
the system keeps working.

## Team conventions

- Branch per feature: `eric/gnews-collector`, `julian/tts`, etc. Open a PR into `main`.
- Never commit `.env` or anything in `data/`. API keys go in `.env` only.
- Stages talk to each other only through the types in `app/models.py`. If you
  need a new field, add it there in its own PR so everyone sees it.
- Model names live in `.env` / `app/config.py`, never hard-coded in a stage.

## Milestones

| Dates | Goal |
|---|---|
| Nov 2–8 | Repo + API keys, collection job storing articles, fact-check feasibility test |
| Nov 9–15 | Clustering, tagging, user preferences |
| Nov 16–22 | Summarizer with citations, fact-check stage, review queue |
| Nov 23–29 | Ranking with feedback, sports recaps, basic web UI |
| Nov 30–Dec 6 | Text-to-speech, full end-to-end daily run |
| Dec 7 | Final report and demo video |
