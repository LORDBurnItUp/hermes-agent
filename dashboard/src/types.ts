// Event shapes emitted by swarm.events.publish on the FastAPI side.
// Keep these in sync with swarm/events.py + the agents that publish events.

export type EventType =
  | "stream.hello"
  | "run.start"
  | "node.start"
  | "node.success"
  | "node.error"
  | "node.tokens"
  | "node.cost"
  | "supervisor.decision"
  | "run.complete"
  | "run.aborted"
  | "publish.complete"
  | "analytics.start"
  | "analytics.empty"
  | "analytics.fetched"
  | "analytics.summarised"
  | "analytics.complete";

export type NodeName =
  | "ingest"
  | "script"
  | "voiceover"
  | "broll"
  | "video_assembly"
  | "publish";

export type SupervisorDecision = "continue" | "retry" | "fallback" | "abort";

export interface SwarmEvent {
  type: EventType;
  ts: number;
  run_id?: string;
  node?: NodeName | string;
  attempt?: number;
  duration_s?: number;
  error?: string;
  decision?: SupervisorDecision;
  delay_s?: number;
  topic?: string;
  niche?: string;

  // node.tokens
  provider?: string;
  model?: string;
  input_tokens?: number;
  output_tokens?: number;
  cost_usd?: number;

  // node.cost (provider/cost_usd reused from above)
  units?: Record<string, number>;

  // publish.complete
  video_id?: string;
  url?: string;
  privacy?: string;

  // analytics.*
  cycle_id?: string;
  lookback_days?: number;
  video_count?: number;
  winners?: number;
  losers?: number;
  new_ideas?: number;
  new_rows_written?: number;
  csv_path?: string;
  failed_node?: string;
}

export type RunStatus = "active" | "done" | "aborted";

export interface RunSummary {
  runId: string;
  topic?: string;
  niche?: string;
  status: RunStatus;
  currentNode?: string;
  lastUpdate: number;
  attempt: number;
  // Per-node history compressed for the card view.
  nodeStates: Partial<Record<string, "running" | "success" | "error">>;
  inputTokens: number;
  outputTokens: number;
  costUsd: number;
  retries: number;
  fallbacks: number;
  videoUrl?: string;
}

export interface SupervisorIntervention {
  ts: number;
  runId?: string;
  node: string;
  decision: SupervisorDecision;
  attempt?: number;
  delaySeconds?: number;
  error?: string;
}

export interface Metrics {
  eventsPerSec: number;
  totalEvents: number;
  totalRuns: number;
  activeRuns: number;
  completedRuns: number;
  abortedRuns: number;
  totalCostUsd: number;
  inputTokens: number;
  outputTokens: number;
  supervisorRetries: number;
  supervisorFallbacks: number;
  supervisorAborts: number;
}

export interface ConnectionState {
  status: "connecting" | "open" | "reconnecting" | "closed";
  attempt: number;
  lastError?: string;
  nextRetryInMs?: number;
}
