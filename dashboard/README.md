# Swarm OS — Live View Dashboard

A Vite + React + TypeScript dashboard that subscribes to the
FastAPI SSE stream exposed by `swarm.sse.attach_live_view()` and
renders, in real time:

- **Active agent status** — one card per run showing which node is
  running, attempt count, and which nodes have completed / failed.
- **Token throughput & cost** — live aggregation of every `node.tokens`
  and `node.cost` event the agents publish, broken down per run and
  totaled in the header.
- **Supervisor log** — every `supervisor.decision` event (retry,
  fallback, abort) with backoff timing and the originating error.

## Performance notes

The SSE consumer batches inbound events into a `useRef` buffer and
flushes via `requestAnimationFrame`. React only re-renders at the
browser's natural paint cadence, so a 50+ events/sec burst from the
swarm never freezes the UI. See `src/hooks/useSwarmStream.ts`.

## Connection hygiene

The hook owns its own reconnect loop instead of relying on the
browser's opaque EventSource retry. On `onerror` we close the socket,
update connection state, and reopen with exponential backoff
(1s → 2s → 4s → … → 30s cap). The dashboard header shows the current
state and the next-retry countdown so the operator can see drops.

## Develop

```bash
cd dashboard
npm install
cp .env.example .env       # or set VITE_SSE_URL inline
npm run dev                # serves on http://127.0.0.1:5174
```

By default the dev server proxies `/swarm/*` to `http://127.0.0.1:8000`,
which assumes FastAPI is running locally with
`swarm.sse.attach_live_view(app, mount="/swarm")`.

## Build & serve from FastAPI

```bash
cd dashboard
npm run build
```

`dist/` is a static SPA. Serve it from FastAPI (`StaticFiles`) under
the same origin as `/swarm/events` to avoid CORS entirely.

## Test

```bash
npm test
```

Covers SSE buffering & batched dispatch, supervisor-event handling,
exponential-backoff reconnect, and malformed-payload tolerance.
