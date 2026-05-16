import { useMemo } from "react";
import { useSwarmStream } from "./hooks/useSwarmStream";
import { MetricsBar } from "./components/MetricsBar";
import { RunGrid } from "./components/RunGrid";
import { SupervisorLog } from "./components/SupervisorLog";

export function App() {
  const { state } = useSwarmStream();

  // Active runs first, then most-recently-updated. Done/aborted runs
  // linger for 2 minutes so the operator can see what just finished.
  const runs = useMemo(() => {
    const cutoff = Date.now() / 1000 - 120;
    return Array.from(state.runs.values())
      .filter((r) => r.status === "active" || r.lastUpdate >= cutoff)
      .sort((a, b) => {
        if (a.status !== b.status) {
          const order = { active: 0, aborted: 1, done: 2 } as const;
          return order[a.status] - order[b.status];
        }
        return b.lastUpdate - a.lastUpdate;
      });
  }, [state.runs]);

  return (
    <div className="app">
      <MetricsBar metrics={state.metrics} connection={state.connection} />
      <main className="app__body">
        <RunGrid runs={runs} />
        <SupervisorLog interventions={state.interventions} />
      </main>
    </div>
  );
}
