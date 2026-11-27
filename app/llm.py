"""Thin wrappers around the model providers so stages don't each build clients.

Summarizer and fact-checker deliberately use different providers (proposal:
a different model gives an independent view).
"""
from dotenv import dotenv_values

from app import config


def anthropic_client():
    import anthropic
    return anthropic.Anthropic(api_key=dotenv_values(config.ENV_PATH, interpolate=False).get("ANTHROPIC_API_KEY") or config.ANTHROPIC_API_KEY)


def openai_client():
    from openai import OpenAI
    return OpenAI(api_key=dotenv_values(config.ENV_PATH, interpolate=False).get("OPENAI_API_KEY") or config.OPENAI_API_KEY)


def claude(prompt: str, model: str, system: str = "", max_tokens: int = 1024) -> str:
    """Single-turn Claude call, returns text."""
    resp = anthropic_client().messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system or None,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(b.text for b in resp.content if b.type == "text")


def openai_chat(prompt: str, model: str, system: str = "") -> str:
    """Single-turn OpenAI call, returns text."""
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    resp = openai_client().chat.completions.create(model=model, messages=messages)
    return resp.choices[0].message.content or ""
