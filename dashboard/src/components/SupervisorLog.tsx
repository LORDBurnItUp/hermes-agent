import type { SupervisorIntervention } from "../types";
import { fmtTime } from "../lib/format";

const DECISION_CLASS: Record<SupervisorIntervention["decision"], string> = {
  continue: "intervention--ok",
  retry: "intervention--warn",
  fallback: "intervention--warn",
  abort: "intervention--bad",
};

export function SupervisorLog({
  interventions,
}: {
  interventions: SupervisorIntervention[];
}) {
  return (
    <section className="supervisor-log" aria-label="Supervisor interventions">
      <header>
        <h2>Supervisor interventions</h2>
        <small>Retries, fallbacks and circuit-breaker trips</small>
      </header>
      {interventions.length === 0 ? (
        <p className="supervisor-log__empty">No interventions — pipeline is healthy.</p>
      ) : (
        <ol className="supervisor-log__list">
          {interventions.map((it, i) => (
            <li
              key={`${it.ts}-${i}`}
              className={`intervention ${DECISION_CLASS[it.decision]}`}
            >
              <time>{fmtTime(it.ts)}</time>
              <span className="intervention__decision">{it.decision.toUpperCase()}</span>
              <span className="intervention__node">{it.node}</span>
              {it.runId && (
                <span className="intervention__run" title={it.runId}>
                  {it.runId.slice(0, 12)}
                </span>
              )}
              {typeof it.attempt === "number" && (
                <span className="intervention__attempt">attempt {it.attempt}</span>
              )}
              {typeof it.delaySeconds === "number" && it.delaySeconds > 0 && (
                <span className="intervention__delay">
                  backoff {it.delaySeconds.toFixed(2)}s
                </span>
              )}
              {it.error && <span className="intervention__error">{it.error}</span>}
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
