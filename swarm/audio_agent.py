"""ElevenLabs voiceover agent — pure ``requests``, no SDK.

Takes a finance script string, posts it to the ElevenLabs TTS REST API,
uploads the resulting MP3 to a public bucket (or the caller's upload
function), and returns the URL ready to drop into a Shotstack timeline.

Constraints from the Phase 2 spec:
    - No FFmpeg, no SDK — raw ``requests`` only.
    - Errors must propagate so the Supervisor can decide to retry.
    - Returning ``None`` is reserved for explicit dry-run mode.
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from typing import Callable, Optional

import requests

logger = logging.getLogger(__name__)

ELEVENLABS_TTS_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
DEFAULT_VOICE_ID = "21m00Tcm4TlvDq8ikWAM"  # ElevenLabs "Rachel" — neutral US english.
DEFAULT_MODEL_ID = "eleven_turbo_v2_5"
DEFAULT_TIMEOUT_S = 60


class AudioGenerationError(RuntimeError):
    """Raised when ElevenLabs fails — caught by the supervisor for retry."""


@dataclass
class VoiceoverResult:
    audio_url: str
    duration_seconds: Optional[float]
    bytes_written: int


# Uploader signature: (mp3_bytes, suggested_filename) -> public_url
Uploader = Callable[[bytes, str], str]


def generate_voiceover(
    script: str,
    *,
    voice_id: Optional[str] = None,
    model_id: str = DEFAULT_MODEL_ID,
    api_key: Optional[str] = None,
    uploader: Optional[Uploader] = None,
    timeout: int = DEFAULT_TIMEOUT_S,
    dry_run: bool = False,
) -> VoiceoverResult:
    """Synthesize ``script`` to MP3 and return a URL usable by Shotstack.

    Parameters
    ----------
    script:
        The narration text. The script node should keep this under ~5000
        chars for a single ElevenLabs call (≈5 min of audio at ~150 wpm).
    voice_id:
        ElevenLabs voice. Defaults to "Rachel" — replace per-niche later.
    uploader:
        Function that publishes MP3 bytes to a publicly readable URL.
        If omitted, falls back to ``ELEVENLABS_AUDIO_BASE_URL`` env var
        treated as a pre-signed PUT target (S3-compatible).
    dry_run:
        If True, returns a stub URL without calling the API. Used by the
        demo runner so a sample Shotstack JSON can be printed without
        burning credits.
    """
    if not script or not script.strip():
        raise AudioGenerationError("Empty script — nothing to synthesize.")

    voice_id = voice_id or DEFAULT_VOICE_ID

    if dry_run:
        stub_url = f"https://example.invalid/dry-run/{voice_id}.mp3"
        logger.info("ElevenLabs dry-run; returning stub url=%s", stub_url)
        return VoiceoverResult(audio_url=stub_url, duration_seconds=None, bytes_written=0)

    api_key = api_key or os.environ.get("ELEVENLABS_API_KEY")
    if not api_key:
        raise AudioGenerationError(
            "ELEVENLABS_API_KEY not set. Pass dry_run=True for offline demos."
        )

    url = ELEVENLABS_TTS_URL.format(voice_id=voice_id)
    headers = {
        "xi-api-key": api_key,
        "accept": "audio/mpeg",
        "content-type": "application/json",
    }
    body = {
        "text": script,
        "model_id": model_id,
        "voice_settings": {
            "stability": 0.45,
            "similarity_boost": 0.75,
            "style": 0.35,
            "use_speaker_boost": True,
        },
    }

    started = time.monotonic()
    try:
        resp = requests.post(url, headers=headers, json=body, timeout=timeout)
    except requests.RequestException as exc:
        raise AudioGenerationError(f"ElevenLabs network error: {exc}") from exc

    if resp.status_code != 200:
        raise AudioGenerationError(
            f"ElevenLabs returned HTTP {resp.status_code}: {resp.text[:300]}"
        )

    mp3_bytes = resp.content
    elapsed = time.monotonic() - started
    logger.info("ElevenLabs synth ok: %d bytes in %.2fs", len(mp3_bytes), elapsed)

    audio_url = _upload(mp3_bytes, voice_id=voice_id, uploader=uploader)
    return VoiceoverResult(
        audio_url=audio_url,
        duration_seconds=None,  # ElevenLabs doesn't return this on /v1; compute downstream if needed.
        bytes_written=len(mp3_bytes),
    )


def _upload(mp3_bytes: bytes, *, voice_id: str, uploader: Optional[Uploader]) -> str:
    if uploader is not None:
        return uploader(mp3_bytes, f"vo-{voice_id}-{int(time.time())}.mp3")

    presigned = os.environ.get("ELEVENLABS_AUDIO_PUT_URL")
    if presigned:
        put = requests.put(presigned, data=mp3_bytes, headers={"content-type": "audio/mpeg"}, timeout=60)
        if put.status_code not in (200, 201, 204):
            raise AudioGenerationError(f"Audio upload failed: HTTP {put.status_code}")
        # Strip the query string to get the public read URL.
        return presigned.split("?", 1)[0]

    raise AudioGenerationError(
        "No uploader configured. Pass an uploader=... callback or set "
        "ELEVENLABS_AUDIO_PUT_URL to a pre-signed S3 PUT URL."
    )
