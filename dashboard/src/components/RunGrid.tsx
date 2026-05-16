import type { RunSummary } from "../types";
import { RunCard } from "./RunCard";

export function RunGrid({ runs }: { runs: RunSummary[] }) {
  if (runs.length === 0) {
    return (
      <section className="run-grid run-grid--empty" aria-label="Active runs">
        <p>No active runs. Trigger a pipeline to see live activity here.</p>
      </section>
    );
  }
  return (
    <section className="run-grid" aria-label="Active runs">
      {runs.map((run) => (
        <RunCard key={run.runId} run={run} />
      ))}
    </section>
  );
}
