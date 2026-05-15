"""Phase 4 tests for the analytics & feedback agent."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import List

import pytest

from swarm.analytics_agent import (
    AnalyticsError,
    DEFAULT_LOOKBACK_DAYS,
    MetricsRow,
    OptimizationReport,
    TopicIdea,
    _parse_report,
    _stub_metrics,
    _stub_report,
    append_topics_to_csv,
    fetch_metrics,
    run_analytics_cycle,
    summarize_with_llm,
)
from swarm.published_log import append_published, read_published


# ---------------------------------------------------------------------------
# fetch_metrics
# ---------------------------------------------------------------------------


def test_fetch_metrics_dry_run_returns_one_row_per_video():
    rows = fetch_metrics(["vidA", "vidB", "vidC"], dry_run=True)
    assert set(rows.keys()) == {"vidA", "vidB", "vidC"}
    for r in rows.values():
        assert isinstance(r, MetricsRow)
        assert r.views > 0
        assert 0 <= r.ctr_pct <= 100


def test_fetch_metrics_empty_input_returns_empty_dict():
    assert fetch_metrics([], dry_run=True) == {}


def test_fetch_metrics_dry_run_is_deterministic():
    a = fetch_metrics(["repeat"], dry_run=True)
    b = fetch_metrics(["repeat"], dry_run=True)
    assert a["repeat"].views == b["repeat"].views
    assert a["repeat"].ctr_pct == b["repeat"].ctr_pct


# ---------------------------------------------------------------------------
# summarize_with_llm
# ---------------------------------------------------------------------------


def test_summarize_dry_run_produces_full_report():
    history = [
        {"video_id": "v1", "topic": "Roth IRA", "niche": "personal_finance"},
        {"video_id": "v2", "topic": "Dividend ETFs", "niche": "passive_income"},
        {"video_id": "v3", "topic": "P/E Ratios", "niche": "stock_education"},
    ]
    metrics = _stub_metrics([h["video_id"] for h in history])
    report = summarize_with_llm(metrics, history, target_new_ideas=4, dry_run=True)
    assert report.analyzed_video_count == 3
    assert len(report.new_topic_ideas) == 4
    assert report.winners
    for idea in report.new_topic_ideas:
        assert idea.video_topic
        assert idea.niche in {"personal_finance", "passive_income", "stock_education"}


def test_summarize_handles_empty_metrics_gracefully():
    report = summarize_with_llm({}, history=[], dry_run=True)
    assert report.analyzed_video_count == 0
    assert report.new_topic_ideas == []


def test_parse_report_extracts_fields_and_normalises_niche():
    raw = json.dumps(
        {
            "winners": [{"video_id": "v1", "topic": "Roth IRA", "why": "high CTR"}],
            "losers":  [{"video_id": "v2", "topic": "Bonds 101", "why": "low CTR"}],
            "new_topic_ideas": [
                {
                    "video_topic": "Roth IRA Conversion Ladders",
                    "script_caption": "Lower your tax bill at retirement",
                    "niche": "PERSONAL_FINANCE",
                    "duration_seconds": "45",
                    "why": "Adjacent to top winner",
                },
                {
                    "video_topic": "  ",  # should be dropped
                    "niche": "weird",
                },
            ],
            "notes": "CTR rising across finance bucket.",
        }
    )
    report = _parse_report(raw, analyzed_count=2)
    assert len(report.winners) == 1
    assert len(report.losers) == 1
    assert len(report.new_topic_ideas) == 1
    idea = report.new_topic_ideas[0]
    assert idea.niche == "personal_finance"
    assert idea.duration_seconds == 45.0
    assert report.notes.startswith("CTR rising")


def test_parse_report_rejects_non_json():
    with pytest.raises(AnalyticsError):
        _parse_report("definitely not json", analyzed_count=0)


def test_parse_report_clamps_duration_to_15_60_range():
    raw = json.dumps(
        {
            "winners": [],
            "losers": [],
            "new_topic_ideas": [
                {"video_topic": "Tiny", "niche": "personal_finance", "duration_seconds": 1},
                {"video_topic": "Huge", "niche": "personal_finance", "duration_seconds": 999},
            ],
            "notes": "",
        }
    )
    report = _parse_report(raw, analyzed_count=0)
    durations = sorted(t.duration_seconds for t in report.new_topic_ideas)
    assert durations == [15.0, 60.0]


# ---------------------------------------------------------------------------
# append_topics_to_csv
# ---------------------------------------------------------------------------


def test_append_topics_creates_new_csv(tmp_path: Path):
    csv_path = tmp_path / "topics.csv"
    report = OptimizationReport(
        new_topic_ideas=[
            TopicIdea("New Topic A", "cap A", "personal_finance", 30.0, "why"),
            TopicIdea("New Topic B", "cap B", "stock_education", 45.0, "why"),
        ]
    )
    n = append_topics_to_csv(report, csv_path)
    assert n == 2
    body = csv_path.read_text(encoding="utf-8")
    assert "video_topic" in body  # header written
    assert "New Topic A" in body
    assert "New Topic B" in body


def test_append_topics_skips_existing_case_insensitive(tmp_path: Path):
    csv_path = tmp_path / "topics.csv"
    csv_path.write_text(
        "video_topic,script_caption,niche,duration_seconds\n"
        "Already Here,cap,personal_finance,30\n",
        encoding="utf-8",
    )
    report = OptimizationReport(
        new_topic_ideas=[
            TopicIdea("already here", "cap", "personal_finance", 30.0, "why"),  # dupe
            TopicIdea("Fresh Idea", "cap", "personal_finance", 30.0, "why"),
        ]
    )
    n = append_topics_to_csv(report, csv_path)
    assert n == 1
    body = csv_path.read_text(encoding="utf-8")
    assert body.lower().count("already here") == 1
    assert "Fresh Idea" in body


def test_append_topics_with_empty_report_does_nothing(tmp_path: Path):
    csv_path = tmp_path / "topics.csv"
    assert append_topics_to_csv(OptimizationReport(), csv_path) == 0
    assert not csv_path.exists()


# ---------------------------------------------------------------------------
# published_log
# ---------------------------------------------------------------------------


def test_published_log_round_trip(tmp_path: Path):
    log = tmp_path / "published.jsonl"
    append_published(
        video_id="v1", run_id="r1", topic="T", title="T1",
        niche="personal_finance", tags=["a", "b"], url="https://yt/v1",
        path=log,
    )
    append_published(
        video_id="v2", run_id="r2", topic="U", title="U1",
        niche="passive_income", tags=[], url="https://yt/v2",
        path=log,
    )
    rows = read_published(path=log)
    assert [r["video_id"] for r in rows] == ["v1", "v2"]
    assert rows[0]["niche"] == "personal_finance"


def test_published_log_since_filter(tmp_path: Path):
    log = tmp_path / "published.jsonl"
    append_published(
        video_id="old", run_id="r0", topic="X", title="X", niche="x",
        tags=[], url="", path=log,
    )
    # Backdate the first row by rewriting the file
    raw = log.read_text(encoding="utf-8")
    log.write_text(raw.replace(f'"ts": {json.loads(raw)["ts"]}', '"ts": 100'), encoding="utf-8")
    append_published(
        video_id="new", run_id="r1", topic="Y", title="Y", niche="y",
        tags=[], url="", path=log,
    )
    recent = read_published(path=log, since_ts=time.time() - 60)
    assert [r["video_id"] for r in recent] == ["new"]


# ---------------------------------------------------------------------------
# run_analytics_cycle end-to-end
# ---------------------------------------------------------------------------


def test_run_analytics_cycle_with_no_history(tmp_path: Path):
    log = tmp_path / "empty.jsonl"
    csv_path = tmp_path / "topics.csv"
    result = run_analytics_cycle(
        csv_path=csv_path,
        published_log_path=log,
        dry_run=True,
    )
    assert result.analyzed_video_count == 0
    assert result.new_rows_written == 0


def test_run_analytics_cycle_writes_new_topics(tmp_path: Path):
    log = tmp_path / "published.jsonl"
    for i in range(3):
        append_published(
            video_id=f"vid{i}",
            run_id=f"r{i}",
            topic=f"Topic {i}",
            title=f"Title {i}",
            niche="personal_finance",
            tags=["t"],
            url=f"https://yt/vid{i}",
            path=log,
        )

    csv_path = tmp_path / "topics.csv"
    report_dir = tmp_path / "reports"

    first = run_analytics_cycle(
        csv_path=csv_path,
        published_log_path=log,
        report_dir=report_dir,
        target_new_ideas=5,
        dry_run=True,
    )
    assert first.analyzed_video_count == 3
    assert first.new_rows_written == 5
    assert first.report_path is not None and first.report_path.exists()

    saved = json.loads(first.report_path.read_text(encoding="utf-8"))
    assert saved["analyzed_video_count"] == 3
    assert saved["lookback_days"] == DEFAULT_LOOKBACK_DAYS

    # Re-running the cron is idempotent: same dry-run output, no duplicates.
    second = run_analytics_cycle(
        csv_path=csv_path,
        published_log_path=log,
        report_dir=report_dir,
        target_new_ideas=5,
        dry_run=True,
    )
    assert second.new_rows_written == 0


def test_topic_idea_csv_row_keys_match_csv_fields():
    idea = TopicIdea("Topic", "cap", "personal_finance", 30.0, "why")
    row = idea.as_csv_row()
    assert set(row.keys()) == {"video_topic", "script_caption", "niche", "duration_seconds"}
