"""End-to-end demo runner for the Swarm OS.

Phase 2 deliverable: prints a sample Shotstack JSON payload.
Phase 3 deliverable: drives the full pipeline
    Ingest -> Script (LLM) -> Voiceover -> B-Roll -> Assembly -> Publish

Usage::

    python -m swarm.demo                       # built-in finance topic
    python -m swarm.demo --csv path.csv        # iterate a CSV of topics
    python -m swarm.demo --live                # hit real APIs (needs keys)

API keys required only with ``--live``:
    ANTHROPIC_API_KEY (or OPENAI_API_KEY) for script_node
    ELEVENLABS_API_KEY + ELEVENLABS_AUDIO_PUT_URL for voiceover_node
    SWARM_BROLL_PROVIDER=sora|veo + relevant credentials for broll_node
    SHOTSTACK_API_KEY for video_assembly_node
    YOUTUBE_CLIENT_ID / YOUTUBE_CLIENT_SECRET / YOUTUBE_REFRESH_TOKEN for publish_node
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from swarm.csv_ingest import ingest_topics_from_csv, iter_topic_payloads
from swarm.graph import build_graph, run_pipeline
from swarm.video_assembly import build_shotstack_payload


def _sample_payload() -> dict:
    """A canonical Shotstack JSON for a Budgeting-for-Beginners demo."""
    return build_shotstack_payload(
        video_title="Budgeting for Beginners — 3 Tips That Actually Work",
        script_caption="Tip #1: Pay yourself first",
        audio_url="https://example.invalid/dry-run/vo-rachel.mp3",
        niche="personal_finance",
        duration_seconds=30.0,
        overlay_lines=[
            "Budgeting for Beginners",
            "Tip 1 — Pay yourself first",
            "Tip 2 — Track every dollar",
            "Tip 3 — Automate the boring stuff",
        ],
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Swarm OS Phase 2 demo runner.")
    parser.add_argument("--csv", type=Path, help="optional CSV of topics to ingest")
    parser.add_argument("--live", action="store_true", help="hit real APIs (needs keys)")
    parser.add_argument("--no-run", action="store_true", help="print sample JSON only; skip pipeline")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    print("=" * 78)
    print("SWARM OS · Phase 2 · Sample Shotstack JSON payload")
    print("=" * 78)
    print(json.dumps(_sample_payload(), indent=2))
    print("=" * 78)

    if args.no_run:
        return 0

    dry_run = not args.live
    graph = build_graph(dry_run=dry_run)

    if args.csv:
        rows = ingest_topics_from_csv(args.csv)
        print(f"\nIngested {len(rows)} topics from {args.csv}; running pipeline (dry_run={dry_run}).\n")
        for payload in iter_topic_payloads(rows):
            final = run_pipeline(graph=graph, dry_run=dry_run, **payload)
            print(
                f"  · {payload['video_topic']!r}: "
                f"render_id={final.get('shotstack_render_id')} "
                f"status={final.get('shotstack_status')} "
                f"aborted={final.get('aborted', False)}"
            )
    else:
        topic = "Budgeting for Beginners — 3 Tips That Actually Work"
        print(f"\nRunning single pipeline (dry_run={dry_run}) for: {topic!r}\n")
        final = run_pipeline(
            video_topic=topic,
            script_caption="Tip #1: Pay yourself first",
            graph=graph,
            dry_run=dry_run,
        )
        print("\n--- Final state summary ---")
        print(f"  run_id           : {final.get('run_id')}")
        print(f"  video_title      : {final.get('video_title')}")
        print(f"  script_caption   : {final.get('script_caption')}")
        print(f"  visual_prompt    : {final.get('visual_prompt')}")
        print(f"  audio_url        : {final.get('audio_url')}")
        print(f"  broll_url        : {final.get('broll_url')} (provider={final.get('broll_provider')})")
        print(f"  shotstack_render : {final.get('shotstack_render_id')}")
        print(f"  rendered_mp4     : {final.get('video_url')}")
        print(f"  published_url    : {final.get('published_url')}")
        print(f"  privacy          : {final.get('published_privacy')}")
        print(f"  tags             : {final.get('video_tags')}")
        print(f"  aborted          : {final.get('aborted', False)}")
        print(f"  nodes executed   : {[h['node'] for h in final.get('node_history') or []]}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
