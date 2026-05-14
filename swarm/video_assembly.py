"""Shotstack video assembly — cloud rendering via JSON edit-decision list.

We never touch FFmpeg. Instead we build a JSON timeline (background
B-roll, voiceover audio, dynamic text overlays with merge fields) and
POST it to Shotstack's ``/render`` endpoint. The Supervisor handles the
polling and retry of the render lifecycle.

References:
    - Shotstack timeline JSON schema (clips, tracks, transitions, soundtrack)
    - Merge fields: ``{{VIDEO_TITLE}}``, ``{{SCRIPT_CAPTION}}``, ...
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

SHOTSTACK_BASE_URL = "https://api.shotstack.io/edit/{stage}"
DEFAULT_STAGE = "stage"  # "v1" for production
DEFAULT_TIMEOUT_S = 30

# Curated B-roll pools per niche. The orchestrator can swap in dynamic
# stock-API queries later; hard-coded URLs keep the demo deterministic.
NICHE_BROLL: Dict[str, List[str]] = {
    "personal_finance": [
        "https://shotstack-assets.s3.amazonaws.com/footage/finance-charts-1.mp4",
        "https://shotstack-assets.s3.amazonaws.com/footage/finance-skyline-1.mp4",
    ],
    "passive_income": [
        "https://shotstack-assets.s3.amazonaws.com/footage/laptop-cafe-1.mp4",
        "https://shotstack-assets.s3.amazonaws.com/footage/coins-stack-1.mp4",
    ],
    "stock_education": [
        "https://shotstack-assets.s3.amazonaws.com/footage/candlestick-chart-1.mp4",
        "https://shotstack-assets.s3.amazonaws.com/footage/trader-monitors-1.mp4",
    ],
}


class VideoAssemblyError(RuntimeError):
    """Raised when Shotstack rejects the payload or the render request fails."""


@dataclass
class RenderRequestResult:
    render_id: str
    status: str


def build_shotstack_payload(
    *,
    video_title: str,
    script_caption: str,
    audio_url: str,
    niche: str = "personal_finance",
    duration_seconds: float = 30.0,
    output_resolution: str = "hd",
    overlay_lines: Optional[List[str]] = None,
    broll_urls: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Construct a Shotstack edit-decision list as a plain dict.

    The dict is JSON-serialisable and intentionally readable so it can be
    diffed in PRs and rendered as a sample by the demo runner.
    """
    if not video_title:
        raise VideoAssemblyError("video_title is required.")
    if not audio_url:
        raise VideoAssemblyError("audio_url is required.")

    broll = broll_urls or NICHE_BROLL.get(niche) or NICHE_BROLL["personal_finance"]
    overlay_lines = overlay_lines or [script_caption]

    # Distribute B-roll evenly across the audio duration.
    per_clip = max(duration_seconds / max(len(broll), 1), 4.0)
    broll_clips: List[Dict[str, Any]] = []
    cursor = 0.0
    for url in broll:
        broll_clips.append(
            {
                "asset": {"type": "video", "src": url},
                "start": round(cursor, 3),
                "length": round(per_clip, 3),
                "fit": "cover",
                "effect": "zoomIn",
                "transition": {"in": "fade", "out": "fade"},
            }
        )
        cursor += per_clip
        if cursor >= duration_seconds:
            break

    # Title card — burned in for the first 4 seconds.
    title_clip = {
        "asset": {
            "type": "title",
            "text": "{{VIDEO_TITLE}}",
            "style": "blockbuster",
            "color": "#ffffff",
            "background": "#0b1d3a",
            "size": "large",
            "position": "center",
        },
        "start": 0,
        "length": 4,
        "transition": {"in": "fade", "out": "fade"},
    }

    # Rolling caption track — one caption per overlay line, spread across the timeline.
    caption_clips: List[Dict[str, Any]] = []
    if overlay_lines:
        slot = max(duration_seconds / len(overlay_lines), 3.0)
        for idx, line in enumerate(overlay_lines):
            caption_clips.append(
                {
                    "asset": {
                        "type": "html",
                        "html": (
                            "<p style='font-family:Inter,Arial;font-size:48px;"
                            "color:#ffffff;text-shadow:0 2px 6px rgba(0,0,0,.7);"
                            "text-align:center;'>{{SCRIPT_CAPTION}}</p>"
                        ),
                        "width": 1280,
                        "height": 200,
                    },
                    "start": round(idx * slot, 3),
                    "length": round(min(slot, duration_seconds - idx * slot), 3),
                    "position": "bottom",
                    "offset": {"y": 0.08},
                    "transition": {"in": "slideUp", "out": "fade"},
                    "merge": [{"find": "SCRIPT_CAPTION", "replace": line}],
                }
            )

    payload: Dict[str, Any] = {
        "timeline": {
            "background": "#000000",
            "soundtrack": {"src": audio_url, "effect": "fadeOut"},
            "tracks": [
                {"clips": caption_clips},
                {"clips": [title_clip]},
                {"clips": broll_clips},
            ],
        },
        "output": {
            "format": "mp4",
            "resolution": output_resolution,
            "aspectRatio": "9:16",  # vertical for YouTube Shorts.
            "fps": 30,
        },
        "merge": [
            {"find": "VIDEO_TITLE", "replace": video_title},
            {"find": "SCRIPT_CAPTION", "replace": script_caption},
        ],
    }
    return payload


