"""In-process event bus that bridges LangGraph nodes to the Live View SSE.

Nodes call ``publish(event)`` synchronously; the SSE endpoint subscribes
to its own asyncio.Queue and streams JSON events to the dashboard.

This is intentionally minimal — one process, in-memory fan-out, no Redis.
For multi-worker deployments swap ``_subscribers`` for a Redis pub/sub or
NATS subject without touching the node code.
"""

from __future__ import annotations

import asyncio
import json
import logging
import threading
import time
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

_subscribers: "List[asyncio.Queue[Dict[str, Any]]]" = []
_lock = threading.Lock()
_loop: "asyncio.AbstractEventLoop | None" = None


def bind_loop(loop: asyncio.AbstractEventLoop) -> None:
    """Bind the event-loop used by the SSE endpoint.

    Called once at FastAPI startup. Synchronous callers (LangGraph nodes
    running in a worker thread) schedule queue puts on this loop.
    """
    global _loop
    _loop = loop


def subscribe() -> "asyncio.Queue[Dict[str, Any]]":
    """Add a subscriber and return its queue."""
    q: "asyncio.Queue[Dict[str, Any]]" = asyncio.Queue(maxsize=1024)
    with _lock:
        _subscribers.append(q)
    return q


def unsubscribe(q: "asyncio.Queue[Dict[str, Any]]") -> None:
    with _lock:
        if q in _subscribers:
            _subscribers.remove(q)


def publish(event: Dict[str, Any]) -> None:
    """Fan out an event to every live subscriber.

    Safe to call from sync code. Adds ``ts`` if missing. Drops the event
    for a slow subscriber rather than blocking the pipeline.
    """
    event.setdefault("ts", time.time())
    payload = dict(event)

    with _lock:
        targets = list(_subscribers)

    if not targets:
        return

    if _loop is None or not _loop.is_running():
        # No SSE consumer attached yet — drop silently. Useful for tests.
        return

    for q in targets:
        try:
            _loop.call_soon_threadsafe(_put_nowait, q, payload)
        except RuntimeError:
            # loop closed
            pass


def _put_nowait(q: "asyncio.Queue[Dict[str, Any]]", payload: Dict[str, Any]) -> None:
    try:
        q.put_nowait(payload)
    except asyncio.QueueFull:
        logger.warning("Live View subscriber queue full; dropping event %s", payload.get("type"))


def serialize(event: Dict[str, Any]) -> str:
    """Serialize an event as an SSE ``data:`` payload line."""
    return f"data: {json.dumps(event, default=str)}\n\n"
