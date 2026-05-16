"""CSV → topic queue ingestion.

The orchestrator reads a spreadsheet of raw financial topics and emits
one ``TopicRow`` per line. Each row becomes an independent LangGraph
run, so a 500-row CSV produces 500 videos.

Expected columns (case-insensitive; extras are preserved in ``extras``):

    video_topic           required — used as {{VIDEO_TITLE}}
    script_caption        optional — short tagline burned on screen
    niche                 optional — defaults to "personal_finance"
    voice_id              optional — ElevenLabs voice id
    duration_seconds      optional — defaults to 30

Empty rows and rows starting with ``#`` are skipped.
"""

from __future__ import annotations

import csv
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

logger = logging.getLogger(__name__)

REQUIRED_COLUMNS = ("video_topic",)
KNOWN_COLUMNS = (
    "video_topic",
    "script_caption",
    "niche",
    "voice_id",
    "duration_seconds",
)


@dataclass
class TopicRow:
    video_topic: str
    script_caption: str = ""
    niche: str = "personal_finance"
    voice_id: str = ""
    duration_seconds: float = 30.0
    extras: Dict[str, str] = field(default_factory=dict)


def ingest_topics_from_csv(
    path: str | Path,
    *,
    encoding: str = "utf-8-sig",
) -> List[TopicRow]:
    """Parse ``path`` and return a list of ``TopicRow``.

    Raises ``ValueError`` for missing required columns so the operator
    sees the problem immediately rather than mid-pipeline.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"CSV not found: {p}")

    with p.open("r", encoding=encoding, newline="") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames is None:
            raise ValueError(f"{p} has no header row.")

        normalized = {c.lower().strip(): c for c in reader.fieldnames}
        missing = [c for c in REQUIRED_COLUMNS if c not in normalized]
        if missing:
            raise ValueError(
                f"{p} missing required column(s): {missing}. "
                f"Found: {list(reader.fieldnames)}"
            )

        rows: List[TopicRow] = []
        for raw in reader:
            topic = (raw.get(normalized["video_topic"]) or "").strip()
            if not topic or topic.startswith("#"):
                continue
            rows.append(_row_from_dict(raw, normalized))

    logger.info("Ingested %d topic rows from %s", len(rows), p)
    return rows


def _row_from_dict(raw: Dict[str, Any], normalized: Dict[str, str]) -> TopicRow:
    def get(key: str, default: str = "") -> str:
        src = normalized.get(key)
        if src is None:
            return default
        val = raw.get(src)
        return (val or default).strip() if isinstance(val, str) else default

    duration_raw = get("duration_seconds", "30")
    try:
        duration = float(duration_raw) if duration_raw else 30.0
    except ValueError:
        logger.warning("Invalid duration_seconds=%r; defaulting to 30", duration_raw)
        duration = 30.0

    extras = {
        k: (v or "").strip()
        for k, v in raw.items()
        if k and k.lower().strip() not in KNOWN_COLUMNS and v
    }

    return TopicRow(
        video_topic=get("video_topic"),
        script_caption=get("script_caption"),
        niche=get("niche", "personal_finance") or "personal_finance",
        voice_id=get("voice_id"),
        duration_seconds=duration,
        extras=extras,
    )


def iter_topic_payloads(rows: Iterable[TopicRow]) -> Iterable[Dict[str, Any]]:
    """Adapter: TopicRow → kwargs accepted by ``run_pipeline``."""
    for row in rows:
        yield {
            "video_topic": row.video_topic,
            "script_caption": row.script_caption or row.video_topic,
            "niche": row.niche,
            "voice_id": row.voice_id or None,
            "duration_seconds": row.duration_seconds,
        }
