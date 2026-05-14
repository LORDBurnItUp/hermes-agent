"""SwarmState — the TypedDict shared across all LangGraph nodes.

State flows through nodes in the order:
    ingest -> script -> voiceover -> video_assembly -> publish

The Supervisor inspects ``node_history`` after each node to decide whether
to retry (with exponential backoff), skip to a fallback path, or abort.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional, TypedDict


class NodeStatus(str, Enum):
    """Lifecycle states for a single node execution."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    RETRYING = "retrying"
    SKIPPED = "skipped"


class SupervisorDecision(str, Enum):
    """What the auto-healing supervisor decided to do after a node ran."""

    CONTINUE = "continue"
    RETRY = "retry"
    FALLBACK = "fallback"
    ABORT = "abort"


class NodeExecution(TypedDict, total=False):
    """Telemetry for a single node run — emitted to the Live View."""

    node: str
    status: NodeStatus
    started_at: float
    finished_at: float
    attempt: int
    error: Optional[str]
    detail: Optional[Dict[str, Any]]


class SwarmState(TypedDict, total=False):
    """Canonical state passed between LangGraph nodes.

    All fields are optional so a node can populate the slice it owns
    without having to know about downstream/upstream fields.
    """

    # --- Inputs ---
    run_id: str
    video_topic: str
    niche: str  # e.g. "passive_income", "stock_education"
    script: str  # raw narration text; populated by script node
    caption_overlays: List[str]  # short captions to burn on screen

    # --- Audio (ElevenLabs) ---
    voice_id: str
    audio_url: Optional[str]
    audio_duration_seconds: Optional[float]

    # --- Video (Shotstack) ---
    shotstack_payload: Optional[Dict[str, Any]]
    shotstack_render_id: Optional[str]
    shotstack_status: Optional[str]
    video_url: Optional[str]

    # --- Supervisor / telemetry ---
    node_history: List[NodeExecution]
    attempts: Dict[str, int]  # node_name -> attempt count
    last_error: Optional[str]
    supervisor_decision: Optional[SupervisorDecision]
    aborted: bool


def new_state(run_id: str, video_topic: str, niche: str = "personal_finance") -> SwarmState:
    """Construct a fresh state for one pipeline run."""
    return SwarmState(
        run_id=run_id,
        video_topic=video_topic,
        niche=niche,
        script="",
        caption_overlays=[],
        voice_id="",
        audio_url=None,
        audio_duration_seconds=None,
        shotstack_payload=None,
        shotstack_render_id=None,
        shotstack_status=None,
        video_url=None,
        node_history=[],
        attempts={},
        last_error=None,
        supervisor_decision=None,
        aborted=False,
    )
