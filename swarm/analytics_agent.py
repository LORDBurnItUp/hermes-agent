"""Analytics & Feedback Agent.

Runs out-of-band from the main render pipeline (cron-scheduled) and
closes the loop between *what we published* and *what we publish next*:

    1. Read swarm/published_log.py to discover which video_ids the
       publish_node has uploaded.
    2. Query the YouTube Analytics API v2 for CTR, retention,
       view-duration, watch-time per video (last N days).
    3. Hand the metrics matrix to an LLM that returns a structured
       OptimizationReport: winners, losers, and N new topic ideas with
       why each one is grounded in the observed performance signal.
    4. Append the new topic ideas to swarm/sample_topics.csv (or the
       caller-supplied CSV) so the next ingest run picks them up.

Hygiene:
    * All network calls go through ``_with_backoff`` so a flaky
      Analytics endpoint or LLM 503 doesn't crash the cron job.
    * Dry-run mode mocks both the Analytics API and the LLM so unit
      tests stay offline and deterministic.
    * Appending to the CSV is idempotent — existing topics are skipped
      via a case-insensitive set.

Required env vars when ``dry_run=False``:

    YOUTUBE_CLIENT_ID
    YOUTUBE_CLIENT_SECRET
    YOUTUBE_REFRESH_TOKEN     # must have yt-analytics.readonly scope
    ANTHROPIC_API_KEY (or OPENAI_API_KEY with SWARM_SCRIPT_PROVIDER=openai)
"""

from __future__ import annotations

import csv
import dataclasses
import datetime as dt
import json
import logging
import os
import random
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, TypeVar

import requests

from swarm import events
from swarm.published_log import default_log_path, read_published
from swarm.script_agent import (
    PROVIDER_ANTHROPIC,
    PROVIDER_OPENAI,
    ScriptGenerationError,
    _call_anthropic,
    _call_openai,
    _extract_json_object,
)

logger = logging.getLogger(__name__)

YT_ANALYTICS_REPORTS_URL = "https://youtubeanalytics.googleapis.com/v2/reports"
TOKEN_URL = "https://oauth2.googleapis.com/token"
DEFAULT_TIMEOUT_S = 30
DEFAULT_LOOKBACK_DAYS = 14
DEFAULT_MAX_RETRIES = 4

T = TypeVar("T")


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class AnalyticsError(RuntimeError):
    """Raised on any unrecoverable failure in the analytics pipeline."""


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass
class MetricsRow:
    video_id: str
    views: int = 0
    impressions: int = 0
    ctr_pct: float = 0.0                    # impressions click-through, 0-100
    average_view_duration_seconds: float = 0.0
    estimated_minutes_watched: float = 0.0
    retention_rate: float = 0.0             # 0-1, avg_view_duration / video_length
    likes: int = 0
    comments: int = 0


@dataclass
class TopicIdea:
    video_topic: str
    script_caption: str
    niche: str
    duration_seconds: float
    why: str  # one-line rationale grounded in the metrics

    def as_csv_row(self) -> Dict[str, str]:
        return {
            "video_topic": self.video_topic,
            "script_caption": self.script_caption,
            "niche": self.niche,
            "duration_seconds": str(int(self.duration_seconds)),
        }


@dataclass
class OptimizationReport:
    generated_at: float = field(default_factory=time.time)
    analyzed_video_count: int = 0
    lookback_days: int = DEFAULT_LOOKBACK_DAYS
    winners: List[Dict[str, str]] = field(default_factory=list)
    losers: List[Dict[str, str]] = field(default_factory=list)
    new_topic_ideas: List[TopicIdea] = field(default_factory=list)
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "analyzed_video_count": self.analyzed_video_count,
            "lookback_days": self.lookback_days,
            "winners": list(self.winners),
            "losers": list(self.losers),
            "new_topic_ideas": [dataclasses.asdict(t) for t in self.new_topic_ideas],
            "notes": self.notes,
        }


# ---------------------------------------------------------------------------
# Backoff wrapper
# ---------------------------------------------------------------------------


