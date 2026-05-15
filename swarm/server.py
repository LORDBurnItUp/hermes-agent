"""Swarm OS FastAPI server — Live View SSE bus + demo trigger.

Usage::

    uvicorn swarm.server:app --host 0.0.0.0 --port 8000

Environment variables (all optional for dry-run):
    ANTHROPIC_API_KEY / OPENAI_API_KEY
    ELEVENLABS_API_KEY, ELEVENLABS_AUDIO_PUT_URL
    SWARM_BROLL_PROVIDER, SHOTSTACK_API_KEY
    YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET, YOUTUBE_REFRESH_TOKEN
"""

from __future__ import annotations

import logging
import threading
from typing import Any, Dict

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from swarm.sse import attach_live_view

logger = logging.getLogger(__name__)

app = FastAPI(title="Swarm OS", version="0.7.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5174", "http://127.0.0.1:5174"],
    allow_methods=["*"],
    allow_headers=["*"],
)

attach_live_view(app, mount="/swarm")


@app.get("/healthz")
async def healthz() -> JSONResponse:
    return JSONResponse({"status": "ok"})


@app.post("/swarm/run")
async def trigger_run(body: Dict[str, Any] = {}) -> JSONResponse:
    """Trigger a dry-run pipeline in a background thread."""
    from swarm.graph import build_graph, run_pipeline

    video_topic = body.get("video_topic", "Budgeting for Beginners — 3 Tips That Actually Work")
    niche = body.get("niche", "personal_finance")
    dry_run = body.get("dry_run", True)

    def _run() -> None:
        try:
            graph = build_graph(dry_run=dry_run)
            run_pipeline(video_topic=video_topic, niche=niche, graph=graph, dry_run=dry_run)
        except Exception:
            logger.exception("Pipeline run failed")

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    return JSONResponse({"status": "started", "video_topic": video_topic, "dry_run": dry_run})
