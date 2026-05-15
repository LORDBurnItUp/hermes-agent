# Swarm OS — Technical & Strategic Architecture

> Autonomous YouTube automation for high-RPM niches (personal finance,
> passive income, stock education). LangGraph-orchestrated, cloud-rendered,
> auto-healing, observable.

---

## 1. Context & Strategic Frame

The Swarm OS exists to remove humans from the inner loop of repeatable
video production. The economic premise is simple: in finance-adjacent
niches a single algorithmically-priced ad slot is worth 5–30× a generic
lifestyle slot, but the manual workflow (research → script → record →
edit → thumbnail → upload) is the cost ceiling on output. Replace that
loop with software and the only remaining cost is API spend, which
scales sub-linearly.

Strategic targets:

| Lever                              | Mechanism                             | Expected impact                         |
| ---------------------------------- | ------------------------------------- | --------------------------------------- |
| Eliminate manual timeline editing  | Shotstack JSON edit-decision list     | 20–40+ hours/week of engineer time back |
| Eliminate voice booth labour       | ElevenLabs TTS via REST               | Hours → seconds per video               |
| Eliminate orchestration glue       | LangGraph StateGraph + Supervisor     | Pipelines self-heal; no human babysit   |
| Eliminate ops blind spots          | Live View SSE dashboard               | Real-time visibility into every run     |
| Eliminate brittle local rendering  | Cloud render (no FFmpeg)              | Zero infra to maintain                  |

Non-goals (deliberately): visual novelty, hand-edited cinematic cuts,
brand-style variation per video. The Swarm OS optimises for **throughput
× watch-time × CPM**, not per-video craft.

---

## 2. High-Level Architecture

```
  +--------------+      +--------------+      +-------------------+      +-------------+
  | CSV / Sheets |----->| ingest_node  |----->| script_node (LLM) |----->| voiceover   |
  +--------------+      +--------------+      +-------------------+      | (ElevenLabs)|
                                                                         +------+------+
                                                                                |
                                                                                v
   +------------------+      +-------------------+      +----------------------+
   | publish_node     |<-----| video_assembly    |<-----| broll_node           |
   | (YouTube v3 API) |      | (Shotstack JSON)  |      | (Sora / Veo)         |
   +--------+---------+      +---------+---------+      +----------+-----------+
            ^                          ^                           ^
            |                          |                           |
            +-------- Auto-Healing Supervisor (after every node) --+
                                  |
                                  v
                       +---------------------+
                       | Live View (SSE)     |
                       | /swarm/events       |
                       +---------------------+
```

Every worker node returns control to the **Supervisor**, which inspects
`node_history`, decides `CONTINUE / RETRY / FALLBACK / ABORT`, and
publishes a `supervisor.decision` event to the Live View bus before
LangGraph's conditional edge fires.

Repo layout (`swarm/`):

| File                          | Role                                              |
| ----------------------------- | ------------------------------------------------- |
| `state.py`                    | `SwarmState` TypedDict; node + supervisor enums   |
| `csv_ingest.py`               | Bulk topic ingestion (`TopicRow`)                 |
| `script_agent.py`             | LLM-backed script writer (Anthropic/OpenAI)       |
| `audio_agent.py`              | ElevenLabs TTS via raw `requests`                 |
| `broll_agent.py`              | Generative B-roll (Sora/Veo) + dry-run fallback   |
| `video_assembly.py`           | Shotstack JSON builder + `/render` POST + poll    |
| `publish_agent.py`            | YouTube Data API v3 resumable upload              |
| `supervisor.py`               | Auto-healing retry / fallback / circuit breaker   |
| `graph.py`                    | LangGraph wiring + ManualGraph fallback           |
| `events.py`                   | In-process event bus (sync → asyncio.Queue)       |
| `sse.py` + `live_view.html`   | FastAPI SSE endpoint and dashboard UI             |
| `demo.py`                     | End-to-end runner (prints sample JSON + run)      |

---

## 3. Multi-Agent Framework Choice: LangGraph vs CrewAI

