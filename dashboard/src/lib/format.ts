export function fmtTime(ts: number): string {
  return new Date(ts * 1000).toLocaleTimeString();
}

export function fmtUsd(value: number): string {
  if (value < 0.01) return `$${value.toFixed(4)}`;
  if (value < 1) return `$${value.toFixed(3)}`;
  return `$${value.toFixed(2)}`;
}

export function fmtTokens(value: number): string {
  if (value > 1_000_000) return `${(value / 1_000_000).toFixed(2)}M`;
  if (value > 1_000) return `${(value / 1_000).toFixed(1)}k`;
  return String(value);
}

export function fmtRelative(ts: number, now = Date.now() / 1000): string {
  const delta = now - ts;
  if (delta < 1) return "just now";
  if (delta < 60) return `${Math.floor(delta)}s ago`;
  if (delta < 3600) return `${Math.floor(delta / 60)}m ago`;
  return `${Math.floor(delta / 3600)}h ago`;
}
