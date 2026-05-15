import { describe, it, expect, vi } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { useSwarmStream } from "./useSwarmStream";
import type { EventSourceLike } from "./useSwarmStream";

class FakeEventSource implements EventSourceLike {
  static instances: FakeEventSource[] = [];
  url: string;
  onopen: ((this: unknown, ev: Event) => unknown) | null = null;
  onmessage: ((this: unknown, ev: MessageEvent) => unknown) | null = null;
  onerror: ((this: unknown, ev: Event) => unknown) | null = null;
  closed = false;

  constructor(url: string) {
    this.url = url;
    FakeEventSource.instances.push(this);
  }

  close() {
    this.closed = true;
  }

  emit(data: unknown) {
    this.onmessage?.(
      new MessageEvent("message", { data: JSON.stringify(data) }) as MessageEvent,
    );
  }

  open() {
    this.onopen?.(new Event("open"));
  }

  fail(message = "boom") {
    this.onerror?.(new ErrorEvent("error", { message }));
  }
}

function makeFactory() {
  FakeEventSource.instances.length = 0;
  return (url: string) => new FakeEventSource(url);
}

describe("useSwarmStream", () => {
  it("buffers events into a single batched dispatch per frame", async () => {
    const factory = makeFactory();
    const { result } = renderHook(() =>
      useSwarmStream({ url: "/swarm/events", factory }),
    );

    const es = FakeEventSource.instances[0];
    expect(es).toBeDefined();
    act(() => es.open());

    act(() => {
      es.emit({ type: "run.start", ts: 1, run_id: "r1", topic: "Roth IRA" });
      es.emit({ type: "node.start", ts: 1.1, run_id: "r1", node: "script", attempt: 1 });
      es.emit({
        type: "node.tokens",
        ts: 1.2,
        run_id: "r1",
        node: "script",
        provider: "anthropic",
        model: "claude-sonnet-4-6",
        input_tokens: 350,
        output_tokens: 220,
        cost_usd: 0.0044,
      });
    });

    await waitFor(() => {
      expect(result.current.state.metrics.totalEvents).toBe(3);
    });

    const run = result.current.state.runs.get("r1");
    expect(run?.topic).toBe("Roth IRA");
    expect(run?.currentNode).toBe("script");
    expect(run?.inputTokens).toBe(350);
    expect(run?.outputTokens).toBe(220);
    expect(run?.costUsd).toBeCloseTo(0.0044, 5);
    expect(result.current.state.metrics.activeRuns).toBe(1);
    expect(result.current.state.metrics.totalCostUsd).toBeCloseTo(0.0044, 5);
  });

  it("records supervisor interventions but not 'continue' decisions", async () => {
    const factory = makeFactory();
    const { result } = renderHook(() => useSwarmStream({ url: "/x", factory }));
    const es = FakeEventSource.instances[0];
    act(() => es.open());

    act(() => {
      es.emit({
        type: "supervisor.decision",
        ts: 2,
        run_id: "r1",
        node: "voiceover",
        decision: "continue",
        attempt: 1,
      });
      es.emit({
        type: "supervisor.decision",
        ts: 3,
        run_id: "r1",
        node: "voiceover",
        decision: "retry",
        attempt: 2,
        delay_s: 1.7,
        error: "ElevenLabs 429",
      });
      es.emit({
        type: "supervisor.decision",
        ts: 4,
        run_id: "r1",
        node: "video_assembly",
        decision: "abort",
        error: "circuit breaker",
      });
    });

    await waitFor(() => {
      expect(result.current.state.interventions).toHaveLength(2);
    });
    expect(result.current.state.metrics.supervisorRetries).toBe(1);
    expect(result.current.state.metrics.supervisorAborts).toBe(1);
    expect(result.current.state.interventions[0].decision).toBe("abort");
    expect(result.current.state.interventions[1].decision).toBe("retry");
  });

  it("auto-reconnects with exponential backoff after an error", async () => {
    vi.useFakeTimers();
    const factory = makeFactory();
    const { result } = renderHook(() =>
      useSwarmStream({ url: "/x", factory, initialReconnectMs: 1000 }),
    );

    const first = FakeEventSource.instances[0];
    act(() => first.open());
    expect(result.current.state.connection.status).toBe("open");

    act(() => first.fail("connection reset"));
    expect(result.current.state.connection.status).toBe("reconnecting");
    expect(result.current.state.connection.attempt).toBe(1);
    expect(result.current.state.connection.nextRetryInMs).toBe(1000);

    // First retry attempt fires after 1s.
    act(() => {
      vi.advanceTimersByTime(1000);
    });
    const second = FakeEventSource.instances[1];
    expect(second).toBeDefined();
    act(() => second.fail("still down"));
    expect(result.current.state.connection.attempt).toBe(2);
    expect(result.current.state.connection.nextRetryInMs).toBe(2000);

    // Second retry — happens after 2s.
    act(() => {
      vi.advanceTimersByTime(2000);
    });
    const third = FakeEventSource.instances[2];
    expect(third).toBeDefined();
    act(() => third.open());
    expect(result.current.state.connection.status).toBe("open");
    expect(result.current.state.connection.attempt).toBe(0);

    vi.useRealTimers();
  });

  it("ignores malformed event payloads without crashing", async () => {
    const warn = vi.spyOn(console, "warn").mockImplementation(() => {});
    const factory = makeFactory();
    const { result } = renderHook(() => useSwarmStream({ url: "/x", factory }));
    const es = FakeEventSource.instances[0];
    act(() => es.open());
    act(() => {
      // Manually call onmessage with a non-JSON payload.
      es.onmessage?.(new MessageEvent("message", { data: "not-json" }) as MessageEvent);
    });
    await waitFor(() => {
      expect(warn).toHaveBeenCalled();
    });
    expect(result.current.state.metrics.totalEvents).toBe(0);
    warn.mockRestore();
  });
});
