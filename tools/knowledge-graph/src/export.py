"""Export the Layer 1 structural graph to JSON / Mermaid / Graphviz DOT.

Pure stdlib; runs with the model down. JSON always emits the full graph.
Mermaid/DOT default to the feature/adr/plan/doc view (the 192 `code` evidence
nodes are dropped unless --include-code, and the count dropped is logged — no
silent truncation).
"""
from __future__ import annotations

import json
import sys

from src import structural

_SHAPE = {  # mermaid node shapes by type
    "feature": ("[", "]"),
    "adr": ("{{", "}}"),
    "plan": ("([", "])"),
    "doc": (">", "]"),
    "code": ("[(", ")]"),
}


def _filter(g: structural.Graph, include_code: bool):
    if include_code:
        return g.nodes, g.edges, 0
    keep = {nid: n for nid, n in g.nodes.items() if n.type != "code"}
    edges = [e for e in g.edges if e.src in keep and e.dst in keep]
    dropped = len(g.nodes) - len(keep)
    return keep, edges, dropped


def _to_json(g: structural.Graph) -> str:
    return json.dumps(
        {
            "nodes": [
                {"id": n.id, "type": n.type, "label": n.label,
                 "path": n.path, "exists": n.exists}
                for n in g.nodes.values()
            ],
            "edges": [{"src": e.src, "rel": e.rel, "dst": e.dst} for e in g.edges],
        },
        indent=2,
    )


def _to_mermaid(nodes, edges) -> str:
    alias = {nid: f"n{i}" for i, nid in enumerate(nodes)}
    lines = ["graph LR"]
    for nid, n in nodes.items():
        open_, close = _SHAPE.get(n.type, ("[", "]"))
        text = n.id.replace('"', "'")
        lines.append(f'  {alias[nid]}{open_}"{text}"{close}')
    for e in edges:
        lines.append(f"  {alias[e.src]} -->|{e.rel}| {alias[e.dst]}")
    return "\n".join(lines)


def _to_dot(nodes, edges) -> str:
    alias = {nid: f"n{i}" for i, nid in enumerate(nodes)}
    lines = ["digraph kg {", "  rankdir=LR;", '  node [shape=box, fontsize=10];']
    for nid, n in nodes.items():
        label = n.id.replace('"', "'")
        lines.append(f'  {alias[nid]} [label="{label}"];')
    for e in edges:
        lines.append(f'  {alias[e.src]} -> {alias[e.dst]} [label="{e.rel}"];')
    lines.append("}")
    return "\n".join(lines)


def run_export(fmt: str, out: str | None, include_code: bool = False) -> int:
    g = structural.build_graph()
    if fmt == "json":
        content = _to_json(g)
    else:
        nodes, edges, dropped = _filter(g, include_code)
        if dropped:
            print(
                f"note: dropped {dropped} code node(s) from {fmt} view "
                f"(use --include-code to keep them).",
                file=sys.stderr,
            )
        content = _to_mermaid(nodes, edges) if fmt == "mermaid" else _to_dot(nodes, edges)

    if out:
        with open(out, "w", encoding="utf-8") as fh:
            fh.write(content + "\n")
        print(f"wrote {fmt} → {out}")
    else:
        print(content)
    return 0
