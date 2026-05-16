import type { RunSummary } from "../types";
import { fmtRelative, fmtTokens, fmtUsd } from "../lib/format";

const NODE_ORDER: string[] = [
  "ingest",
  "script",
  "voiceover",
  "broll",
  "video_assembly",
  "publish",
];

const NODE_LABEL: Record<string, string> = {
  ingest: "ingest",
  script: "script",
  voiceover: "voice",
  broll: "b-roll",
  video_assembly: "render",
  publish: "publish",
};

export function RunCard({ run }: { run: RunSummary }) {
  return (
    <article className="run-card" data-status={run.status}>
      <header className="run-card__hd">
        <div>
          <strong>{run.topic ?? run.runId}</strong>
          <div className="run-card__sub">{run.niche ?? "—"}</div>
        </div>
        <div className="run-card__status">
          {run.status === "active" && <span className="badge badge--info">active</span>}
          {run.status === "done" && <span className="badge badge--ok">complete</span>}
          {run.status === "aborted" && <span className="badge badge--bad">aborted</span>}
          {run.attempt > 1 && (
            <span className="badge badge--warn">attempt {run.attempt}</span>
          )}
        </div>
      </header>

      <ol className="run-card__nodes" aria-label="Pipeline nodes">
        {NODE_ORDER.map((node) => {
          const state = run.nodeStates[node];
          return (
            <li key={node} data-state={state ?? "pending"} title={node}>
              <span className="run-card__node-dot" aria-hidden />
              <span className="run-card__node-label">{NODE_LABEL[node]}</span>
            </li>
          );
        })}
      </ol>

      <footer className="run-card__ft">
        <div>
          <span className="kbd">{fmtTokens(run.inputTokens + run.outputTokens)} tok</span>
          <span className="kbd">{fmtUsd(run.costUsd)}</span>
          {run.retries > 0 && (
            <span className="kbd kbd--warn">{run.retries}× retry</span>
          )}
          {run.fallbacks > 0 && (
            <span className="kbd kbd--warn">{run.fallbacks}× fallback</span>
          )}
        </div>
        <small>{fmtRelative(run.lastUpdate)}</small>
      </footer>

      {run.videoUrl && (
        <a className="run-card__link" href={run.videoUrl} target="_blank" rel="noreferrer">
          {run.videoUrl}
        </a>
      )}
    </article>
  );
}
