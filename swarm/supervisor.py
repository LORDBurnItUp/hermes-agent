"""Auto-Healing Supervisor.

After every worker node, control passes through ``supervise`` which:

    1. Reads ``node_history`` for the just-completed node.
    2. Increments the per-node attempt counter.
    3. Decides:
          - CONTINUE  → success, move to the next node
          - RETRY     → transient failure, route back with backoff
          - FALLBACK  → permanent failure on this path, take alt route
          - ABORT     → kill the run, surface the error

    4. Emits a Live View event describing the decision.

Retry policy is exponential backoff with a jitter envelope. Per-node caps
prevent infinite loops; the global ``MAX_TOTAL_RETRIES`` protects the
account budget from a runaway pipeline.
"""

from __future__ import annotations

import logging
import random
import time
from typing import Dict

from swarm import events
from swarm.state import NodeStatus, SupervisorDecision, SwarmState

logger = logging.getLogger(__name__)

# Per-node retry caps. Nodes that touch a paid API get tighter budgets.
NODE_MAX_ATTEMPTS: Dict[str, int] = {
    "ingest": 1,
    "script": 3,
    "voiceover": 3,
    "video_assembly": 4,
    "publish": 3,
}
DEFAULT_MAX_ATTEMPTS = 2
MAX_TOTAL_RETRIES = 12  # circuit breaker: sum across all nodes


def supervise(state: SwarmState, *, last_node: str) -> SwarmState:
    """Examine the last node's outcome and decide what happens next.

    Mutates and returns ``state`` so LangGraph's conditional edges can
    route on ``state['supervisor_decision']``.
    """
    history = state.get("node_history") or []
    last_entry = next(
        (h for h in reversed(history) if h.get("node") == last_node),
        None,
    )

    if last_entry is None:
        # Shouldn't happen — defensive.
        state["supervisor_decision"] = SupervisorDecision.CONTINUE
        return state

    status = last_entry.get("status")
    attempts = state.get("attempts") or {}
    total_retries = sum(max(v - 1, 0) for v in attempts.values())

    if status == NodeStatus.SUCCESS:
        decision = SupervisorDecision.CONTINUE
        delay = 0.0
    elif total_retries >= MAX_TOTAL_RETRIES:
        decision = SupervisorDecision.ABORT
        delay = 0.0
        logger.error(
            "Supervisor: circuit breaker tripped — %d total retries across run %s",
            total_retries,
            state.get("run_id"),
        )
    elif attempts.get(last_node, 0) >= NODE_MAX_ATTEMPTS.get(last_node, DEFAULT_MAX_ATTEMPTS):
        decision = _fallback_or_abort(last_node)
        delay = 0.0
    else:
        decision = SupervisorDecision.RETRY
        delay = _backoff_seconds(attempts.get(last_node, 1))

    state["supervisor_decision"] = decision
    events.publish(
        {
            "type": "supervisor.decision",
            "run_id": state.get("run_id"),
            "node": last_node,
            "decision": decision.value,
            "attempt": attempts.get(last_node, 0),
            "delay_s": delay,
            "error": last_entry.get("error"),
        }
    )

    if decision == SupervisorDecision.RETRY and delay > 0:
        # The graph runs synchronously; sleeping here is the simplest
        # backoff. For a fully async deployment, replace with a delayed
        # re-enqueue on the task runner.
        time.sleep(delay)

    if decision == SupervisorDecision.ABORT:
        state["aborted"] = True

    return state


def _fallback_or_abort(node: str) -> SupervisorDecision:
    """Nodes with an alternate path return FALLBACK; otherwise ABORT."""
    if node in {"voiceover", "video_assembly"}:
        return SupervisorDecision.FALLBACK
    return SupervisorDecision.ABORT


def _backoff_seconds(attempt: int) -> float:
    """Exponential backoff with full jitter, capped at 30s."""
    base = min(2 ** max(attempt - 1, 0), 30)
    return random.uniform(0, base)
