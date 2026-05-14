"""LLM-backed script agent — turns a topic into a structured short-form script.

Returns a ``ScriptBundle`` containing the fields the rest of the pipeline
needs:

    video_title       -> {{VIDEO_TITLE}} merge field + YouTube title
    script_caption    -> {{SCRIPT_CAPTION}} hero caption
    script            -> full narration handed to ElevenLabs
    caption_overlays  -> rolling captions burned on screen
    visual_prompt     -> forwarded to the generative B-roll API
    video_description -> YouTube description (CTA + disclaimer)
    video_tags        -> YouTube tag list

The agent enforces a strict JSON schema. If the model returns invalid
JSON, malformed fields, or empty values we raise ``ScriptGenerationError``
so the supervisor can retry with backoff.

By default we use Anthropic Claude (already a project dep). The OpenAI
provider is wired in symmetrically so the choice is one env var away.
"""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

PROVIDER_ANTHROPIC = "anthropic"
PROVIDER_OPENAI = "openai"

DEFAULT_PROVIDER = PROVIDER_ANTHROPIC
DEFAULT_ANTHROPIC_MODEL = "claude-sonnet-4-6"
DEFAULT_OPENAI_MODEL = "gpt-4.1-mini"
DEFAULT_TIMEOUT_S = 60

SYSTEM_PROMPT = """You are a senior YouTube Shorts scriptwriter for the
personal-finance niche. Every script you write is ~30 seconds (≈75
spoken words), high-retention, and built around a strong hook in the
first 2 seconds. You always reply with strict JSON only — no markdown
fences, no preamble. Never give specific financial advice; phrase tips
as general education.""".replace("\n", " ")

USER_PROMPT_TEMPLATE = """Topic: {topic}
Niche: {niche}
Target duration (seconds): {duration}

Produce a JSON object with exactly these keys:

  video_title       - <=70 chars, click-worthy, no emojis, no ALL CAPS.
  script_caption    - the hero caption (the strongest line in the script,
                      <=60 chars; appears as the first overlay).
  script            - the full narration, plain prose, no stage directions,
                      no numbered lists, optimised for TTS, ~{words} words.
  caption_overlays  - array of 3-5 short on-screen captions, each <=60
                      chars, that summarise the spoken beats.
  visual_prompt     - one sentence describing a single cinematic B-roll
                      shot that matches the topic. Used by a generative
                      video model.
  video_description - 2-4 sentences for YouTube. End with: "Educational
                      content only — not financial advice."
  video_tags        - array of 6-12 lowercase tags, no '#'.

Return JSON only.
"""


class ScriptGenerationError(RuntimeError):
    """Raised when the LLM call fails or the JSON cannot be validated."""


@dataclass
class ScriptBundle:
    video_title: str
    script_caption: str
    script: str
    caption_overlays: List[str]
    visual_prompt: str
    video_description: str
    video_tags: List[str] = field(default_factory=list)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "video_title": self.video_title,
            "script_caption": self.script_caption,
            "script": self.script,
            "caption_overlays": list(self.caption_overlays),
            "visual_prompt": self.visual_prompt,
            "video_description": self.video_description,
            "video_tags": list(self.video_tags),
        }


def generate_script(
    *,
    video_topic: str,
    niche: str = "personal_finance",
    duration_seconds: float = 30.0,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    timeout: int = DEFAULT_TIMEOUT_S,
    dry_run: bool = False,
) -> ScriptBundle:
    """Generate a script bundle for ``video_topic``.

    ``dry_run=True`` returns a deterministic stub bundle so the pipeline
    and tests run without API keys or credits.
    """
    if not video_topic or not video_topic.strip():
        raise ScriptGenerationError("video_topic is required.")

    if dry_run:
        return _stub_bundle(video_topic, niche)

    provider = (provider or os.environ.get("SWARM_SCRIPT_PROVIDER") or DEFAULT_PROVIDER).lower()
    words = max(int(duration_seconds * 2.5), 20)  # ~150 wpm spoken
    user_prompt = USER_PROMPT_TEMPLATE.format(
        topic=video_topic,
        niche=niche,
        duration=int(duration_seconds),
        words=words,
    )

    if provider == PROVIDER_ANTHROPIC:
        raw = _call_anthropic(user_prompt, model=model, api_key=api_key, timeout=timeout)
    elif provider == PROVIDER_OPENAI:
        raw = _call_openai(user_prompt, model=model, api_key=api_key, timeout=timeout)
    else:
        raise ScriptGenerationError(f"Unknown script provider: {provider!r}")

    return _parse_bundle(raw)


# ---------------------------------------------------------------------------
# Provider calls
# ---------------------------------------------------------------------------


