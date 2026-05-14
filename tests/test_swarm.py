"""Phase 2 unit tests for the Swarm OS package."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from swarm.audio_agent import AudioGenerationError, generate_voiceover
from swarm.csv_ingest import ingest_topics_from_csv
from swarm.graph import build_graph, run_pipeline
from swarm.state import NodeStatus, SupervisorDecision, new_state
from swarm.supervisor import supervise
from swarm.video_assembly import VideoAssemblyError, build_shotstack_payload


# ---------------------------------------------------------------------------
# build_shotstack_payload
# ---------------------------------------------------------------------------


def test_shotstack_payload_has_required_top_level_keys():
    payload = build_shotstack_payload(
        video_title="Test Title",
        script_caption="Caption",
        audio_url="https://example.com/a.mp3",
    )
    assert {"timeline", "output", "merge"} <= payload.keys()
    assert payload["output"]["format"] == "mp4"
    assert payload["output"]["aspectRatio"] == "9:16"


def test_shotstack_payload_includes_merge_fields_and_soundtrack():
    payload = build_shotstack_payload(
        video_title="My Video",
        script_caption="Hello",
        audio_url="https://cdn.example.com/voice.mp3",
        overlay_lines=["A", "B", "C"],
    )
    merge_keys = {m["find"] for m in payload["merge"]}
    assert "VIDEO_TITLE" in merge_keys and "SCRIPT_CAPTION" in merge_keys
    assert payload["timeline"]["soundtrack"]["src"] == "https://cdn.example.com/voice.mp3"

    # Three caption clips, one per overlay line.
    caption_track = payload["timeline"]["tracks"][0]
    assert len(caption_track["clips"]) == 3
    captions = [c["merge"][0]["replace"] for c in caption_track["clips"]]
    assert captions == ["A", "B", "C"]


def test_shotstack_payload_rejects_missing_inputs():
    with pytest.raises(VideoAssemblyError):
        build_shotstack_payload(video_title="", script_caption="x", audio_url="x")
    with pytest.raises(VideoAssemblyError):
        build_shotstack_payload(video_title="x", script_caption="x", audio_url="")


def test_shotstack_payload_is_json_serializable():
    payload = build_shotstack_payload(
        video_title="x",
        script_caption="y",
        audio_url="https://e/x.mp3",
    )
    # Round trip — must not raise.
    json.loads(json.dumps(payload))


# ---------------------------------------------------------------------------
# audio_agent
# ---------------------------------------------------------------------------


def test_voiceover_dry_run_returns_stub_url():
    result = generate_voiceover("Some script", dry_run=True)
    assert result.audio_url.startswith("https://example.invalid/dry-run/")
    assert result.bytes_written == 0


def test_voiceover_rejects_empty_script():
    with pytest.raises(AudioGenerationError):
        generate_voiceover("   ", dry_run=True)


# ---------------------------------------------------------------------------
# csv_ingest
# ---------------------------------------------------------------------------


def test_csv_ingest_parses_known_columns_and_skips_comments(tmp_path: Path):
    csv_path = tmp_path / "topics.csv"
    csv_path.write_text(
        "video_topic,script_caption,niche,duration_seconds\n"
        "Budgeting,Tip 1,personal_finance,30\n"
        "# comment row,,,\n"
        ",,,\n"
        "Dividends,Sleep money,passive_income,45\n",
        encoding="utf-8",
    )
    rows = ingest_topics_from_csv(csv_path)
    assert len(rows) == 2
    assert rows[0].video_topic == "Budgeting"
    assert rows[0].niche == "personal_finance"
    assert rows[1].duration_seconds == 45.0


def test_csv_ingest_requires_topic_column(tmp_path: Path):
    bad = tmp_path / "bad.csv"
    bad.write_text("title,niche\nA,B\n", encoding="utf-8")
    with pytest.raises(ValueError):
        ingest_topics_from_csv(bad)


# ---------------------------------------------------------------------------
# supervisor
# ---------------------------------------------------------------------------


def test_supervisor_continues_on_success():
    state = new_state("r1", "Topic")
    state["attempts"] = {"voiceover": 1}
    state["node_history"] = [
        {"node": "voiceover", "status": NodeStatus.SUCCESS, "attempt": 1}
    ]
    out = supervise(state, last_node="voiceover")
    assert out["supervisor_decision"] == SupervisorDecision.CONTINUE
    assert out.get("aborted") is False


def test_supervisor_retries_within_budget():
    state = new_state("r1", "Topic")
    state["attempts"] = {"voiceover": 1}
    state["node_history"] = [
        {"node": "voiceover", "status": NodeStatus.FAILED, "attempt": 1, "error": "boom"}
    ]
    out = supervise(state, last_node="voiceover")
    assert out["supervisor_decision"] == SupervisorDecision.RETRY


def test_supervisor_falls_back_on_node_cap():
    state = new_state("r1", "Topic")
    state["attempts"] = {"video_assembly": 4}  # at the per-node cap
    state["node_history"] = [
        {"node": "video_assembly", "status": NodeStatus.FAILED, "attempt": 4, "error": "boom"}
    ]
    out = supervise(state, last_node="video_assembly")
    assert out["supervisor_decision"] == SupervisorDecision.FALLBACK


def test_supervisor_aborts_on_global_circuit_breaker():
    state = new_state("r1", "Topic")
    # Total retries: sum(max(v-1, 0)) = 14 > MAX_TOTAL_RETRIES (12).
    state["attempts"] = {"voiceover": 8, "video_assembly": 7}
    state["node_history"] = [
        {"node": "voiceover", "status": NodeStatus.FAILED, "attempt": 8, "error": "boom"}
    ]
    out = supervise(state, last_node="voiceover")
    assert out["supervisor_decision"] == SupervisorDecision.ABORT
    assert out["aborted"] is True


# ---------------------------------------------------------------------------
# graph end-to-end
# ---------------------------------------------------------------------------


def test_pipeline_runs_all_nodes_in_dry_run():
    final = run_pipeline(
        video_topic="Roth IRA vs Traditional IRA",
        niche="personal_finance",
        dry_run=True,
    )
    executed = [h["node"] for h in final.get("node_history") or []]
    assert executed == ["ingest", "script", "voiceover", "video_assembly", "publish"]
    assert final["audio_url"].startswith("https://example.invalid/dry-run/")
    assert final["shotstack_render_id"].startswith("dryrun-")
    assert final.get("aborted") is False
    assert final["shotstack_payload"]["output"]["aspectRatio"] == "9:16"


def test_build_graph_returns_invokable_object():
    g = build_graph(dry_run=True)
    assert hasattr(g, "invoke")
