"""Turn a digest into audio (OpenAI gpt-4o-mini-tts; ElevenLabs as alternative). Owner: Julian."""
import re
from pathlib import Path

from app import config, llm
from app.models import Digest

AUDIO_DIR = config.ROOT / "audio"


def digest_to_script(digest: Digest) -> str:
    parts = ["Here is your daily brief."]
    for item in digest.items:
        text = re.sub(r"\[\d+\]", "", item.summary.text)  # strip citation markers
        parts.append(f"{item.headline}. {text}")
    parts.extend(digest.game_recaps)
    return "\n\n".join(parts)


def synthesize(digest: Digest) -> str | None:
    if config.OFFLINE_MODE or not config.OPENAI_API_KEY:
        return None
    AUDIO_DIR.mkdir(exist_ok=True)
    out = AUDIO_DIR / f"digest_{digest.user_id}_{digest.created_at:%Y%m%d}.mp3"
    # TODO: chunk long scripts (TTS input limits)
    with llm.openai_client().audio.speech.with_streaming_response.create(
        model=config.TTS_MODEL, voice="alloy", input=digest_to_script(digest)
    ) as resp:
        resp.stream_to_file(out)
    return str(Path(out).relative_to(config.ROOT))
