#!/usr/bin/env python3
"""kg.py — knowledge-graph dev tool over the rev-eval codebase + docs/.

Local-only, free. Two layers:
  Layer 1 (structural)  — deterministic doc-graph; needs NO model. `structure`, `export`.
  Layer 2 (semantic)    — LightRAG + containerized Ollama; toggle with `up`/`down`.

See docs/plans/tool-knowledge-graph.md and ./README.md.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

# Make `src` importable regardless of the caller's cwd.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from src import config  # noqa: E402

COMPOSE_FILE = config.TOOL_DIR / "docker-compose.kg.yml"
CONTAINER = "rev-eval-kg-ollama"


# --------------------------------------------------------------------------- #
# Layer 2 lifecycle: containerized Ollama on/off (the "model runtime").
# --------------------------------------------------------------------------- #
def _compose(*args: str) -> int:
    """Run `docker compose -f <kg compose> --profile kg <args>`."""
    cmd = ["docker", "compose", "-f", str(COMPOSE_FILE), "--profile", "kg", *args]
    print(f"$ {' '.join(cmd)}")
    return subprocess.call(cmd)


def cmd_up(_: argparse.Namespace) -> int:
    """Start the Ollama container and pull models on first run."""
    rc = _compose("up", "-d")
    if rc != 0:
        return rc
    for model in config.PULL_MODELS:
        print(f"\n==> ollama pull {model}")
        rc = subprocess.call(["docker", "exec", CONTAINER, "ollama", "pull", model])
        if rc != 0:
            print(f"!! failed to pull {model}", file=sys.stderr)
            return rc
    print(
        f"\nKG model runtime up at {config.OLLAMA_HOST}.\n"
        "Idle RAM ~0 (OLLAMA_KEEP_ALIVE=0 unloads after each request).\n"
        "Next: python kg.py ingest  then  python kg.py query \"...\""
    )
    return 0


def cmd_down(_: argparse.Namespace) -> int:
    """Stop and remove the Ollama container (frees all model RAM)."""
    return _compose("down")


# --------------------------------------------------------------------------- #
# Layer 1 (no model) + Layer 2 query — delegate to src modules (lazy import so
# `up`/`down`/`structure`/`export` work without LightRAG/Ollama installed).
# --------------------------------------------------------------------------- #
def cmd_structure(args: argparse.Namespace) -> int:
    from src import structural

    return structural.run_structure(args.node)


def cmd_export(args: argparse.Namespace) -> int:
    from src import export

    return export.run_export(args.format, args.out, include_code=args.include_code)


def cmd_ingest(args: argparse.Namespace) -> int:
    from src import ingest

    return ingest.run_ingest(include_source=args.include_source)


def cmd_query(args: argparse.Namespace) -> int:
    from src import query

    return query.run_query(args.text, mode=args.mode)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="kg.py", description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("up", help="start containerized Ollama + pull models").set_defaults(func=cmd_up)
    sub.add_parser("down", help="stop Ollama, free model RAM").set_defaults(func=cmd_down)

    s = sub.add_parser("structure", help="Layer 1 lookup (no model needed)")
    s.add_argument("node", help='node id, e.g. "W4-F1", "ADR-0001", or a file path')
    s.set_defaults(func=cmd_structure)

    e = sub.add_parser("export", help="export the structural graph")
    e.add_argument("--format", choices=["json", "mermaid", "dot"], default="mermaid")
    e.add_argument("--out", default=None, help="output file (default: stdout)")
    e.add_argument(
        "--include-code",
        action="store_true",
        help="keep code evidence nodes in mermaid/dot (default: drop for readability)",
    )
    e.set_defaults(func=cmd_export)

    i = sub.add_parser("ingest", help="Layer 2: build LightRAG index (needs Ollama up)")
    i.add_argument(
        "--include-source",
        action="store_true",
        help="also ingest ALL source files (~16k); off by default",
    )
    i.set_defaults(func=cmd_ingest)

    q = sub.add_parser("query", help="Layer 2: natural-language query (needs Ollama up)")
    q.add_argument("text", help="the question")
    q.add_argument(
        "--mode",
        choices=["naive", "local", "global", "hybrid", "mix"],
        default="hybrid",
        help="LightRAG retrieval mode (default: hybrid)",
    )
    q.set_defaults(func=cmd_query)

    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
