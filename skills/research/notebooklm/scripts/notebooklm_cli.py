#!/usr/bin/env python3
"""Thin wrapper around the notebooklm-py CLI for use from Hermes skills.

Checks that notebooklm-py is installed and authenticated before running
commands.  All heavy lifting is delegated to the upstream package.

Usage:
    python notebooklm_cli.py check          # verify install + auth
    python notebooklm_cli.py create "Name"  # create a notebook
    python notebooklm_cli.py list           # list notebooks
    python notebooklm_cli.py add-source NOTEBOOK_ID URL_OR_PATH
    python notebooklm_cli.py ask NOTEBOOK_ID "question"
    python notebooklm_cli.py audio NOTEBOOK_ID [--instructions "..."] [--output path.mp3]
"""
import argparse
import json
import shutil
import subprocess
import sys


def _run(args: list[str], check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(args, capture_output=True, text=True, check=check)


def cmd_check(_args: argparse.Namespace) -> None:
    if not shutil.which("notebooklm"):
        print(json.dumps({"status": "NOT_INSTALLED",
                          "fix": "pip install 'notebooklm-py[browser]' && playwright install chromium"}))
        sys.exit(1)
    result = _run(["notebooklm", "auth", "check", "--test"], check=False)
    if result.returncode != 0:
        print(json.dumps({"status": "NOT_AUTHENTICATED",
                          "fix": "notebooklm login",
                          "detail": result.stderr.strip()}))
        sys.exit(1)
    print(json.dumps({"status": "OK"}))


def cmd_create(args: argparse.Namespace) -> None:
    result = _run(["notebooklm", "create", args.name])
    print(result.stdout)


def cmd_list(_args: argparse.Namespace) -> None:
    result = _run(["notebooklm", "list"])
    print(result.stdout)


def cmd_add_source(args: argparse.Namespace) -> None:
    _run(["notebooklm", "use", args.notebook_id])
    result = _run(["notebooklm", "source", "add", args.source])
    print(result.stdout)


def cmd_ask(args: argparse.Namespace) -> None:
    _run(["notebooklm", "use", args.notebook_id])
    result = _run(["notebooklm", "ask", args.question])
    print(result.stdout)


def cmd_audio(args: argparse.Namespace) -> None:
    _run(["notebooklm", "use", args.notebook_id])
    gen_args = ["notebooklm", "generate", "audio"]
    if args.instructions:
        gen_args.append(args.instructions)
    gen_args.append("--wait")
    result = _run(gen_args)
    print(result.stdout)

    if args.output:
        dl = _run(["notebooklm", "download", "audio", args.output])
        print(dl.stdout)


def main() -> None:
    parser = argparse.ArgumentParser(description="NotebookLM helper for Hermes")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("check", help="Verify installation and auth")

    p_create = sub.add_parser("create", help="Create a notebook")
    p_create.add_argument("name")

    sub.add_parser("list", help="List notebooks")

    p_src = sub.add_parser("add-source", help="Add a source to a notebook")
    p_src.add_argument("notebook_id")
    p_src.add_argument("source", help="URL or file path")

    p_ask = sub.add_parser("ask", help="Ask a question")
    p_ask.add_argument("notebook_id")
    p_ask.add_argument("question")

    p_audio = sub.add_parser("audio", help="Generate audio overview")
    p_audio.add_argument("notebook_id")
    p_audio.add_argument("--instructions", default="")
    p_audio.add_argument("--output", default="", help="Download path for mp3")

    args = parser.parse_args()
    {
        "check": cmd_check,
        "create": cmd_create,
        "list": cmd_list,
        "add-source": cmd_add_source,
        "ask": cmd_ask,
        "audio": cmd_audio,
    }[args.command](args)


if __name__ == "__main__":
    main()