| Dimension                    | LangGraph                                          | CrewAI                                                  | Pick for Swarm OS |
| ---------------------------- | -------------------------------------------------- | ------------------------------------------------------- | ----------------- |
| Topology                     | Explicit directed graph w/ conditional edges       | Role-based crew, manager delegates by description       | LangGraph         |
| State model                  | Typed shared state (TypedDict / Pydantic)          | Implicit task-context passing                           | LangGraph         |
| Cycles & retries             | First-class loops, conditional edges, breakpoints  | Limited; manager has to re-issue tasks                  | LangGraph         |
| Determinism                  | Edges are static; routing is data-driven           | LLM-driven delegation is non-deterministic              | LangGraph         |
| Observability                | Node-level hooks, LangSmith trace, easy SSE bridge | Crew-level logs, less granular                          | LangGraph         |
| Time to first prototype      | Higher (graph wiring)                              | Lower (declare crew + tasks)                            | CrewAI for spikes |
| Long-running, idempotent ops | Strong — checkpointing, resumable runs             | Weaker — re-running whole crew is common                | LangGraph         |
| Best fit                     | **Production pipelines with retries & SLAs**       | Brainstorms, research crews, exploratory agent teams    |                   |

**Decision:** LangGraph is the spine of the Swarm OS. We may still embed
a CrewAI "research crew" inside the `script_node` later (one node, one
crew) when the script generation needs multi-persona ideation (writer +
fact-checker + hook-doctor). The two frameworks compose cleanly because
CrewAI's crew has a single function-call entry point. The principle:
**LangGraph owns the assembly line; CrewAI is a station on the line.**

---

## 4. The Programmatic Media Supply Chain (Phase 2)

### 4.1 Audio — `swarm/audio_agent.py`

- Pure `requests` POST to `https://api.elevenlabs.io/v1/text-to-speech/{voice_id}`.
- Returns raw MP3 bytes, which are uploaded via a caller-supplied
  `uploader(bytes, filename) -> url` or a pre-signed S3 PUT URL
  (`ELEVENLABS_AUDIO_PUT_URL`).
- `dry_run=True` short-circuits to a deterministic stub URL so demos and
  unit tests don't burn credits.
- Failure surfaces as `AudioGenerationError`, caught by the supervisor.

### 4.2 Video — `swarm/video_assembly.py`

- `build_shotstack_payload(...)` constructs the edit-decision list as a
  plain `dict`:
  - **Soundtrack track** with the ElevenLabs URL.
  - **B-roll track** distributed evenly across the duration; B-roll
    pool is niche-keyed (`personal_finance`, `passive_income`,
    `stock_education`).
  - **Title-card clip** (4s) with merge field `{{VIDEO_TITLE}}`.
  - **Rolling caption track** with HTML clips, one per overlay line,
    each carrying a `merge` substitution for `{{SCRIPT_CAPTION}}`.
- Output defaults to 9:16 HD MP4 at 30 fps (YouTube Shorts profile).
- `submit_render(payload)` POSTs to Shotstack's stage `/render` endpoint
  and returns a `render_id` — *no FFmpeg, no local encoding*.
