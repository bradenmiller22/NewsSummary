"""Fact-check a summary against its sources with a different provider (OpenAI). Owner: Braden.

Flagged summaries go to the review queue; nothing is auto-corrected.
"""
import json

from app import config, llm
from app.db import connect
from app.models import Article, FactCheckResult, Summary
from app.summarize import prompts
from app.summarize.summarizer import format_sources


def check(summary_text: str, sources_text: str) -> FactCheckResult:
    if config.OFFLINE_MODE:
        return FactCheckResult(passed=True)

    raw = llm.openai_chat(
        prompts.FACTCHECK_USER.format(sources=sources_text, summary=summary_text),
        model=config.FACTCHECK_MODEL,
        system=prompts.FACTCHECK_SYSTEM,
    )
    try:
        data = json.loads(raw.strip().removeprefix("```json").removesuffix("```"))
        return FactCheckResult(**data)
    except (json.JSONDecodeError, TypeError, ValueError):
        # Unparseable output is treated as a failure so a human looks at it.
        return FactCheckResult(passed=False, unsupported_claims=[f"Checker output unparseable: {raw[:200]}"])


def check_summary(summary: Summary, articles: list[Article]) -> FactCheckResult:
    return check(summary.text, format_sources(articles))


def send_to_review(summary_id: int, result: FactCheckResult) -> None:
    with connect() as conn:
        conn.execute(
            "INSERT INTO review_queue (summary_id, unsupported_json) VALUES (?, ?)",
            (summary_id, json.dumps(result.unsupported_claims)),
        )
        conn.execute("UPDATE summaries SET status = 'review' WHERE id = ?", (summary_id,))
