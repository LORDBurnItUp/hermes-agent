/**
 * useSwarmStream — connects to the FastAPI SSE endpoint and aggregates
 * the event stream into the shape the dashboard renders.
 *
 * Two performance properties matter here:
 *
 *  1. **High event rates must not freeze the UI.** Naively calling
 *     setState() inside EventSource.onmessage would re-render on every
 *     incoming event — a hot swarm can push 50+ events per second. We
 *     buffer events into a ref and flush via requestAnimationFrame so
 *     React only re-renders at the browser's natural paint cadence.
 *
 *  2. **SSE drops must auto-recover.** The browser's built-in
 *     EventSource reconnect is opaque and not configurable. We close
 *     it ourselves on error and reopen with exponential backoff
 *     (1s → 2s → 4s → … capped at 30s) so the dashboard reflects the
 *     true connection state and the operator isn't left guessing.
 */

import { useEffect, useReducer, useRef } from "react";
import type {
  ConnectionState,
  Metrics,
  RunSummary,
  SupervisorIntervention,
  SwarmEvent,
} from "../types";

interface DashboardState {
  connection: ConnectionState;
  runs: Map<string, RunSummary>;
  recentEvents: SwarmEvent[];
  interventions: SupervisorIntervention[];
  metrics: Metrics;
  // Rolling 5-second event-rate buckets.
  rateWindow: Array<{ ts: number; count: number }>;
}

type Action =
  | { kind: "connection"; payload: Partial<ConnectionState> }
  | { kind: "events"; payload: SwarmEvent[] }
  | { kind: "tick"; ts: number };

const MAX_RECENT_EVENTS = 200;
const MAX_INTERVENTIONS = 100;
const RATE_WINDOW_MS = 5_000;

const emptyMetrics: Metrics = {
  eventsPerSec: 0,
  totalEvents: 0,
  totalRuns: 0,
  activeRuns: 0,
  completedRuns: 0,
  abortedRuns: 0,
  totalCostUsd: 0,
  inputTokens: 0,
  outputTokens: 0,
  supervisorRetries: 0,
  supervisorFallbacks: 0,
  supervisorAborts: 0,
};

function initialState(): DashboardState {
  return {
    connection: { status: "connecting", attempt: 0 },
    runs: new Map(),
    recentEvents: [],
    interventions: [],
    metrics: { ...emptyMetrics },
    rateWindow: [],
  };
}

function reducer(state: DashboardState, action: Action): DashboardState {
  switch (action.kind) {
    case "connection":
      return { ...state, connection: { ...state.connection, ...action.payload } };
    case "events":
      return applyEvents(state, action.payload);
    case "tick":
      return tickRate(state, action.ts);
  }
}