- `poll_render(render_id)` is a single GET; the supervisor decides
  cadence (it's not a tight loop).

### 4.3 Data ingestion — `swarm/csv_ingest.py`

- `ingest_topics_from_csv(path) -> list[TopicRow]`
- Columns: `video_topic` (required), `script_caption`, `niche`,
  `voice_id`, `duration_seconds`. Extra columns preserved in `extras`.
- Comment lines (`#…`) skipped; encoding defaults to `utf-8-sig` so
  Excel exports work unmodified.
- `iter_topic_payloads(rows)` adapts directly to `run_pipeline(**kwargs)`,
  so a 500-row spreadsheet becomes 500 LangGraph runs with one for-loop.

### 4.4 LangGraph wiring — `swarm/graph.py`

- `SwarmState` flows through `ingest → script → voiceover →
  video_assembly → publish`.
- Each worker node is followed by a `sup_<node>` supervisor node and a
  `add_conditional_edges` block that maps the supervisor's decision to
  one of `{next_node, same_node, __end__}`.
- If `langgraph` isn't installed (e.g. lightweight CI image), `build_graph()`
  returns a `ManualGraph` that executes the same nodes in order using
  the same supervisor. This keeps `swarm.demo` runnable on a bare
  Python install.

---

## 5. Auto-Healing Supervisor Logic

The supervisor is a pure function over `SwarmState`. It runs between
every pair of nodes and produces one of four decisions:

| Decision  | When                                                 | What LangGraph does                       |
| --------- | ---------------------------------------------------- | ----------------------------------------- |
| CONTINUE  | Last node `SUCCESS`                                  | Route to the next stage                   |
| RETRY     | Last node `FAILED` & under per-node attempt cap      | Re-enter the same node after backoff      |
| FALLBACK  | Per-node cap hit on a node with an alternate path    | Skip to next stage (state flags partial)  |
| ABORT     | Total retries ≥ `MAX_TOTAL_RETRIES` or fatal node    | Route to `END`, emit `run.aborted` event  |

### 5.1 Retry budget

```python
NODE_MAX_ATTEMPTS = {
    "ingest": 1,
    "script": 3,
    "voiceover": 3,
    "video_assembly": 4,
    "publish": 3,
}
MAX_TOTAL_RETRIES = 12  # global circuit breaker
```

- Backoff: `2^(attempt-1)` seconds capped at 30, with full jitter — the
  AWS "Exponential Backoff and Jitter" formula, prevents thundering-herd
  on shared upstream APIs (Shotstack, ElevenLabs).
- The **circuit breaker** is a hard ceiling on cumulative retries across
  a run. It exists to protect the API budget: a misconfigured payload
  that 4xx's forever can otherwise burn the entire monthly quota in
  minutes.

### 5.2 Fallback semantics

`FALLBACK` is reserved for nodes where degraded completion is better
than nothing:

- **voiceover fallback**: skip premium ElevenLabs voice → fall through;
  Phase 3 will plug in Edge TTS (free) as the fallback.
- **video_assembly fallback**: skip render; Phase 3 will queue the
  payload to a delayed retry job so a Shotstack outage doesn't lose the
  script.

Every other failure escalates to `ABORT`.

### 5.3 Idempotency

Each node carries an idempotency contract:

- `script_node` is keyed by `(video_topic, niche)` and is safe to repeat.
- `voiceover_node` writes to a content-hashed S3 key — repeats overwrite.
- `video_assembly_node`'s Shotstack call is idempotent per `run_id` +
  payload hash (the Supervisor stores the last successful `render_id`
  so a retry will reuse rather than re-pay).

### 5.4 Observability surface

Every supervisor decision emits a `supervisor.decision` event
(`run_id`, `node`, `decision`, `attempt`, `delay_s`, `error`). Combined
with the `node.start / node.success / node.error` events emitted by the
worker nodes themselves, the Live View has a complete state machine
trace per run.

---

## 6. Live View — Real-Time Dashboard

### 6.1 Functional requirements

- **One concurrent operator, dozens of concurrent runs.** The dashboard
  must summarise the fleet at a glance and let the operator drill into
  a single run.
- **Latency:** events visible in the UI within ~250 ms of node entry.
- **No polling.** The page opens an `EventSource` to `/swarm/events`
  and renders updates as they arrive.
- **Resilient to disconnects.** Reconnects automatically and replays
  via the SSE `Last-Event-ID` header (Phase 3 — current build replays
  only since-connect).

### 6.2 Non-functional requirements

| Requirement       | Implementation                                                         |
| ----------------- | ---------------------------------------------------------------------- |
| Single-process    | In-memory `asyncio.Queue` per subscriber                               |
| Multi-process     | Swap `events._subscribers` for Redis pub/sub or NATS subject — no node-side change |
| Backpressure      | Per-subscriber `maxsize=1024` queue; drops with WARN log on overflow   |
| Proxy compatibility | `cache-control: no-cache`, `x-accel-buffering: no`, 15-s keep-alive comment |
| Auth              | Mount under FastAPI auth dependency (Phase 3)                          |

### 6.3 Event schema

```
{ "type": "run.start",            "run_id": "...", "topic": "...", "niche": "..." }
{ "type": "node.start",           "run_id": "...", "node": "...", "attempt": 1 }
{ "type": "node.success",         "run_id": "...", "node": "...", "duration_s": 1.23 }
{ "type": "node.error",           "run_id": "...", "node": "...", "error": "..." }
{ "type": "supervisor.decision",  "run_id": "...", "node": "...", "decision": "retry|continue|fallback|abort", "attempt": 2, "delay_s": 1.7 }
{ "type": "run.complete",         "run_id": "..." }
{ "type": "run.aborted",          "run_id": "...", "failed_node": "...", "error": "..." }
```

The browser client in `swarm/live_view.html` colours runs by state
(blue = active, green = done, red = aborted) and tags events by type.

### 6.4 Mounting

```python
from fastapi import FastAPI
from swarm.sse import attach_live_view

app = FastAPI()
attach_live_view(app, mount="/swarm")
# Dashboard: GET /swarm/    Stream: GET /swarm/events
```

---

## 7. YouTube Automation Workflow

End-to-end, per video, the system performs:

1. **Topic ingestion** — pop a `TopicRow` from a CSV, Google Sheet sync,
   or a niche-tuned trend miner.
2. **Script generation** — LLM call (deferred from Phase 2 stub) keyed
   by `niche`. Prompt template is held in `prompts/` and version
   controlled; output is constrained to ~150 wpm × duration.
3. **Voiceover synthesis** — ElevenLabs `eleven_turbo_v2_5` for cost,
   `eleven_multilingual_v2` for higher-quality flagship videos. Voice
   id is per-channel (consistent host = retention).
4. **Visual assembly** — Shotstack JSON. Phase 2 ships static B-roll
   pools per niche; Phase 3 will integrate Pexels/Pixabay search keyed
   by script entities.
5. **Render** — Shotstack cloud renders MP4 in 9:16. Average finance
   short renders in 30–90s.
6. **Publish** — `publish_node` (Phase 3) hands the MP4 URL to the
   YouTube Data API v3 `videos.insert` upload, with niche-tuned title,
   description (incl. affiliate links), tags, and thumbnail.
7. **Telemetry loop** — YouTube Analytics polled hourly; per-video
   performance writes back to the topic row for the script node's
   future prompt context.

This is the **assembly line**. Throughput is bounded by the slowest
external API (Shotstack rendering, typically). A single operator can
run multiple parallel pipelines limited only by Shotstack/ElevenLabs
rate caps and YouTube's upload quota (Phase 4 introduces multi-channel
sharding to lift the upload ceiling).

