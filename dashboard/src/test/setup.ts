import "@testing-library/jest-dom/vitest";

// jsdom doesn't ship requestAnimationFrame by default — polyfill so the
// hook flushes on its normal RAF cadence in tests.
if (typeof globalThis.requestAnimationFrame === "undefined") {
  globalThis.requestAnimationFrame = (cb: FrameRequestCallback) =>
    setTimeout(() => cb(performance.now()), 0) as unknown as number;
  globalThis.cancelAnimationFrame = (id: number) => clearTimeout(id);
}