def submit_render(
    payload: Dict[str, Any],
    *,
    api_key: Optional[str] = None,
    stage: str = DEFAULT_STAGE,
    timeout: int = DEFAULT_TIMEOUT_S,
    dry_run: bool = False,
) -> RenderRequestResult:
    """POST the JSON payload to Shotstack and return the render id.

    Raises ``VideoAssemblyError`` on any failure so the LangGraph node
    can hand control to the Supervisor for retry.
    """
    if dry_run:
        stub_id = f"dryrun-{int(time.time())}"
        logger.info("Shotstack dry-run; returning render_id=%s", stub_id)
        return RenderRequestResult(render_id=stub_id, status="queued")

    api_key = api_key or os.environ.get("SHOTSTACK_API_KEY")
    if not api_key:
        raise VideoAssemblyError(
            "SHOTSTACK_API_KEY not set. Pass dry_run=True for offline demos."
        )

    url = SHOTSTACK_BASE_URL.format(stage=stage) + "/render"
    headers = {"x-api-key": api_key, "content-type": "application/json"}

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
    except requests.RequestException as exc:
        raise VideoAssemblyError(f"Shotstack network error: {exc}") from exc

    if resp.status_code not in (200, 201):
        raise VideoAssemblyError(
            f"Shotstack /render returned HTTP {resp.status_code}: {resp.text[:300]}"
        )

    data = resp.json() or {}
    response_block = data.get("response") or {}
    render_id = response_block.get("id")
    if not render_id:
        raise VideoAssemblyError(f"Shotstack response missing render id: {data}")

    return RenderRequestResult(render_id=render_id, status=response_block.get("message", "queued"))


def poll_render(
    render_id: str,
    *,
    api_key: Optional[str] = None,
    stage: str = DEFAULT_STAGE,
    timeout: int = DEFAULT_TIMEOUT_S,
) -> Dict[str, Any]:
    """Single GET to ``/render/{id}``. The Supervisor decides when to call again."""
    api_key = api_key or os.environ.get("SHOTSTACK_API_KEY")
    if not api_key:
        raise VideoAssemblyError("SHOTSTACK_API_KEY not set.")

    url = SHOTSTACK_BASE_URL.format(stage=stage) + f"/render/{render_id}"
    headers = {"x-api-key": api_key}
    try:
        resp = requests.get(url, headers=headers, timeout=timeout)
    except requests.RequestException as exc:
        raise VideoAssemblyError(f"Shotstack poll network error: {exc}") from exc

    if resp.status_code != 200:
        raise VideoAssemblyError(
            f"Shotstack /render/{render_id} HTTP {resp.status_code}: {resp.text[:200]}"
        )
    return resp.json() or {}
