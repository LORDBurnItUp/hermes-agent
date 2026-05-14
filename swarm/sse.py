"""Live View — Server-Sent Events dashboard endpoint.

Mount this on your FastAPI app and the operator can stream every node
start/success/error and supervisor decision in real time. The default
client lives in ``swarm/live_view.html`` (a single-file dashboard).

Usage::

    from fastapi import FastAPI
    from swarm.sse import attach_live_view

    app = FastAPI()
    attach_live_view(app, mount="/swarm")

Then ``GET /swarm/events`` is the SSE stream and ``GET /swarm/`` is the
dashboard UI.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

from swarm import events

logger = logging.getLogger(__name__)

LIVE_VIEW_HTML = Path(__file__).parent / "live_view.html"


def attach_live_view(app: Any, *, mount: str = "/swarm") -> None:
    """Wire the Live View endpoints onto an existing FastAPI ``app``."""
    try:
        from fastapi import Request
        from fastapi.responses import HTMLResponse, StreamingResponse
    except ImportError as exc:  # pragma: no cover - dependency surface
        raise RuntimeError("FastAPI required for Live View; pip install fastapi") from exc

    @app.on_event("startup")
    async def _bind() -> None:
        events.bind_loop(asyncio.get_running_loop())
        logger.info("Live View bus bound to event loop.")

    @app.get(f"{mount}/", response_class=HTMLResponse)
    async def dashboard() -> HTMLResponse:
        if LIVE_VIEW_HTML.exists():
            return HTMLResponse(LIVE_VIEW_HTML.read_text(encoding="utf-8"))
        return HTMLResponse(
            "<h1>Swarm OS Live View</h1>"
            f"<p>Connect an SSE client to <code>{mount}/events</code>.</p>"
        )

    @app.get(f"{mount}/events")
    async def event_stream(request: Request) -> StreamingResponse:
        q = events.subscribe()

        async def gen():
            # Replay a synthetic heartbeat so the client knows the stream is alive.
            yield events.serialize({"type": "stream.hello"})
            try:
                while True:
                    if await request.is_disconnected():
                        return
                    try:
                        event = await asyncio.wait_for(q.get(), timeout=15.0)
                    except asyncio.TimeoutError:
                        # SSE heartbeat — keeps proxies from idling out.
                        yield ": keep-alive\n\n"
                        continue
                    yield events.serialize(event)
            finally:
                events.unsubscribe(q)

        return StreamingResponse(
            gen(),
            media_type="text/event-stream",
            headers={
                "cache-control": "no-cache",
                "x-accel-buffering": "no",  # disable nginx buffering
                "connection": "keep-alive",
            },
        )