def _with_backoff(
    fn: Callable[[], T],
    *,
    description: str,
    max_retries: int = DEFAULT_MAX_RETRIES,
    transient: Sequence[type] = (requests.RequestException, AnalyticsError),
) -> T:
    """Retry ``fn`` with exponential-backoff-plus-jitter on transient errors.

    Mirrors the supervisor's backoff envelope so analytics behaves
    identically to the main pipeline when an API misbehaves.
    """
    attempt = 0
    while True:
        try:
            return fn()
        except tuple(transient) as exc:  # type: ignore[misc]
            attempt += 1
            if attempt > max_retries:
                raise
            delay = random.uniform(0, min(2 ** (attempt - 1), 30))
            logger.warning(
                "%s failed (attempt %d/%d): %s — backing off %.1fs",
                description, attempt, max_retries, exc, delay,
            )
            time.sleep(delay)


# ---------------------------------------------------------------------------
# YouTube Analytics fetch
# ---------------------------------------------------------------------------


def _exchange_refresh_token(timeout: int = DEFAULT_TIMEOUT_S) -> str:
    cid = os.environ.get("YOUTUBE_CLIENT_ID")
    csec = os.environ.get("YOUTUBE_CLIENT_SECRET")
    rtok = os.environ.get("YOUTUBE_REFRESH_TOKEN")
    if not all((cid, csec, rtok)):
        raise AnalyticsError(
            "Analytics auth requires YOUTUBE_CLIENT_ID/SECRET/REFRESH_TOKEN "
            "(refresh token must include yt-analytics.readonly scope)."
        )
    resp = requests.post(
        TOKEN_URL,
        data={
            "client_id": cid,
            "client_secret": csec,
            "refresh_token": rtok,
            "grant_type": "refresh_token",
        },
        timeout=timeout,
    )
    if resp.status_code != 200:
        raise AnalyticsError(
            f"OAuth token exchange HTTP {resp.status_code}: {resp.text[:200]}"
        )
    token = (resp.json() or {}).get("access_token")
    if not token:
        raise AnalyticsError("OAuth response missing access_token.")
    return token


def fetch_metrics(
    video_ids: Sequence[str],
    *,
    lookback_days: int = DEFAULT_LOOKBACK_DAYS,
    timeout: int = DEFAULT_TIMEOUT_S,
    dry_run: bool = False,
) -> Dict[str, MetricsRow]:
    """Return a ``video_id -> MetricsRow`` mapping.

    Issues one Analytics report request per video (the v2 API supports
    multi-video reports too, but per-video keeps quota predictable and
    lets us tolerate one bad id without losing the batch). Failures on
    individual videos are logged and dropped, not propagated.
    """
    video_ids = [v for v in video_ids if v]
    if not video_ids:
        return {}

    if dry_run:
        return _stub_metrics(video_ids)

    token = _with_backoff(_exchange_refresh_token, description="yt-analytics OAuth")
    today = dt.date.today()
    start = (today - dt.timedelta(days=lookback_days)).isoformat()
    end = today.isoformat()

    out: Dict[str, MetricsRow] = {}
    for video_id in video_ids:
        try:
            row = _with_backoff(
                lambda vid=video_id: _fetch_one(vid, token, start, end, timeout),
                description=f"yt-analytics video={video_id}",
            )
            out[video_id] = row
        except Exception as exc:
            logger.warning("Skipping video %s: %s", video_id, exc)
    return out


def _fetch_one(video_id: str, token: str, start: str, end: str, timeout: int) -> MetricsRow:
    params = {
        "ids": "channel==MINE",
        "metrics": ",".join(
            [
                "views",
                "estimatedMinutesWatched",
                "averageViewDuration",
                "annotationClickThroughRate",
                "likes",
                "comments",
            ]
        ),
        "dimensions": "video",
        "filters": f"video=={video_id}",
        "startDate": start,
        "endDate": end,
    }
    resp = requests.get(
        YT_ANALYTICS_REPORTS_URL,
        params=params,
        headers={"authorization": f"Bearer {token}"},
        timeout=timeout,
    )
    if resp.status_code != 200:
        raise AnalyticsError(
            f"yt-analytics HTTP {resp.status_code}: {resp.text[:200]}"
        )
    return _row_from_report(video_id, resp.json() or {})


def _row_from_report(video_id: str, body: Dict[str, Any]) -> MetricsRow:
    headers = [h.get("name") for h in body.get("columnHeaders", [])]
    rows = body.get("rows") or []
    if not rows:
        return MetricsRow(video_id=video_id)
    record = rows[0]
    values = dict(zip(headers, record))

    avg_view = float(values.get("averageViewDuration") or 0)
    ctr = float(values.get("annotationClickThroughRate") or 0) * 100  # to %

    # ``estimatedMinutesWatched`` + ``views`` are reliable. Retention rate is
    # synthesised since the standard report does not expose video length.
    return MetricsRow(
        video_id=video_id,
        views=int(values.get("views") or 0),
        impressions=0,  # standard report doesn't include impressions; CTR is enough.
        ctr_pct=round(ctr, 3),
        average_view_duration_seconds=avg_view,
        estimated_minutes_watched=float(values.get("estimatedMinutesWatched") or 0),
        retention_rate=0.0,
        likes=int(values.get("likes") or 0),
        comments=int(values.get("comments") or 0),
    )


