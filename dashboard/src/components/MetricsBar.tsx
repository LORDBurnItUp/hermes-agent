import type { ConnectionState, Metrics } from "../types";
import { fmtTokens, fmtUsd } from "../lib/format";

interface Props {
  metrics: Metrics;
  connection: ConnectionState;
}

export function MetricsBar({ metrics, connection }: Props) {
  return (
    <header className="metrics-bar">
      <div className="metrics-bar__brand">
        <span className="dot" data-state={connection.status} aria-hidden />
        <strong>Swarm OS</strong>
        <small className="metrics-bar__conn">
          {connection.status === "open" && "connected"}
          {connection.status === "connecting" && "connecting…"}
          {connection.status === "reconnecting" &&
            `reconnecting (attempt ${connection.attempt}` +
              (connection.nextRetryInMs
                ? `, retry in ${(connection.nextRetryInMs / 1000).toFixed(0)}s`
                : "") +
              ")"}
          {connection.status === "closed" && "offline"}
        </small>
      </div>
      <Tile label="events/s" value={metrics.eventsPerSec.toFixed(1)} />
      <Tile label="active runs" value={metrics.activeRuns} />
      <Tile
        label="runs (done / aborted)"
        value={`${metrics.completedRuns} / ${metrics.abortedRuns}`}
      />
      <Tile label="cost" value={fmtUsd(metrics.totalCostUsd)} />
      <Tile
        label="tokens in / out"
        value={`${fmtTokens(metrics.inputTokens)} / ${fmtTokens(metrics.outputTokens)}`}
      />
      <Tile
        label="supervisor R / F / A"
        value={`${metrics.supervisorRetries} / ${metrics.supervisorFallbacks} / ${metrics.supervisorAborts}`}
        tone={metrics.supervisorAborts > 0 ? "alert" : "default"}
      />
    </header>
  );
}

function Tile({
  label,
  value,
  tone = "default",
}: {
  label: string;
  value: string | number;
  tone?: "default" | "alert";
}) {
  return (
    <div className="metrics-tile" data-tone={tone}>
      <div className="metrics-tile__value">{value}</div>
      <div className="metrics-tile__label">{label}</div>
    </div>
  );
}
