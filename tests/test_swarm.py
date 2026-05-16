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
    # "script" has no fallback path, so once it hits its per-node cap the
    # supervisor either RETRYs (under budget) or ABORTs. Push total
    # retries past MAX_TOTAL_RETRIES (16) so we land in the ABORT branch.
    state["attempts"] = {"voiceover": 9, "video_assembly": 9}
    state["node_history"] = [
        {"node": "voiceover", "status": NodeStatus.FAILED, "attempt": 9, "error": "boom"}
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
    assert executed == [
        "ingest",
        "script",
        "voiceover",
        "broll",
        "video_assembly",
        "publish",
    ]
    assert final["audio_url"].startswith("https://example.invalid/dry-run/")
    assert final["shotstack_render_id"].startswith("dryrun-")
    assert final.get("aborted") is False
    assert final["shotstack_payload"]["output"]["aspectRatio"] == "9:16"


def test_build_graph_returns_invokable_object():
    g = build_graph(dry_run=True)
    assert hasattr(g, "invoke")


# ---------------------------------------------------------------------------
# Phase 3: script / b-roll / publish
# ---------------------------------------------------------------------------


def test_script_agent_dry_run_returns_complete_bundle():
    from swarm.script_agent import generate_script

    bundle = generate_script(
        video_topic="High-Yield Savings vs Money Market",
        niche="personal_finance",
        dry_run=True,
    )
    assert bundle.video_title
    assert bundle.script
    assert bundle.script_caption
    assert bundle.visual_prompt
    assert bundle.video_description.endswith("not financial advice.")
    assert len(bundle.caption_overlays) >= 3
    assert len(bundle.video_tags) >= 4


def test_script_agent_rejects_invalid_json():
    from swarm.script_agent import _parse_bundle, ScriptGenerationError

    with pytest.raises(ScriptGenerationError):
        _parse_bundle("not json at all")
    with pytest.raises(ScriptGenerationError):
        _parse_bundle('{"video_title": "x"}')  # missing required fields


def test_script_agent_parses_fenced_json():
    from swarm.script_agent import _parse_bundle

    raw = (
        "```json\n"
        "{\"video_title\": \"T\", \"script_caption\": \"C\", \"script\": \"S\","
        " \"caption_overlays\": [\"a\", \"b\"], \"visual_prompt\": \"P\","
        " \"video_description\": \"D\", \"video_tags\": [\"x\"]}\n"
        "```"
    )
    bundle = _parse_bundle(raw)
    assert bundle.video_title == "T"
    assert bundle.caption_overlays == ["a", "b"]


def test_broll_agent_dry_run_returns_placeholder():
    from swarm.broll_agent import generate_broll, PLACEHOLDER_BROLL_URL

    result = generate_broll(prompt="Cinematic finance shot", dry_run=True)
    assert result.url == PLACEHOLDER_BROLL_URL
    assert result.provider == "placeholder"
    assert result.job_id and result.job_id.startswith("dryrun-")


def test_broll_agent_rejects_empty_prompt():
    from swarm.broll_agent import generate_broll, BRollGenerationError

    with pytest.raises(BRollGenerationError):
        generate_broll(prompt="  ", dry_run=True)


def test_video_assembly_uses_state_broll_url():
    """When broll_url is set on state, the video_assembly node injects it."""
    from swarm.graph import video_assembly_node
    from swarm.state import new_state

    state = new_state("r1", "Topic")
    state["audio_url"] = "https://example.invalid/audio.mp3"
    state["video_title"] = "T"
    state["script_caption"] = "C"
    state["broll_url"] = "https://example.com/generated-broll.mp4"
    state["caption_overlays"] = ["a", "b"]

    out = video_assembly_node(state, dry_run=True)
    payload = out["shotstack_payload"]
    # B-roll track is the last one in the build order; check it contains the injected URL.
    broll_track = payload["timeline"]["tracks"][-1]
    sources = [c["asset"]["src"] for c in broll_track["clips"]]
    assert "https://example.com/generated-broll.mp4" in sources


def test_publish_agent_dry_run_returns_shorts_url():
    from swarm.publish_agent import publish_to_youtube

    result = publish_to_youtube(
        video_url="https://example.invalid/render.mp4",
        title="Roth IRA vs Traditional IRA — Quick Guide",
        description="Educational only — not financial advice.",
        tags=["roth ira", "personal finance"],
        dry_run=True,
    )
    assert result.video_id.startswith("dryrun-yt-")
    assert result.url.startswith("https://www.youtube.com/shorts/")
    assert result.privacy == "private"


def test_publish_agent_validates_privacy():
    from swarm.publish_agent import publish_to_youtube, PublishError

    with pytest.raises(PublishError):
        publish_to_youtube(
            video_url="https://x/y.mp4",
            title="T",
            description="D",
            tags=[],
            privacy="oops",
            dry_run=True,
        )


def test_full_phase3_pipeline_populates_publish_fields():
    final = run_pipeline(video_topic="Index Funds 101", dry_run=True)
    assert final.get("video_title")
    assert final.get("visual_prompt")
    assert final.get("broll_url")
    assert final.get("video_url", "").endswith(".mp4")
    assert final.get("published_video_id", "").startswith("dryrun-yt-")
    assert final.get("published_url", "").startswith("https://www.youtube.com/shorts/")
    assert final.get("published_privacy") == "private"