def _stub_metrics(video_ids: Sequence[str]) -> Dict[str, MetricsRow]:
    """Deterministic synthetic metrics for tests / offline cron dry-runs.

    Uses sha1 (not Python's per-process-randomised ``hash``) so values
    are stable across runs, processes, and CI workers.
    """
    import hashlib

    out: Dict[str, MetricsRow] = {}
    for vid in video_ids:
        digest = hashlib.sha1(vid.encode("utf-8")).digest()
        seed = int.from_bytes(digest[:4], "big") % 1000
        views = 1000 + seed * 5
        avg_view = 8 + (seed % 20)
        out[vid] = MetricsRow(
            video_id=vid,
            views=views,
            impressions=views * 10,
            ctr_pct=round(2.0 + (seed % 100) / 50, 2),
            average_view_duration_seconds=float(avg_view),
            estimated_minutes_watched=round(views * avg_view / 60.0, 2),
            retention_rate=round(avg_view / 30.0, 3),
            likes=seed % 50,
            comments=seed % 7,
        )
    return out


# ---------------------------------------------------------------------------
# LLM analysis
# ---------------------------------------------------------------------------


ANALYSIS_SYSTEM_PROMPT = (
    "You are the optimisation analyst for a programmatic personal-finance "
    "YouTube Shorts swarm. Given recent per-video performance data and the "
    "topic each video covered, identify what is working, what is not, and "
    "propose data-grounded next topics. Reply with strict JSON only. Never "
    "give specific financial advice; all suggestions must remain general "
    "educational content."
)


def _build_analysis_prompt(
    rows: Iterable[MetricsRow],
    history: Sequence[Dict[str, Any]],
    *,
    target_new_ideas: int,
) -> str:
    table = []
    history_by_id = {h.get("video_id"): h for h in history}
    for r in rows:
        h = history_by_id.get(r.video_id, {})
        table.append(
            {
                "video_id": r.video_id,
                "topic": h.get("topic", ""),
                "niche": h.get("niche", ""),
                "views": r.views,
                "ctr_pct": r.ctr_pct,
                "avg_view_duration_s": r.average_view_duration_seconds,
                "watch_minutes": r.estimated_minutes_watched,
                "likes": r.likes,
                "comments": r.comments,
            }
        )
    return (
        "Recent video performance (JSON):\n"
        + json.dumps(table, indent=2)
        + "\n\nReturn a JSON object with exactly these keys:\n"
        '  winners: array of {video_id, topic, why} for the top performers (max 5).\n'
        '  losers:  array of {video_id, topic, why} for the worst performers (max 5).\n'
        f'  new_topic_ideas: array of EXACTLY {target_new_ideas} objects with\n'
        "    keys {video_topic, script_caption, niche, duration_seconds, why}.\n"
        "    Each topic must be derived from a signal in the winners list\n"
        "    (e.g. similar angle, deeper dive, adjacent niche). niche must be\n"
        "    one of: personal_finance, passive_income, stock_education.\n"
        '  notes: 1-2 sentence summary of the overall trend.\n'
        "Return JSON only — no markdown fences, no preamble."
    )


def summarize_with_llm(
    rows: Dict[str, MetricsRow],
    history: Sequence[Dict[str, Any]],
    *,
    target_new_ideas: int = 5,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    timeout: int = 60,
    dry_run: bool = False,
) -> OptimizationReport:
    """Hand metrics to the LLM and parse the response into an OptimizationReport."""
    if not rows:
        logger.info("summarize_with_llm: no metrics — returning empty report")
        return OptimizationReport(analyzed_video_count=0)

    if dry_run:
        return _stub_report(rows, history, target_new_ideas=target_new_ideas)

    provider = (provider or os.environ.get("SWARM_SCRIPT_PROVIDER") or PROVIDER_ANTHROPIC).lower()
    user_prompt = _build_analysis_prompt(rows.values(), history, target_new_ideas=target_new_ideas)

    def _call() -> str:
        if provider == PROVIDER_ANTHROPIC:
            raw, _ = _call_anthropic(user_prompt, model=model, api_key=None, timeout=timeout)
        elif provider == PROVIDER_OPENAI:
            raw, _ = _call_openai(user_prompt, model=model, api_key=None, timeout=timeout)
        else:
            raise AnalyticsError(f"Unknown LLM provider: {provider!r}")
        return raw

    try:
        raw = _with_backoff(
            _call,
            description=f"analytics LLM ({provider})",
            transient=(ScriptGenerationError, AnalyticsError, requests.RequestException),
        )
    except ScriptGenerationError as exc:
        raise AnalyticsError(f"LLM analysis failed: {exc}") from exc

    return _parse_report(raw, analyzed_count=len(rows))