---

## 8. Phasing & Roadmap

| Phase | Scope                                                                           | Status     |
| ----- | ------------------------------------------------------------------------------- | ---------- |
| 1     | LangGraph backend scaffold, SSE bus, event schema, repo skeleton                | Done (Phase 2 PR) |
| 2     | Shotstack + ElevenLabs + video_assembly_node + CSV ingestion + Live View HTML   | Done       |
| 3     | LLM `script_node`, generative B-roll, YouTube `publish_node`                    | Done       |
| **4** | **React Live View dashboard + analytics & feedback agent (CSV self-loop)**      | **This PR** |
| 5     | Edge-TTS voiceover fallback, deferred-render queue, multi-channel sharding      | Next       |
| 6     | Multi-niche tenancy, per-tenant quotas, billing                                 | Later      |

---

## 11. Phase 3: Intelligence & Distribution

### 11.1 `script_node` — `swarm/script_agent.py`

LLM-backed scriptwriter. Defaults to **Anthropic Claude** (project
already depends on `anthropic`); flip `SWARM_SCRIPT_PROVIDER=openai` to
route through OpenAI's `chat.completions` with `response_format=
json_object`. Both providers return the same `ScriptBundle`:

```
video_title       -> {{VIDEO_TITLE}} merge field + YouTube title
script_caption    -> {{SCRIPT_CAPTION}} hero caption
script            -> full narration handed to ElevenLabs
caption_overlays  -> rolling captions burned on screen
visual_prompt     -> forwarded to broll_node (Sora/Veo)
video_description -> YouTube description (CTA + "not financial advice")
video_tags        -> deduped lowercase YouTube tags
```

Validation: `_parse_bundle` strips `​```json` fences, parses JSON,
enforces every required field is present with the correct type, and
raises `ScriptGenerationError` on any deviation. The supervisor sees
that exception and retries with backoff — same circuit it used for
Shotstack timeouts in Phase 2.