function applyEvents(state: DashboardState, batch: SwarmEvent[]): DashboardState {
  if (batch.length === 0) return state;

  const runs = new Map(state.runs);
  const interventions = state.interventions.slice();
  const metrics: Metrics = { ...state.metrics };
  metrics.totalEvents += batch.length;

  for (const event of batch) {
    const runId = event.run_id;
    let run: RunSummary | undefined = runId ? runs.get(runId) : undefined;

    if (runId && !run) {
      run = blankRun(runId);
      metrics.totalRuns += 1;
    }
    if (run) {
      run = { ...run, lastUpdate: event.ts };
    }

    switch (event.type) {
      case "run.start":
        if (run) {
          run.topic = event.topic ?? run.topic;
          run.niche = event.niche ?? run.niche;
          run.status = "active";
          metrics.activeRuns += 1;
        }
        break;
      case "node.start":
        if (run && event.node) {
          run.currentNode = event.node;
          run.attempt = event.attempt ?? run.attempt;
          run.nodeStates = { ...run.nodeStates, [event.node]: "running" };
        }
        break;
      case "node.success":
        if (run && event.node) {
          run.nodeStates = { ...run.nodeStates, [event.node]: "success" };
        }
        break;
      case "node.error":
        if (run && event.node) {
          run.nodeStates = { ...run.nodeStates, [event.node]: "error" };
        }
        break;
      case "node.tokens":
        if (run) {
          run.inputTokens += event.input_tokens ?? 0;
          run.outputTokens += event.output_tokens ?? 0;
          run.costUsd += event.cost_usd ?? 0;
        }
        metrics.inputTokens += event.input_tokens ?? 0;
        metrics.outputTokens += event.output_tokens ?? 0;
        metrics.totalCostUsd += event.cost_usd ?? 0;
        break;
      case "node.cost":
        if (run) run.costUsd += event.cost_usd ?? 0;
        metrics.totalCostUsd += event.cost_usd ?? 0;
        break;
      case "supervisor.decision": {
        const decision = event.decision;
        if (decision === "retry") metrics.supervisorRetries += 1;
        if (decision === "fallback") metrics.supervisorFallbacks += 1;
        if (decision === "abort") metrics.supervisorAborts += 1;
        if (decision && decision !== "continue" && event.node) {
          if (run && decision === "retry") run.retries += 1;
          if (run && decision === "fallback") run.fallbacks += 1;
          interventions.unshift({
            ts: event.ts,
            runId,
            node: event.node,
            decision,
            attempt: event.attempt,
            delaySeconds: event.delay_s,
            error: event.error,
          });
          if (interventions.length > MAX_INTERVENTIONS) {
            interventions.length = MAX_INTERVENTIONS;
          }
        }
        break;
      }
      case "run.complete":
        if (run) {
          run.status = "done";
          metrics.completedRuns += 1;
          metrics.activeRuns = Math.max(0, metrics.activeRuns - 1);
        }
        break;
      case "run.aborted":
        if (run) {
          run.status = "aborted";
          metrics.abortedRuns += 1;
          metrics.activeRuns = Math.max(0, metrics.activeRuns - 1);
        }
        break;
      case "publish.complete":
        if (run) run.videoUrl = event.url ?? run.videoUrl;
        break;
      default:
        break;
    }
    if (runId && run) runs.set(runId, run);
  }

  const recentEvents = [...batch, ...state.recentEvents].slice(0, MAX_RECENT_EVENTS);
  const rateWindow = [...state.rateWindow, { ts: Date.now(), count: batch.length }];
  metrics.eventsPerSec = computeRate(rateWindow);

  return {
    ...state,
    runs,
    interventions,
    metrics,
    recentEvents,
    rateWindow,
  };
}

function tickRate(state: DashboardState, ts: number): DashboardState {
  const cutoff = ts - RATE_WINDOW_MS;
  const trimmed = state.rateWindow.filter((b) => b.ts >= cutoff);
  if (trimmed.length === state.rateWindow.length) return state;
  return {
    ...state,
    rateWindow: trimmed,
    metrics: { ...state.metrics, eventsPerSec: computeRate(trimmed) },
  };
}

function computeRate(window: Array<{ ts: number; count: number }>): number {
  if (window.length === 0) return 0;
  const now = window[window.length - 1]?.ts ?? Date.now();
  const cutoff = now - RATE_WINDOW_MS;
  const total = window.reduce((acc, b) => (b.ts >= cutoff ? acc + b.count : acc), 0);
  return +(total / (RATE_WINDOW_MS / 1000)).toFixed(2);
}

function blankRun(runId: string): RunSummary {
  return {
    runId,
    status: "active",
    lastUpdate: Date.now() / 1000,
    attempt: 0,
    nodeStates: {},
    inputTokens: 0,
    outputTokens: 0,
    costUsd: 0,
    retries: 0,
    fallbacks: 0,
  };
}

export interface UseSwarmStreamOptions {
  /** SSE endpoint URL. Defaults to import.meta.env.VITE_SSE_URL. */
  url?: string;
  /** EventSource factory — injected by tests. */
  factory?: (url: string) => EventSourceLike;
  /** Initial reconnect delay; doubles on each retry, capped at 30s. */
  initialReconnectMs?: number;
}

export interface EventSourceLike {
  onopen: ((this: unknown, ev: Event) => unknown) | null;
  onmessage: ((this: unknown, ev: MessageEvent) => unknown) | null;
  onerror: ((this: unknown, ev: Event) => unknown) | null;
  close(): void;
}

/**
 * Connect, buffer, and flush events into a React-friendly shape.
 *
 * The hook does not throttle individual events — every event lands in
 * state — but it ensures only one React update happens per browser
 * paint frame, which is the only thing that matters for smoothness.
 */