# ---------------------------------------------------------------------------
# Report parsing
# ---------------------------------------------------------------------------


_ALLOWED_NICHES = {"personal_finance", "passive_income", "stock_education"}


def _parse_report(raw: str, *, analyzed_count: int) -> OptimizationReport:
    obj = _extract_json_object(raw)
    if obj is None:
        raise AnalyticsError(f"Analyst LLM did not return JSON: {raw[:200]!r}")

    winners = _coerce_str_list_of_dicts(obj.get("winners") or [], keys=("video_id", "topic", "why"))
    losers = _coerce_str_list_of_dicts(obj.get("losers") or [], keys=("video_id", "topic", "why"))

    ideas_raw = obj.get("new_topic_ideas") or []
    ideas: List[TopicIdea] = []
    for item in ideas_raw:
        if not isinstance(item, dict):
            continue
        topic = (item.get("video_topic") or "").strip()
        if not topic:
            continue
        niche = (item.get("niche") or "personal_finance").strip().lower()
        if niche not in _ALLOWED_NICHES:
            niche = "personal_finance"
        try:
            duration = float(item.get("duration_seconds") or 30.0)
        except (TypeError, ValueError):
            duration = 30.0
        ideas.append(
            TopicIdea(
                video_topic=topic,
                script_caption=(item.get("script_caption") or topic)[:60],
                niche=niche,
                duration_seconds=max(min(duration, 60.0), 15.0),
                why=(item.get("why") or "").strip(),
            )
        )

    notes = (obj.get("notes") or "").strip()
    return OptimizationReport(
        analyzed_video_count=analyzed_count,
        winners=winners,
        losers=losers,
        new_topic_ideas=ideas,
        notes=notes,
    )


def _coerce_str_list_of_dicts(items: Any, *, keys: Sequence[str]) -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    if not isinstance(items, list):
        return out
    for it in items:
        if not isinstance(it, dict):
            continue
        out.append({k: str(it.get(k, "")).strip() for k in keys})
    return out


def _stub_report(
    rows: Dict[str, MetricsRow],
    history: Sequence[Dict[str, Any]],
    *,
    target_new_ideas: int,
) -> OptimizationReport:
    """Deterministic synthetic report used by tests/dry-run."""
    by_id = {h.get("video_id"): h for h in history}
    ranked = sorted(rows.values(), key=lambda r: (r.views, r.ctr_pct), reverse=True)
    winners = [
        {
            "video_id": r.video_id,
            "topic": by_id.get(r.video_id, {}).get("topic", ""),
            "why": f"high CTR ({r.ctr_pct}%) and {r.views} views",
        }
        for r in ranked[: min(3, len(ranked))]
    ]
    losers = [
        {
            "video_id": r.video_id,
            "topic": by_id.get(r.video_id, {}).get("topic", ""),
            "why": f"low CTR ({r.ctr_pct}%)",
        }
        for r in ranked[-min(2, len(ranked)) :]
        if ranked
    ]

    # Synthesise N new topics deterministically off the winner topics.
    base_topics = [w["topic"] or "Personal Finance" for w in winners] or ["Personal Finance"]
    ideas: List[TopicIdea] = []
    for i in range(target_new_ideas):
        base = base_topics[i % len(base_topics)]
        ideas.append(
            TopicIdea(
                video_topic=f"{base} — Deeper Dive #{i + 1}",
                script_caption=f"New angle on {base}",
                niche="personal_finance",
                duration_seconds=30.0,
                why=f"Adjacent angle to winning topic {base!r}",
            )
        )
    return OptimizationReport(
        analyzed_video_count=len(rows),
        winners=winners,
        losers=losers,
        new_topic_ideas=ideas,
        notes="stub report (dry_run=True)",
    )


