"""Cron entrypoint for the analytics & feedback agent.

Wire this into the system scheduler::

    # crontab (daily at 06:30 UTC)
    30 6 * * *  cd /opt/hermes-agent && python -m swarm.cron_analytics --csv swarm/sample_topics.csv

Or, with the project's own scheduler::

    [project.scripts]
    swarm-analytics = "swarm.cron_analytics:main"

Then ``swarm-analytics --csv swarm/sample_topics.csv``.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from swarm.analytics_agent import run_analytics_cycle


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Swarm OS analytics & feedback cron.")
    parser.add_argument("--csv", type=Path, required=True, help="Topic CSV to append into.")
    parser.add_argument(
        "--published-log",
        type=Path,
        default=None,
        help="Override default ~/.hermes/swarm/published.jsonl path.",
    )
    parser.add_argument(
        "--report-dir",
        type=Path,
        default=None,
        help="If set, writes the OptimizationReport JSON for auditing.",
    )
    parser.add_argument("--lookback-days", type=int, default=14)
    parser.add_argument("--new-ideas", type=int, default=5)
    parser.add_argument(
        "--live", action="store_true", help="hit real APIs (needs YouTube + LLM keys)"
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    result = run_analytics_cycle(
        csv_path=args.csv,
        published_log_path=args.published_log,
        report_dir=args.report_dir,
        lookback_days=args.lookback_days,
        target_new_ideas=args.new_ideas,
        dry_run=not args.live,
    )

    print(f"analyzed videos      : {result.analyzed_video_count}")
    print(f"new topics appended  : {result.new_rows_written}")
    print(f"csv path             : {result.csv_path}")
    if result.report_path:
        print(f"report written to    : {result.report_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