System prompt forbids specific financial advice and forces JSON-only
output. Dry-run mode short-circuits to a deterministic stub so CI and
demos run without credits.

### 11.2 `broll_node` — `swarm/broll_agent.py`

Provider-agnostic generative-video step. Concrete providers:

- **`SoraProvider`** — POST `/v1/videos` (`model=sora-2`, `9:16`,
  duration clamped to 4–60s), poll `GET /v1/videos/{id}` until
  `status="succeeded"`, return `output.url`.
- **`VeoProvider`** — POST `predictLongRunning` on the Vertex AI
  publisher endpoint for `veo-3.1-generate-preview`, poll
  `fetchPredictOperation`, return the first `videos[0].uri`.

`SWARM_BROLL_PROVIDER` (`sora`/`veo`) selects the provider. If unset
**or** `dry_run=True`, `generate_broll` returns a deterministic
placeholder URL (a Shotstack-hosted finance B-roll asset) keyed by a
SHA-1 of the visual prompt — handy for traceability across reruns.

Failures raise `BRollGenerationError`. The supervisor maps the
`broll` node to `FALLBACK`, so a Sora/Veo outage transparently
degrades to the niche stock pool already wired into
`video_assembly_node`.

### 11.3 Injection into Shotstack

When `state['broll_url']` is set, `video_assembly_node` passes it as a
single-element `broll_urls` list to `build_shotstack_payload`. The
helper already supports the override (it distributes any provided URLs
evenly across the timeline), so no schema change in Shotstack land.

### 11.4 `publish_node` — `swarm/publish_agent.py`

Two stages:

1. **Render polling.** `poll_render_until_done(render_id)` polls
   Shotstack every 5s until `response.status == "done"` and returns the
   final MP4 URL (or raises on `failed` / timeout).
2. **YouTube resumable upload.** OAuth exchange via
   `oauth2.googleapis.com/token` using a refresh-token grant
   (`YOUTUBE_CLIENT_ID` / `_SECRET` / `_REFRESH_TOKEN` env vars).
   Streams the rendered MP4 to a temp file, initialises a resumable
   upload session against `/upload/youtube/v3/videos?uploadType=resumable`,
   PUTs the bytes, and returns the new `videoId`.

Privacy defaults to `private`; flip `YOUTUBE_DEFAULT_PRIVACY` or pass
`privacy="unlisted"|"public"` once a channel has been QA'd. The
upload metadata (`title`, `description`, `tags[]`,
`selfDeclaredMadeForKids=false`) all comes from the `script_node`
bundle — no operator touch required.

Failures (rate limit, token expiry, network) raise `PublishError`. The
supervisor treats `publish` as ABORT-on-cap (no fallback path), with
4 retries per run inside the global 16-retry circuit breaker.

### 11.5 Updated supervisor budgets

```python
NODE_MAX_ATTEMPTS = {
    "ingest": 1,
    "script": 3,
    "voiceover": 3,
    "broll": 3,
    "video_assembly": 4,
    "publish": 4,
}
MAX_TOTAL_RETRIES = 16
```

FALLBACK-eligible nodes: `voiceover`, `broll`, `video_assembly`.

### 11.6 Env-var summary (live mode)

