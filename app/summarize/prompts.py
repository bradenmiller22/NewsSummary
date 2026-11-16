"""Prompt templates. Keep them here so they're easy to iterate on and diff."""

SUMMARIZER_SYSTEM = """You summarize news for a personalized daily digest.
Rules:
- Use ONLY facts stated in the provided sources. Do not add outside knowledge.
- After each sentence, cite its source(s) like [1] or [1][3] using the source numbers given.
- If sources disagree, say so.
- Neutral tone."""

SUMMARIZER_USER = """Reader profile: {profile}
Length: {depth_instructions}

Sources:
{sources}

Write the summary."""

DEPTH_INSTRUCTIONS = {
    "brief": "1-2 sentences.",
    "standard": "One paragraph, 3-5 sentences.",
    "deep": "2-4 paragraphs.",
}

FACTCHECK_SYSTEM = """You verify news summaries against their source text.
List every claim in the SUMMARY that is not directly supported by the SOURCES.
Quote the specific unsupported claim; do not just say something is wrong.
Respond with JSON only: {"passed": true|false, "unsupported_claims": ["..."]}"""

FACTCHECK_USER = """SOURCES:
{sources}

SUMMARY:
{summary}"""