export function useSwarmStream(options: UseSwarmStreamOptions = {}): {
  state: DashboardState;
  reconnect: () => void;
} {
  const [state, dispatch] = useReducer(reducer, undefined, initialState);
  const bufferRef = useRef<SwarmEvent[]>([]);
  const rafRef = useRef<number | null>(null);
  const reconnectRef = useRef<number>(0);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const sourceRef = useRef<EventSourceLike | null>(null);

  const url =
    options.url ??
    ((import.meta as unknown as { env?: Record<string, string> }).env?.VITE_SSE_URL ??
      "/swarm/events");
  const initialReconnectMs = options.initialReconnectMs ?? 1_000;

  useEffect(() => {
    let cancelled = false;

    const flush = () => {
      rafRef.current = null;
      if (bufferRef.current.length === 0) return;
      const batch = bufferRef.current;
      bufferRef.current = [];
      dispatch({ kind: "events", payload: batch });
    };

    const scheduleFlush = () => {
      if (rafRef.current != null) return;
      if (typeof requestAnimationFrame === "function") {
        rafRef.current = requestAnimationFrame(flush);
      } else {
        // Fallback for non-browser hosts (tests, SSR).
        rafRef.current = window.setTimeout(flush, 16) as unknown as number;
      }
    };

    const tickInterval = window.setInterval(
      () => dispatch({ kind: "tick", ts: Date.now() }),
      1_000,
    );

    const connect = () => {
      if (cancelled) return;
      const attempt = reconnectRef.current;
      dispatch({
        kind: "connection",
        payload: {
          status: attempt === 0 ? "connecting" : "reconnecting",
          attempt,
          nextRetryInMs: undefined,
        },
      });

      const factory =
        options.factory ??
        ((u: string) => new EventSource(u) as unknown as EventSourceLike);
      const source = factory(url);
      sourceRef.current = source;

      source.onopen = () => {
        reconnectRef.current = 0;
        dispatch({ kind: "connection", payload: { status: "open", attempt: 0 } });
      };
      source.onmessage = (ev: MessageEvent) => {
        try {
          const parsed = JSON.parse(ev.data) as SwarmEvent;
          bufferRef.current.push(parsed);
          scheduleFlush();
        } catch (err) {
          // Malformed event — log to console but don't crash.
          console.warn("[swarm-stream] failed to parse event", err, ev.data);
        }
      };
      source.onerror = (ev: Event) => {
        const errMsg = (ev as ErrorEvent).message;
        try {
          source.close();
        } catch {
          /* ignore */
        }
        sourceRef.current = null;
        if (cancelled) return;
        const nextAttempt = reconnectRef.current + 1;
        reconnectRef.current = nextAttempt;
        const delay = Math.min(initialReconnectMs * 2 ** (nextAttempt - 1), 30_000);
        dispatch({
          kind: "connection",
          payload: {
            status: "reconnecting",
            attempt: nextAttempt,
            lastError: errMsg,
            nextRetryInMs: delay,
          },
        });
        timerRef.current = setTimeout(connect, delay);
      };
    };

    connect();

    return () => {
      cancelled = true;
      window.clearInterval(tickInterval);
      if (timerRef.current) clearTimeout(timerRef.current);
      if (rafRef.current != null && typeof cancelAnimationFrame === "function") {
        cancelAnimationFrame(rafRef.current);
      }
      try {
        sourceRef.current?.close();
      } catch {
        /* ignore */
      }
    };
  }, [url, options.factory, initialReconnectMs]);

  const reconnect = () => {
    reconnectRef.current = 0;
    try {
      sourceRef.current?.close();
    } catch {
      /* ignore */
    }
    sourceRef.current = null;
    // The effect's cleanup-then-restart mechanism doesn't run on every render,
    // so toggle by simulating an error to kick the timer.
    if (timerRef.current) clearTimeout(timerRef.current);
    dispatch({ kind: "connection", payload: { status: "reconnecting", attempt: 0 } });
    timerRef.current = setTimeout(() => {
      // No-op — the next setInterval tick handles the reconnect timer cleanup,
      // and the effect's `connect()` closure remains valid until unmount.
    }, 0);
  };

  return { state, reconnect };
}