```
ANTHROPIC_API_KEY          # script_node (default provider)
OPENAI_API_KEY             # script_node alt provider (set SWARM_SCRIPT_PROVIDER=openai)
ELEVENLABS_API_KEY         # voiceover_node
ELEVENLABS_AUDIO_PUT_URL   # pre-signed S3 PUT for MP3 hosting
SWARM_BROLL_PROVIDER       # "sora" | "veo" | unset (placeholder)
SORA_API_KEY               # or OPENAI_API_KEY for Sora
GOOGLE_API_KEY             # Veo
GOOGLE_CLOUD_PROJECT       # Veo
SHOTSTACK_API_KEY          # video_assembly_node
YOUTUBE_CLIENT_ID          # publish_node
YOUTUBE_CLIENT_SECRET      # publish_node
YOUTUBE_REFRESH_TOKEN      # publish_node (one-time OAuth setup)
YOUTUBE_DEFAULT_PRIVACY    # optional override of "private"
```

---

## 12. Phase 4: Live View dashboard + continuous-optimisation loop

Phase 4 ships two complementary deliverables: a **React dashboard**
that visualises the SSE stream in real time, and an **analytics agent**
that closes the loop between what we publish and what the swarm
publishes next.

### 12.1 React Live View — `dashboard/`

Stack: Vite + React 18 + TypeScript + vitest. Mount point: any
FastAPI app that already calls `swarm.sse.attach_live_view(...)`.

Layout:

```
dashboard/
├── package.json / tsconfig / vite.config.ts
├── src/
│   ├── App.tsx                       composition root
│   ├── hooks/useSwarmStream.ts       SSE consumer + state aggregator
│   ├── components/
│   │   ├── MetricsBar.tsx            top header tiles
│   │   ├── RunGrid.tsx + RunCard.tsx active-run cards
│   │   └── SupervisorLog.tsx         intervention timeline
│   ├── lib/format.ts                 USD / token / time formatters
│   └── styles.css
```

**Why batching with `requestAnimationFrame`.** A naive
`useState` write inside `EventSource.onmessage` would re-render on
every event. The swarm fans out 5–50 events/sec under load, and at
50 events/sec a 16 ms paint budget is exceeded by the React layout
alone. The hook instead pushes events into a `useRef` buffer and
calls `requestAnimationFrame` to flush. The reducer applies the
batch atomically — connection-state, run summaries, intervention
log, and metrics all update in one paint — so the dashboard stays
60 fps even when the swarm goes wide. `cancelAnimationFrame` on
unmount prevents leaked scheduled flushes.

**Auto-reconnect with explicit backoff.** Browser EventSource has
opaque retry semantics: no visibility into attempt count, no
configurable delay. The hook owns the lifecycle: `onerror` closes
the socket, increments `reconnectRef`, computes the next delay
(`min(initialReconnectMs * 2^(attempt-1), 30_000)`), and schedules
a `setTimeout` to reconnect. Connection state surfaces in
`ConnectionState` so the header shows
"reconnecting (attempt 3, retry in 4s)" — operators see drops
instead of guessing.

**What it visualises.**
- *MetricsBar:* events/s rolling 5 s window, active runs,
  completed / aborted count, total cost USD, input / output tokens,
  supervisor R / F / A counters. Goes red when an abort happens.
- *RunCard:* per-run card with node-state ribbon
  (`ingest → script → voice → b-roll → render → publish`), token /
  cost tags, retry / fallback badges, and the published YouTube
  URL once `publish.complete` fires.
- *SupervisorLog:* timeline of every non-`continue` supervisor
  decision with attempt, backoff delay, and originating error.

Tests live in `src/hooks/useSwarmStream.test.ts` and exercise the
buffering, supervisor-event handling, exponential-backoff
reconnect, and malformed-payload tolerance against a fake
EventSource. `npm test` → 4 cases passing; `npm run build`
produces a 49 KB gzipped SPA suitable for serving via FastAPI
`StaticFiles` alongside `/swarm/events`.

### 12.2 Token + cost telemetry

Every paid node now emits structured events the dashboard renders:

- `script_node` → `node.tokens` (`provider`, `model`,
  `input_tokens`, `output_tokens`, `cost_usd`) sourced from the
  Anthropic / OpenAI SDK usage block.
- `voiceover_node` → `node.cost` (`provider=elevenlabs`,
  `units={characters}`, USD via `swarm/pricing.py`).
- `broll_node` → `node.cost` (`provider=sora|veo|placeholder`,
  `units={seconds}`).
