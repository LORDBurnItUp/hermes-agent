# Swarm OS

Autonomous YouTube automation built on LangGraph, ElevenLabs, and
Shotstack. See [`docs/swarm-os-architecture.md`](../docs/swarm-os-architecture.md)
for the full report.

## Install

```bash
pip install -e ".[swarm]"
# brings in langgraph, fastapi, uvicorn, sse-starlette
```

The package itself (state, supervisor, audio, video, CSV, demo) works
without any extras — the `swarm.graph` module falls back to a
`ManualGraph` runner if `langgraph` isn't installed. The Live View
endpoint requires `fastapi`.

## Run the Phase 2 demo

```bash
python -m swarm.demo                              # built-in finance topic
python -m swarm.demo --csv swarm/sample_topics.csv
python -m swarm.demo --live                       # hits real APIs (needs keys)
```

Required env vars for `--live`:

```
ELEVENLABS_API_KEY=...
ELEVENLABS_AUDIO_PUT_URL=https://<bucket>.s3.amazonaws.com/...?X-Amz-Signature=...
SHOTSTACK_API_KEY=...
```

## Mount the Live View on FastAPI

```python
from fastapi import FastAPI
from swarm.sse import attach_live_view

app = FastAPI()
attach_live_view(app, mount="/swarm")
# Dashboard: GET /swarm/    Stream: GET /swarm/events
```

## Public API

```python
from swarm import (
    SwarmState, NodeStatus, SupervisorDecision,
    TopicRow, ingest_topics_from_csv,
    build_graph, run_pipeline,
)
```
