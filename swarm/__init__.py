"""Swarm OS — autonomous YouTube automation built on LangGraph.

This package implements Phase 2 of the Swarm OS roadmap: the programmatic
media supply chain. Audio is generated via ElevenLabs, video is assembled
via Shotstack's cloud rendering API (no local FFmpeg), and the whole
pipeline is orchestrated by a LangGraph StateGraph with an auto-healing
supervisor and a Live View SSE dashboard.

Public surface:
    SwarmState              — TypedDict state schema shared across nodes
    build_graph             — assemble and compile the LangGraph
    run_pipeline            — convenience runner for a single topic
    ingest_topics_from_csv  — bulk CSV → list[topic] ingestor
"""

from swarm.state import SwarmState, NodeStatus, SupervisorDecision
from swarm.csv_ingest import ingest_topics_from_csv, TopicRow
from swarm.graph import build_graph, run_pipeline
from swarm.analytics_agent import (
    OptimizationReport,
    TopicIdea,
    MetricsRow,
    run_analytics_cycle,
)

__all__ = [
    "SwarmState",
    "NodeStatus",
    "SupervisorDecision",
    "TopicRow",
    "ingest_topics_from_csv",
    "build_graph",
    "run_pipeline",
    "OptimizationReport",
    "TopicIdea",
    "MetricsRow",
    "run_analytics_cycle",
]
