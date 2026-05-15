"""LangGraph StateGraph wiring for the Swarm OS pipeline.

Nodes:
    ingest_node         -- normalises inputs and seeds telemetry
    script_node         -- (stub) populates state['script']; replace with LLM call
    voiceover_node      -- ElevenLabs synth → audio_url
    video_assembly_node -- Shotstack JSON build + render submit
    publish_node        -- (stub) hand-off to YouTube uploader

Edges always pass through ``supervisor_router`` which inspects
``state['supervisor_decision']`` and routes RETRY back to the same node,
FALLBACK to the next-best alternative, ABORT to END, and CONTINUE to the
next stage in the pipeline.

LangGraph is imported lazily: if it's not installed (e.g. the demo
runner just wants to print a Shotstack payload) we expose a minimal
``ManualGraph`` fallback so the same node functions still execute.
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any, Callable, Dict, Optional

from swarm import events, pricing
from swarm.audio_agent import AudioGenerationError, generate_voiceover
from swarm.broll_agent import BRollGenerationError, generate_broll
from swarm.publish_agent import PublishError, publish_to_youtube
from swarm.script_agent import ScriptGenerationError, generate_script
from swarm.state import (
    NodeExecution,
    NodeStatus,
    SupervisorDecision,
    SwarmState,
    new_state,
)
from swarm.supervisor import supervise
from swarm.video_assembly import (
    VideoAssemblyError,
    build_shotstack_payload,
    poll_render_until_done,
    submit_render,
)

logger = logging.getLogger(__name__)

# Re-export for convenience from swarm.__init__.
END = "__end__"


# ---------------------------------------------------------------------------
# Node implementations
# ---------------------------------------------------------------------------


def ingest_node(state: SwarmState) -> SwarmState:
    """Validate inputs, attach a run id, emit a 'run.start' event."""
    with _track(state, "ingest"):
        if not state.get("run_id"):
            state["run_id"] = f"run-{uuid.uuid4().hex[:12]}"
        if not state.get("video_topic"):
            raise ValueError("video_topic is required.")
        state.setdefault("niche", "personal_finance")
        state.setdefault("caption_overlays", [])
        events.publish(
            {
                "type": "run.start",
                "run_id": state["run_id"],
                "topic": state["video_topic"],
                "niche": state["niche"],
            }
        )
    return state


def script_node(state: SwarmState, *, dry_run: bool = False) -> SwarmState:
    """LLM-backed scripting agent.

    Calls Anthropic / OpenAI (per ``SWARM_SCRIPT_PROVIDER``) and stores
    every downstream field in state:
        video_title, script_caption, script, caption_overlays,
        visual_prompt, video_description, video_tags
    Invalid JSON or empty fields raise ``ScriptGenerationError``, which
    propagates to the supervisor for retry with backoff.
    """
    with _track(state, "script"):
        bundle = generate_script(
            video_topic=state["video_topic"],
            niche=state.get("niche") or "personal_finance",
            duration_seconds=30.0,
            dry_run=dry_run,
            run_id=state.get("run_id"),
        )
        state["video_title"] = bundle.video_title
        state["script_caption"] = bundle.script_caption
        state["script"] = bundle.script
        state["caption_overlays"] = bundle.caption_overlays or [bundle.script_caption]
        state["visual_prompt"] = bundle.visual_prompt
        state["video_description"] = bundle.video_description
        state["video_tags"] = bundle.video_tags
    return state


def voiceover_node(state: SwarmState, *, dry_run: bool = False) -> SwarmState:
    """Call ElevenLabs (or dry-run) and store the audio URL."""
    with _track(state, "voiceover"):
        result = generate_voiceover(
            state["script"],
            voice_id=state.get("voice_id") or None,
            dry_run=dry_run,
        )
        state["audio_url"] = result.audio_url
        state["audio_duration_seconds"] = result.duration_seconds
        _emit_cost(
            state,
            node="voiceover",
            provider="elevenlabs",
            cost_usd=pricing.estimate_elevenlabs_cost_usd(len(state.get("script") or "")),
            units={"characters": len(state.get("script") or "")},
        )
    return state


def broll_node(state: SwarmState, *, dry_run: bool = False) -> SwarmState:
    """Generative B-roll. Takes ``visual_prompt`` from the script agent and
    asks Sora/Veo for a single MP4. Failure raises ``BRollGenerationError``
    for the supervisor; dry-run yields a stable placeholder URL.
    """
    with _track(state, "broll"):
        prompt = state.get("visual_prompt") or f"Cinematic finance B-roll for {state['video_topic']}"
        result = generate_broll(
            prompt=prompt,
            duration_seconds=30.0,
            dry_run=dry_run,
        )
        state["broll_url"] = result.url
        state["broll_provider"] = result.provider
        _emit_cost(
            state,
            node="broll",
            provider=result.provider,
            cost_usd=pricing.estimate_broll_cost_usd(result.provider, result.duration_seconds or 0),
            units={"seconds": result.duration_seconds or 0},
        )
    return state


def video_assembly_node(state: SwarmState, *, dry_run: bool = False) -> SwarmState:
    """Build the Shotstack JSON edit-decision list and submit the render.

    If ``state['broll_url']`` was populated by the broll_node, it is the
    sole asset in the B-roll track (looped across the timeline by
    Shotstack). Otherwise we fall back to the niche-keyed stock pool.
    """
    with _track(state, "video_assembly"):
        audio_url = state.get("audio_url")
        if not audio_url:
            raise VideoAssemblyError(
                "video_assembly_node requires audio_url from the voiceover node."
            )

        broll_urls: Optional[list] = None
        if state.get("broll_url"):
            broll_urls = [state["broll_url"]]

        payload = build_shotstack_payload(
            video_title=state.get("video_title") or state["video_topic"],
            script_caption=state.get("script_caption")
            or (state.get("caption_overlays") or [state["video_topic"]])[0],
            audio_url=audio_url,
            niche=state.get("niche") or "personal_finance",
            overlay_lines=state.get("caption_overlays") or None,
            broll_urls=broll_urls,
        )
        state["shotstack_payload"] = payload

        rendering = submit_render(payload, dry_run=dry_run)
        state["shotstack_render_id"] = rendering.render_id
        state["shotstack_status"] = rendering.status
        _emit_cost(
            state,
            node="video_assembly",
            provider="shotstack",
            cost_usd=pricing.estimate_shotstack_cost_usd(30.0),
            units={"output_seconds": 30.0},
        )
    return state


def publish_node(state: SwarmState, *, dry_run: bool = False) -> SwarmState:
    """Poll Shotstack until done, download MP4, upload to YouTube."""
    with _track(state, "publish"):
        render_id = state.get("shotstack_render_id")
        if not render_id:
            raise PublishError("publish_node requires a shotstack_render_id.")

        video_url = poll_render_until_done(render_id, dry_run=dry_run)
        state["video_url"] = video_url

        publish = publish_to_youtube(
            video_url=video_url,
            title=state.get("video_title") or state["video_topic"],
            description=state.get("video_description")
            or f"{state['video_topic']} — Educational content only.",
            tags=state.get("video_tags") or ["personal finance", "shorts"],
            dry_run=dry_run,
        )
        state["published_video_id"] = publish.video_id
        state["published_url"] = publish.url
        state["published_privacy"] = publish.privacy
        events.publish(
            {
                "type": "publish.complete",
                "run_id": state.get("run_id"),
                "video_id": publish.video_id,
                "url": publish.url,
                "privacy": publish.privacy,
            }
        )
        _record_published(state)
    return state


def _record_published(state: SwarmState) -> None:
    """Append a row to the published log so analytics_agent has a manifest.

    Skips dry-run uploads (their video_id starts with 'dryrun-yt-') so
    we don't pollute the real history. Errors are swallowed — losing a
    log row should never abort a successful publish.
    """
    from swarm.published_log import append_published

    video_id = state.get("published_video_id") or ""
    if not video_id or video_id.startswith("dryrun-yt-"):
        return
    try:
        append_published(
            video_id=video_id,
            run_id=state.get("run_id") or "",
            topic=state.get("video_topic") or "",
            title=state.get("video_title") or "",
            niche=state.get("niche") or "",
            tags=state.get("video_tags") or [],
            url=state.get("published_url") or "",
        )
    except Exception as exc:  # pragma: no cover - non-fatal
        logger.warning("published_log write failed: %s", exc)


# ---------------------------------------------------------------------------
# Supervisor + routing
# ---------------------------------------------------------------------------


def _emit_cost(state: SwarmState, *, node: str, provider: str, cost_usd: float, units: Dict[str, Any]) -> None:
    """Emit a node.cost event to the Live View bus."""
    if cost_usd <= 0 and not units:
        return
    events.publish(
        {
            "type": "node.cost",
            "run_id": state.get("run_id"),
            "node": node,
            "provider": provider,
            "cost_usd": round(float(cost_usd), 6),
            "units": units,
        }
    )


def _supervise(node: str) -> Callable[[SwarmState], SwarmState]:
    def _fn(state: SwarmState) -> SwarmState:
        return supervise(state, last_node=node)
    return _fn


def _route(next_node: str) -> Callable[[SwarmState], str]:
    """Map a SupervisorDecision into the next graph node name."""

    def _fn(state: SwarmState) -> str:
        decision = state.get("supervisor_decision", SupervisorDecision.CONTINUE)
        if decision == SupervisorDecision.CONTINUE:
            return next_node
        if decision == SupervisorDecision.RETRY:
            # LangGraph re-enters the most recent worker node.
            return state["__retry_target"]
        if decision == SupervisorDecision.FALLBACK:
            # In Phase 2 the only fallback is to skip the failed stage
            # and continue; the unhealthy state propagates so downstream
            # nodes can no-op gracefully.
            return next_node
        return END

    return _fn


# ---------------------------------------------------------------------------
# Graph builder
# ---------------------------------------------------------------------------


def _try_import_langgraph():
    try:
        from langgraph.graph import StateGraph, END as LG_END  # type: ignore
        return StateGraph, LG_END
    except Exception:  # pragma: no cover - environmental
        return None, None


def build_graph(*, dry_run: bool = False):
    """Compile the StateGraph. Falls back to ManualGraph if langgraph absent."""
    StateGraph, LG_END = _try_import_langgraph()
    if StateGraph is None:
        logger.info("langgraph not installed; using ManualGraph fallback.")
        return ManualGraph(dry_run=dry_run)

    g = StateGraph(SwarmState)

    g.add_node("ingest", ingest_node)
    g.add_node("script", lambda s: script_node(s, dry_run=dry_run))
    g.add_node("voiceover", lambda s: voiceover_node(s, dry_run=dry_run))
    g.add_node("broll", lambda s: broll_node(s, dry_run=dry_run))
    g.add_node("video_assembly", lambda s: video_assembly_node(s, dry_run=dry_run))
    g.add_node("publish", lambda s: publish_node(s, dry_run=dry_run))

    g.add_node("sup_ingest", _supervise("ingest"))
    g.add_node("sup_script", _supervise("script"))
    g.add_node("sup_voiceover", _supervise("voiceover"))
    g.add_node("sup_broll", _supervise("broll"))
    g.add_node("sup_video_assembly", _supervise("video_assembly"))
    g.add_node("sup_publish", _supervise("publish"))

    g.set_entry_point("ingest")
    g.add_edge("ingest", "sup_ingest")
    g.add_conditional_edges(
        "sup_ingest",
        _route("script"),
        {"script": "script", END: LG_END, "ingest": "ingest"},
    )

    g.add_edge("script", "sup_script")
    g.add_conditional_edges(
        "sup_script",
        _route("voiceover"),
        {"voiceover": "voiceover", END: LG_END, "script": "script"},
    )

    g.add_edge("voiceover", "sup_voiceover")
    g.add_conditional_edges(
        "sup_voiceover",
        _route("broll"),
        {"broll": "broll", END: LG_END, "voiceover": "voiceover"},
    )

    g.add_edge("broll", "sup_broll")
    g.add_conditional_edges(
        "sup_broll",
        _route("video_assembly"),
        {"video_assembly": "video_assembly", END: LG_END, "broll": "broll"},
    )

    g.add_edge("video_assembly", "sup_video_assembly")
    g.add_conditional_edges(
        "sup_video_assembly",
        _route("publish"),
        {"publish": "publish", END: LG_END, "video_assembly": "video_assembly"},
    )

    g.add_edge("publish", "sup_publish")
    g.add_conditional_edges(
        "sup_publish",
        _route(LG_END),
        {LG_END: LG_END, "publish": "publish"},
    )

    return g.compile()


# ---------------------------------------------------------------------------
# Manual fallback graph (no langgraph installed)
# ---------------------------------------------------------------------------


class ManualGraph:
    """Minimal stand-in for a compiled LangGraph used when langgraph is absent.

    Runs nodes in the canonical order, consulting the supervisor between
    each step. Honors RETRY / FALLBACK / ABORT just like the real graph.
    """

    NODES: list[tuple[str, Callable[[SwarmState], SwarmState]]]

    def __init__(self, *, dry_run: bool = False) -> None:
        self.dry_run = dry_run
        self.NODES = [
            ("ingest", ingest_node),
            ("script", lambda s: script_node(s, dry_run=dry_run)),
            ("voiceover", lambda s: voiceover_node(s, dry_run=dry_run)),
            ("broll", lambda s: broll_node(s, dry_run=dry_run)),
            ("video_assembly", lambda s: video_assembly_node(s, dry_run=dry_run)),
            ("publish", lambda s: publish_node(s, dry_run=dry_run)),
        ]

    def invoke(self, state: SwarmState) -> SwarmState:
        idx = 0
        while idx < len(self.NODES):
            name, fn = self.NODES[idx]
            try:
                state = fn(state)
            except Exception as exc:
                _record_failure(state, name, exc)

            state = supervise(state, last_node=name)
            decision = state.get("supervisor_decision", SupervisorDecision.CONTINUE)

            if decision == SupervisorDecision.RETRY:
                continue  # re-run same node
            if decision == SupervisorDecision.ABORT:
                events.publish(
                    {
                        "type": "run.aborted",
                        "run_id": state.get("run_id"),
                        "failed_node": name,
                        "error": state.get("last_error"),
                    }
                )
                return state
            if decision in (SupervisorDecision.CONTINUE, SupervisorDecision.FALLBACK):
                idx += 1
                continue

        events.publish({"type": "run.complete", "run_id": state.get("run_id")})
        return state


# ---------------------------------------------------------------------------
# Convenience runner
# ---------------------------------------------------------------------------


def run_pipeline(
    video_topic: str,
    *,
    niche: str = "personal_finance",
    voice_id: Optional[str] = None,
    script_caption: str = "",
    duration_seconds: float = 30.0,
    dry_run: bool = False,
    graph: Any = None,
) -> SwarmState:
    """Run one video end-to-end. Returns the final state."""
    state = new_state(run_id=f"run-{uuid.uuid4().hex[:12]}", video_topic=video_topic, niche=niche)
    if voice_id:
        state["voice_id"] = voice_id
    if script_caption:
        state["caption_overlays"] = [script_caption]

    g = graph or build_graph(dry_run=dry_run)
    return g.invoke(state)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


class _track:
    """Context manager: records start/finish, increments attempts, emits events."""

    def __init__(self, state: SwarmState, node: str) -> None:
        self.state = state
        self.node = node
        self.started = 0.0

    def __enter__(self) -> "_track":
        self.started = time.time()
        attempts = self.state.setdefault("attempts", {})
        attempts[self.node] = attempts.get(self.node, 0) + 1
        self.state["__retry_target"] = self.node  # used by ManualGraph + langgraph router
        events.publish(
            {
                "type": "node.start",
                "run_id": self.state.get("run_id"),
                "node": self.node,
                "attempt": attempts[self.node],
            }
        )
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        finished = time.time()
        attempt = (self.state.get("attempts") or {}).get(self.node, 1)
        if exc is None:
            entry: NodeExecution = {
                "node": self.node,
                "status": NodeStatus.SUCCESS,
                "started_at": self.started,
                "finished_at": finished,
                "attempt": attempt,
            }
            self.state.setdefault("node_history", []).append(entry)
            events.publish(
                {
                    "type": "node.success",
                    "run_id": self.state.get("run_id"),
                    "node": self.node,
                    "duration_s": round(finished - self.started, 3),
                }
            )
            return False

        # Caught error — record but let the supervisor decide.
        msg = f"{exc.__class__.__name__}: {exc}"
        entry = {
            "node": self.node,
            "status": NodeStatus.FAILED,
            "started_at": self.started,
            "finished_at": finished,
            "attempt": attempt,
            "error": msg,
        }
        self.state.setdefault("node_history", []).append(entry)
        self.state["last_error"] = msg
        events.publish(
            {
                "type": "node.error",
                "run_id": self.state.get("run_id"),
                "node": self.node,
                "error": msg,
            }
        )
        # Suppress the exception in LangGraph mode (the supervisor handles
        # retry); rethrow in ManualGraph mode is handled by the caller via
        # _record_failure when needed. Returning True swallows the exception.
        return True


def _record_failure(state: SwarmState, node: str, exc: BaseException) -> None:
    """Backstop for raw failures in ManualGraph that escape ``_track``."""
    msg = f"{exc.__class__.__name__}: {exc}"
    state.setdefault("node_history", []).append(
        {
            "node": node,
            "status": NodeStatus.FAILED,
            "started_at": time.time(),
            "finished_at": time.time(),
            "attempt": (state.get("attempts") or {}).get(node, 1),
            "error": msg,
        }
    )
    state["last_error"] = msg
