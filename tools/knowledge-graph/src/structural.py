"""Layer 1 — deterministic structural graph over docs/ (NO model required).

Walks docs/ and builds a typed graph purely from the repo's documentation
conventions (feature ids, ADR headers, relative md links, inline code-path
evidence). Pure stdlib: `structure` and `export` run with zero pip installs and
with the Ollama container down.

Node types : feature | adr | plan | doc | code
Edge rels  : DEPENDS_ON, UNBLOCKS, DECIDED_BY, DOCUMENTED_BY, SPECIFIED_BY,
             EVIDENCED_BY, LINKS_TO
"""
from __future__ import annotations

import functools
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from src import config

# --------------------------------------------------------------------------- #
# Patterns keyed off the repo's doc conventions (see docs/features, docs/adr).
# --------------------------------------------------------------------------- #
FEATURE_ID = re.compile(r"\bW(\d)-([FMfm])(\d+)\b")
FEATURE_STEM = re.compile(r"^w(\d)-([fm])(\d+)", re.I)
ADR_STEM = re.compile(r"^(\d+)-")
MD_LINK = re.compile(r"\[([^\]]+)\]\(([^)]+?\.md)(?:#[^)]*)?\)")
SPEC_REF = re.compile(r"(days_[\w]+\.md)")
INLINE_CODE = re.compile(r"`([^`]+)`")
# A code token: path with a source extension, optional :line(s) suffix. The
# char class excludes parens/spaces so prose like `AVG(answers.score)` is ignored.
CODE_PATH = re.compile(
    r"^([\w./\-]+\.(?:py|ts|tsx|js|jsx|yml|yaml|sql|sh|toml|ini|cfg|json))"
    r"(?::[\d,\-]+)?$"
)


def norm_feature(text: str) -> str | None:
    m = FEATURE_ID.search(text)
    return f"W{m.group(1)}-{m.group(2).upper()}{m.group(3)}" if m else None


def feat_from_stem(stem: str) -> str | None:
    m = FEATURE_STEM.match(stem)
    return f"W{m.group(1)}-{m.group(2).upper()}{m.group(3)}" if m else None


def adr_from_stem(stem: str) -> str | None:
    m = ADR_STEM.match(stem)
    return f"ADR-{int(m.group(1)):04d}" if m else None


# --------------------------------------------------------------------------- #
# Graph model (plain dataclasses; no networkx dependency for Layer 1).
# --------------------------------------------------------------------------- #
@dataclass
class Node:
    id: str
    type: str
    label: str = ""
    path: str | None = None  # repo-relative, when backed by a file
    exists: bool = True  # for code nodes: does the referenced file exist?


@dataclass
class Edge:
    src: str
    rel: str
    dst: str


@dataclass
class Graph:
    nodes: dict[str, Node] = field(default_factory=dict)
    edges: list[Edge] = field(default_factory=list)
    _edge_keys: set[tuple[str, str, str]] = field(default_factory=set)

    def node(self, nid: str, ntype: str, *, label: str = "", path: str | None = None,
             exists: bool = True) -> Node:
        n = self.nodes.get(nid)
        if n is None:
            n = Node(id=nid, type=ntype, label=label or nid, path=path, exists=exists)
            self.nodes[nid] = n
        else:  # enrich an on-demand node with better data when we parse its own file
            if label:
                n.label = label
            if path and not n.path:
                n.path = path
        return n

    def edge(self, src: str, rel: str, dst: str) -> None:
        if src == dst:
            return
        key = (src, rel, dst)
        if key not in self._edge_keys:
            self._edge_keys.add(key)
            self.edges.append(Edge(src, rel, dst))


# --------------------------------------------------------------------------- #
# Build
# --------------------------------------------------------------------------- #
def _rel(p: Path) -> str:
    return str(p.relative_to(config.REPO_ROOT))


@functools.lru_cache(maxsize=1)
def _tracked_files() -> tuple[str, ...]:
    """All git-tracked repo paths (deterministic, excludes gitignored junk)."""
    try:
        out = subprocess.check_output(
            ["git", "ls-files"], cwd=config.REPO_ROOT, text=True
        )
    except Exception:
        return ()
    return tuple(out.splitlines())


def _resolve_code(relpath: str) -> tuple[str, bool]:
    """Resolve a doc-referenced code path to a repo-relative file.

    Docs cite paths relative to a service dir (e.g. `src/db/session.py`). Match by
    UNIQUE suffix against tracked files: a single match wins; 0 or >1 (e.g. bare
    `main.py`) stays unresolved (exists=False) rather than guessing.
    """
    if (config.REPO_ROOT / relpath).exists():
        return relpath, True
    needle = "/" + relpath
    hits = [f for f in _tracked_files() if f == relpath or f.endswith(needle)]
    if len(hits) == 1:
        return hits[0], True
    return relpath, False


def _node_id_for_doc(path: Path) -> tuple[str, str]:
    """Map a docs/ markdown file to its (node_id, node_type)."""
    stem = path.stem
    try:
        parent = path.parent.name
    except Exception:
        parent = ""
    if parent == "features":
        fid = feat_from_stem(stem)
        if fid:
            return fid, "feature"
    if parent == "adr":
        aid = adr_from_stem(stem)
        if aid:
            return aid, "adr"
    if parent == "plans":
        return f"plan:{stem}", "plan"
    return f"doc:{_rel(path)}", "doc"


def _first_title(text: str) -> str:
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("# "):
            return line[2:].strip()
    return ""