def _call_anthropic(prompt: str, *, model: Optional[str], api_key: Optional[str], timeout: int) -> str:
    try:
        import anthropic  # type: ignore
    except ImportError as exc:
        raise ScriptGenerationError(
            "anthropic SDK not installed. pip install anthropic"
        ) from exc

    key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise ScriptGenerationError("ANTHROPIC_API_KEY not set.")

    client = anthropic.Anthropic(api_key=key, timeout=timeout)
    model_id = model or os.environ.get("SWARM_SCRIPT_MODEL") or DEFAULT_ANTHROPIC_MODEL

    try:
        resp = client.messages.create(
            model=model_id,
            max_tokens=1200,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
    except Exception as exc:  # anthropic.APIError, network, etc.
        raise ScriptGenerationError(f"Anthropic error: {exc}") from exc

    parts = getattr(resp, "content", None) or []
    text = "".join(getattr(b, "text", "") for b in parts if getattr(b, "type", "") == "text")
    if not text.strip():
        raise ScriptGenerationError("Anthropic returned empty content.")
    return text


def _call_openai(prompt: str, *, model: Optional[str], api_key: Optional[str], timeout: int) -> str:
    try:
        import openai  # type: ignore
    except ImportError as exc:
        raise ScriptGenerationError("openai SDK not installed.") from exc

    key = api_key or os.environ.get("OPENAI_API_KEY")
    if not key:
        raise ScriptGenerationError("OPENAI_API_KEY not set.")

    client = openai.OpenAI(api_key=key, timeout=timeout)
    model_id = model or os.environ.get("SWARM_SCRIPT_MODEL") or DEFAULT_OPENAI_MODEL

    try:
        resp = client.chat.completions.create(
            model=model_id,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
        )
    except Exception as exc:
        raise ScriptGenerationError(f"OpenAI error: {exc}") from exc

    choice = (resp.choices or [None])[0]
    if not choice or not choice.message or not choice.message.content:
        raise ScriptGenerationError("OpenAI returned no content.")
    return choice.message.content


# ---------------------------------------------------------------------------
# Parsing & validation
# ---------------------------------------------------------------------------

_REQUIRED_FIELDS = (
    "video_title",
    "script_caption",
    "script",
    "caption_overlays",
    "visual_prompt",
    "video_description",
    "video_tags",
)


def _parse_bundle(raw: str) -> ScriptBundle:
    """Parse the model's raw text into a validated ``ScriptBundle``.

    Strips accidental ```json fences and other leading/trailing prose,
    then validates required fields and types.
    """
    payload = _extract_json_object(raw)
    if payload is None:
        raise ScriptGenerationError(f"LLM did not return JSON: {raw[:200]!r}")

    missing = [k for k in _REQUIRED_FIELDS if k not in payload]
    if missing:
        raise ScriptGenerationError(f"LLM JSON missing fields: {missing}")

    overlays = payload.get("caption_overlays") or []
    tags = payload.get("video_tags") or []
    if not isinstance(overlays, list) or not all(isinstance(x, str) for x in overlays):
        raise ScriptGenerationError("caption_overlays must be a list[str].")
    if not isinstance(tags, list) or not all(isinstance(x, str) for x in tags):
        raise ScriptGenerationError("video_tags must be a list[str].")

    for k in ("video_title", "script_caption", "script", "visual_prompt", "video_description"):
        if not isinstance(payload[k], str) or not payload[k].strip():
            raise ScriptGenerationError(f"Field {k!r} must be a non-empty string.")

    seen_tags: set[str] = set()
    deduped_tags: List[str] = []
    for t in tags:
        if not isinstance(t, str):
            continue
        norm = t.strip().lower()
        if norm and norm not in seen_tags:
            seen_tags.add(norm)
            deduped_tags.append(norm)

    return ScriptBundle(
        video_title=payload["video_title"].strip(),
        script_caption=payload["script_caption"].strip(),
        script=payload["script"].strip(),
        caption_overlays=[s.strip() for s in overlays if s and s.strip()],
        visual_prompt=payload["visual_prompt"].strip(),
        video_description=payload["video_description"].strip(),
        video_tags=deduped_tags,
    )


_JSON_BLOCK_RE = re.compile(r"\{.*\}", re.DOTALL)


def _extract_json_object(raw: str) -> Optional[Dict[str, Any]]:
    """Find and parse the first balanced JSON object in ``raw``."""
    text = raw.strip()

    # Easy path: whole response is JSON.
    try:
        obj = json.loads(text)
        return obj if isinstance(obj, dict) else None
    except ValueError:
        pass

    # Strip ```json fences if present.
    if text.startswith("```"):
        text = text.strip("`")
        text = re.sub(r"^json\s*", "", text, flags=re.IGNORECASE)

    match = _JSON_BLOCK_RE.search(text)
    if not match:
        return None
    try:
        obj = json.loads(match.group(0))
        return obj if isinstance(obj, dict) else None
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Dry-run stub
# ---------------------------------------------------------------------------


def _stub_bundle(topic: str, niche: str) -> ScriptBundle:
    return ScriptBundle(
        video_title=topic if len(topic) <= 70 else topic[:67] + "...",
        script_caption=f"What you need to know about {topic.split('—')[0].strip()}",
        script=(
            f"Here's what nobody tells you about {topic}. "
            "First, automate the boring part — set it and forget it. "
            "Second, track every dollar for one full month; you'll find leaks. "
            "Third, reinvest what you save. Follow for more thirty-second money tips."
        ),
        caption_overlays=[
            topic if len(topic) <= 60 else topic[:57] + "...",
            "Automate it",
            "Track every dollar",
            "Reinvest the gains",
        ],
        visual_prompt=(
            f"Cinematic close-up B-roll for the topic '{topic}', shallow depth of "
            "field, warm light, slow camera push-in."
        ),
        video_description=(
            f"{topic} — three quick wins in under 30 seconds. Save this for later "
            "and follow for daily personal-finance shorts. Educational content only — "
            "not financial advice."
        ),
        video_tags=_dedupe(
            [
                niche.replace("_", " "),
                "personal finance",
                "money tips",
                "shorts",
                "budgeting",
                "investing",
            ]
        ),
    )


def _dedupe(items: List[str]) -> List[str]:
    seen: set[str] = set()
    out: List[str] = []
    for it in items:
        key = it.strip().lower()
        if key and key not in seen:
            seen.add(key)
            out.append(key)
    return out