# ---------------------------------------------------------------------------
# CSV append (idempotent)
# ---------------------------------------------------------------------------

CSV_FIELDS = ["video_topic", "script_caption", "niche", "duration_seconds"]


def append_topics_to_csv(
    report: OptimizationReport,
    csv_path: Path,
    *,
    comment_provenance: bool = True,
) -> int:
    """Append every new topic in ``report`` to ``csv_path``.

    Returns the number of rows actually written. Existing topics (case-
    insensitive match on ``video_topic``) are skipped — this makes the
    cron job idempotent across reruns.
    """
    csv_path = Path(csv_path)
    existing: set[str] = set()
    write_header = not csv_path.exists()

    if csv_path.exists():
        with csv_path.open("r", encoding="utf-8-sig", newline="") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                topic = (row.get("video_topic") or "").strip().lower()
                if topic:
                    existing.add(topic)

    new_rows: List[TopicIdea] = [
        t for t in report.new_topic_ideas if t.video_topic.strip().lower() not in existing
    ]
    if not new_rows:
        return 0

    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("a", encoding="utf-8", newline="") as fh:
        if write_header:
            fh.write(",".join(CSV_FIELDS) + "\n")
        if comment_provenance:
            fh.write(
                f"# appended by analytics_agent at "
                f"{dt.datetime.fromtimestamp(report.generated_at).isoformat()} "
                f"({report.analyzed_video_count} videos analysed)\n"
            )
        writer = csv.DictWriter(fh, fieldnames=CSV_FIELDS, extrasaction="ignore")
        for topic in new_rows:
            writer.writerow(topic.as_csv_row())
    logger.info("append_topics_to_csv: wrote %d new rows to %s", len(new_rows), csv_path)
    return len(new_rows)


# ---------------------------------------------------------------------------
# Full cycle
# ---------------------------------------------------------------------------


@dataclass
class AnalyticsCycleResult:
    analyzed_video_count: int
    new_rows_written: int
    report_path: Optional[Path]
    csv_path: Path


def run_analytics_cycle(
    *,
    csv_path: Path,
    published_log_path: Optional[Path] = None,
    report_dir: Optional[Path] = None,
    lookback_days: int = DEFAULT_LOOKBACK_DAYS,
    target_new_ideas: int = 5,
    dry_run: bool = False,
) -> AnalyticsCycleResult:
    """One full pull → summarise → append cycle. Returns a summary.

    Emits Live View events at every step so dashboards can show the
    cron's progress in real time.
    """
    csv_path = Path(csv_path)
    published_log_path = Path(published_log_path) if published_log_path else default_log_path()
    cycle_id = f"analytics-{int(time.time())}"

    events.publish(
        {"type": "analytics.start", "cycle_id": cycle_id, "lookback_days": lookback_days}
    )

    history = read_published(path=published_log_path)
    video_ids = [h["video_id"] for h in history if h.get("video_id")]
    if not video_ids:
        logger.info("No published videos yet — nothing to analyse.")
        events.publish({"type": "analytics.empty", "cycle_id": cycle_id})
        return AnalyticsCycleResult(0, 0, None, csv_path)

    metrics = fetch_metrics(video_ids, lookback_days=lookback_days, dry_run=dry_run)
    events.publish(
        {
            "type": "analytics.fetched",
            "cycle_id": cycle_id,
            "video_count": len(metrics),
        }
    )

    report = summarize_with_llm(
        metrics, history, target_new_ideas=target_new_ideas, dry_run=dry_run
    )
    report.lookback_days = lookback_days
    events.publish(
        {
            "type": "analytics.summarised",
            "cycle_id": cycle_id,
            "winners": len(report.winners),
            "losers": len(report.losers),
            "new_ideas": len(report.new_topic_ideas),
        }
    )

    new_rows = append_topics_to_csv(report, csv_path)
    report_path: Optional[Path] = None
    if report_dir is not None:
        report_dir = Path(report_dir)
        report_dir.mkdir(parents=True, exist_ok=True)
        report_path = report_dir / f"{cycle_id}.json"
        report_path.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")

    events.publish(
        {
            "type": "analytics.complete",
            "cycle_id": cycle_id,
            "new_rows_written": new_rows,
            "csv_path": str(csv_path),
        }
    )

    return AnalyticsCycleResult(
        analyzed_video_count=len(metrics),
        new_rows_written=new_rows,
        report_path=report_path,
        csv_path=csv_path,
    )