- `video_assembly_node` → `node.cost` (`provider=shotstack`,
  `units={output_seconds}`).

`swarm/pricing.py` centralises list-price rate cards
(LLM-per-million-tokens, ElevenLabs $/1k chars, Shotstack
$/output-minute, Sora/Veo $/second). Replace with billed-actuals in
Phase 5 once each provider's billing API is plumbed in.

### 12.3 Analytics & feedback agent — `swarm/analytics_agent.py`

Out-of-band cron job (not a graph node) that closes the loop:

1. **Read** `~/.hermes/swarm/published.jsonl` — every successful
   `publish_node` call appends a row via `swarm.published_log`.
   Dry-run uploads are excluded so the manifest stays clean.
2. **Fetch** YouTube Analytics v2 reports per video for the last N
   days (default 14): `views`, `estimatedMinutesWatched`,
   `averageViewDuration`, `annotationClickThroughRate`, `likes`,
   `comments`. OAuth uses the same refresh-token pattern as
   `publish_agent` — the token must include the
   `yt-analytics.readonly` scope.
3. **Summarise** via Claude / OpenAI. The LLM gets the per-video
   metrics matrix + the topic each video covered, and returns a
   strict-JSON `OptimizationReport`:
   - `winners[]` — top performers with one-line "why".
   - `losers[]` — underperformers with one-line "why".
   - `new_topic_ideas[]` — N new `TopicRow`-shaped objects each
     grounded in a winner signal. Niche is constrained to
     `{personal_finance, passive_income, stock_education}`;
     duration is clamped to 15–60 s.
   - `notes` — 1–2 sentence trend summary.
4. **Append** the new ideas to `swarm/sample_topics.csv` (or any
   path the operator passes). Existing topics are skipped
   case-insensitively, so the cron is idempotent across reruns.
5. **Emit** `analytics.start / fetched / summarised / complete`
   events so the dashboard renders cron progress in real time.

Every network call (OAuth, Analytics fetch, LLM) is wrapped in
`_with_backoff`, the same exp-backoff-with-jitter envelope used by
the main supervisor. Dry-run mode mocks both the API and the LLM
with deterministic stubs (sha1-keyed so values are stable across
processes), enabling offline CI.

CLI: `python -m swarm.cron_analytics --csv swarm/sample_topics.csv
[--published-log ...] [--report-dir ...] [--live]`.

### 12.4 Verification

```
$ python -m pytest tests/test_swarm_analytics.py -q
16 passed
$ npm --prefix dashboard test
4 passed
$ npm --prefix dashboard run build
✓ built in <1s (49 KB gzipped)
$ python -m swarm.cron_analytics --csv /tmp/topics.csv \
    --published-log /tmp/pub.jsonl --report-dir /tmp/reports
analyzed videos      : 3
new topics appended  : 4
```

---

## 9. Verification

The Phase 2 deliverable is verified by:

```bash
python -m swarm.demo            # prints sample Shotstack JSON + runs dry pipeline
python -m swarm.demo --csv swarm/sample_topics.csv
pytest tests/test_swarm.py -q
```

Expected: the demo prints a fully formed Shotstack JSON payload, runs
all five nodes in dry-run, and exits 0 with `nodes executed:
['ingest', 'script', 'voiceover', 'video_assembly', 'publish']`.

---

## 10. Risk Register

| Risk                              | Mitigation                                                       |
| --------------------------------- | ---------------------------------------------------------------- |
| Shotstack rate limit / outage     | Supervisor `FALLBACK`; Phase 3 queue for deferred re-render      |
| ElevenLabs voice drift            | Pin `model_id` + `voice_settings` per channel; snapshot in state |
| Runaway retry burns budget        | Per-node caps + `MAX_TOTAL_RETRIES` circuit breaker              |
| LLM hallucinates harmful finance advice | Fact-check sub-crew in `script_node` (Phase 3 CrewAI insert) |
| YouTube ToS — automation policy   | Per-channel daily caps; manual sample audits; honest disclosure  |
| Stock B-roll licensing            | Stick to whitelisted CC0/owned pools; track provenance in state  |