def build_graph() -> Graph:
    g = Graph()
    docs = config.DOCS_DIR
    if not docs.is_dir():
        raise SystemExit(f"docs dir not found: {docs}")

    md_files = sorted(docs.rglob("*.md"))

    # Pass 1: register a node for every doc file so link targets resolve.
    for f in md_files:
        nid, ntype = _node_id_for_doc(f)
        g.node(nid, ntype, label=nid, path=_rel(f))
        # A plan named w#-f#-* documents that feature even without an explicit link.
        if ntype == "plan":
            fid = feat_from_stem(f.stem)
            if fid:
                g.node(fid, "feature")
                g.edge(fid, "DOCUMENTED_BY", nid)

    # Pass 2: parse contents for edges + evidence.
    for f in md_files:
        nid, ntype = _node_id_for_doc(f)
        text = f.read_text(encoding="utf-8", errors="replace")
        title = _first_title(text)
        if title:
            g.nodes[nid].label = title

        for raw in text.splitlines():
            line = raw.strip()
            low = line.lower()

            # ADR header: "- **Feature:** W4-F1 (...)" → feature DECIDED_BY adr.
            if ntype == "adr" and "**feature:**" in low:
                fid = norm_feature(line)
                if fid:
                    g.node(fid, "feature")
                    g.edge(fid, "DECIDED_BY", nid)

            # Dependency edges (feature docs).
            if "**depends on:**" in low or low.startswith("depends on:"):
                for fid in {norm_feature(m.group(0)) for m in FEATURE_ID.finditer(line)}:
                    if fid and fid != nid:
                        g.node(fid, "feature")
                        g.edge(nid, "DEPENDS_ON", fid)
            if "**unblocks:**" in low or low.startswith("unblocks:"):
                for fid in {norm_feature(m.group(0)) for m in FEATURE_ID.finditer(line)}:
                    if fid and fid != nid:
                        g.node(fid, "feature")
                        g.edge(nid, "UNBLOCKS", fid)

            # Spec reference.
            if "**spec:**" in low:
                sm = SPEC_REF.search(line)
                if sm:
                    sid = f"spec:{sm.group(1)}"
                    g.node(sid, "doc", label=sm.group(1))
                    g.edge(nid, "SPECIFIED_BY", sid)

        # Relative md links anywhere in the file.
        for label, target in MD_LINK.findall(text):
            tpath = (f.parent / target).resolve()
            if not str(tpath).startswith(str(docs.resolve())):
                continue
            if not tpath.exists():
                continue
            tid, ttype = _node_id_for_doc(tpath)
            g.node(tid, ttype, path=_rel(tpath))
            src_type = g.nodes[nid].type
            if ttype == "adr":
                rel = "DECIDED_BY" if src_type == "feature" else "RELATES_TO"
            elif ttype == "plan":
                rel = "DOCUMENTED_BY" if src_type == "feature" else "LINKS_TO"
            else:
                rel = "LINKS_TO"
            g.edge(nid, rel, tid)

        # Inline code-path evidence → code nodes.
        for token in INLINE_CODE.findall(text):
            m = CODE_PATH.match(token.strip())
            if not m:
                continue
            resolved, exists = _resolve_code(m.group(1))
            cid = f"code:{resolved}"
            g.node(cid, "code", label=resolved, path=resolved, exists=exists)
            g.edge(nid, "EVIDENCED_BY", cid)

    return g


# --------------------------------------------------------------------------- #
# `kg.py structure <node>`
# --------------------------------------------------------------------------- #
def normalize_query(arg: str) -> str:
    s = arg.strip()
    if FEATURE_ID.fullmatch(s.upper()):
        return norm_feature(s.upper())
    am = re.fullmatch(r"(?:adr[\s\-]?)?(\d{1,4})", s, re.I)
    if am:
        return f"ADR-{int(am.group(1)):04d}"
    if s.endswith(".md") or "/" in s:
        p = (Path.cwd() / s).resolve()
        if p.exists() and str(p).startswith(str(config.DOCS_DIR.resolve())):
            return _node_id_for_doc(p)[0]
        # maybe a code path
        return f"code:{s}"
    return s


def run_structure(arg: str) -> int:
    g = build_graph()
    nid = normalize_query(arg)
    node = g.nodes.get(nid)
    if node is None:
        # fuzzy: case-insensitive id or label substring
        cand = [n for n in g.nodes.values()
                if n.id.lower() == nid.lower() or arg.lower() in n.label.lower()]
        if len(cand) == 1:
            node = cand[0]
            nid = node.id
        else:
            print(f"no node '{arg}' (resolved '{nid}').")
            if cand:
                print("did you mean:")
                for n in cand[:10]:
                    print(f"  {n.id}  [{n.type}]  {n.label}")
            return 1

    def fmt(target_id: str) -> str:
        t = g.nodes.get(target_id)
        if not t:
            return target_id
        miss = "" if t.exists else "  (MISSING)"
        extra = f"  — {t.label}" if t.label and t.label != t.id else ""
        loc = f"  [{t.path}]" if t.path else ""
        return f"{t.id}{extra}{loc}{miss}"

    print(f"# {node.id}  [{node.type}]")
    if node.label and node.label != node.id:
        print(f"  {node.label}")
    if node.path:
        print(f"  path: {node.path}")

    out: dict[str, list[str]] = {}
    for e in g.edges:
        if e.src == nid:
            out.setdefault(e.rel, []).append(e.dst)
    inc: dict[str, list[str]] = {}
    for e in g.edges:
        if e.dst == nid:
            inc.setdefault(e.rel, []).append(e.src)

    if out:
        print("\n  outgoing:")
        for rel in sorted(out):
            for tid in sorted(set(out[rel])):
                print(f"    -{rel}-> {fmt(tid)}")
    if inc:
        print("\n  incoming:")
        for rel in sorted(inc):
            for sid in sorted(set(inc[rel])):
                print(f"    <-{rel}- {fmt(sid)}")
    if not out and not inc:
        print("\n  (no edges)")
    return 0
