"""Summarize a story with citations (Claude Sonnet 5.5). Owner: Braden."""
from app import config, llm
from app.models import Article, Citation, Depth, Story, Summary, UserProfile
from app.summarize import prompts


def format_sources(articles: list[Article]) -> str:
    return "\n\n".join(
        f"[{i}] {a.title}\n{a.content or a.description}" for i, a in enumerate(articles, start=1)
    )


def summarize(story: Story, articles: list[Article], profile: UserProfile,
              depth: Depth | None = None) -> Summary:
    depth = depth or profile.depth
    citations = [Citation(article_id=a.id or 0, url=a.url, title=a.title) for a in articles]

    if config.OFFLINE_MODE:
        text = f"Placeholder summary of '{story.headline}' [1]."
    else:
        prompt = prompts.SUMMARIZER_USER.format(
            profile=profile.model_dump_json(include={"location", "teams", "topics"}),
            depth_instructions=prompts.DEPTH_INSTRUCTIONS[depth.value],
            sources=format_sources(articles),
        )
        text = llm.claude(prompt, model=config.SUMMARIZER_MODEL, system=prompts.SUMMARIZER_SYSTEM)

    return Summary(story_id=story.id or 0, depth=depth, text=text, citations=citations)
