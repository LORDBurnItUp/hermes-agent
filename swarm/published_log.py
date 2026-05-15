"""Append-only JSONL of every video the publish_node uploaded.

Used by ``swarm.analytics_agent`` to know which video_ids to query
against the YouTube Analytics API. Lives under the Hermes profile dir
by default so it survives between cron invocations.

Schema (one JSON object per line):

    {
      "ts": 1707930000.0,
      "run_id": "run-...",
      "video_id": "abc123",
      "topic": "Roth IRA vs Traditional IRA",
      "title": "Roth IRA vs Traditional IRA - Quick Guide",
      "niche": "personal_finance",
      "tags": ["roth ira", "personal finance"],
      "url": "https://www.youtube.com/shorts/abc123"
    }
"""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

logger = logging.getLogger(__name__)

DEFAULT_PATH_ENV = "SWARM_PUBLISHED_LOG"


def default_log_path() -> Path:
    override = os.environ.get(DEFAULT_PATH_ENV)
    if override:
        return Path(override).expanduser()
    home = Path(os.environ.get("HERMES_HOME") or (Path.home() / ".hermes"))
    return home / "swarm" / "published.jsonl"


def append_published(
    *,
    video_id: str,
    run_id: str,
    topic: str,
    title: str,
    niche: str,
    tags: List[str],
    url: str,
    path: Optional[Path] = None,
) -> Path:
    """Append a single published-video row. Returns the file path."""
    p = path or default_log_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    record: Dict[str, Any] = {
        "ts": time.time(),
        "run_id": run_id,
        "video_id": video_id,
        "topic": topic,
        "title": title,
        "niche": niche,
        "tags": list(tags or []),
        "url": url,
    }
    with p.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    logger.info("published_log appended video_id=%s", video_id)
    return p


def read_published(
    *,
    path: Optional[Path] = None,
    since_ts: float = 0.0,
    limit: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Read rows newer than ``since_ts``; newest last."""
    p = path or default_log_path()
    if not p.exists():
        return []
    rows: List[Dict[str, Any]] = []
    with p.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except ValueError:
                continue
            if row.get("ts", 0) >= since_ts:
                rows.append(row)
    if limit is not None:
        rows = rows[-limit:]
    return rows


def iter_video_ids(rows: Iterable[Dict[str, Any]]) -> List[str]:
    return [r["video_id"] for r in rows if r.get("video_id")]
