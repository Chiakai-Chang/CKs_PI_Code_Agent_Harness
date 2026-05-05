#!/usr/bin/env python3
"""
merge-batch-graphs.py — Merge and normalize batch analysis results.

Combines batch-*.json files from the intermediate directory into a single
assembled graph with normalized IDs, complexity values, and cleaned edges.

Called at the end of Phase 2 of /understand. Phase 3 (ASSEMBLE REVIEW)
then reviews the output for semantic issues the script cannot catch.

Usage:
    python merge-batch-graphs.py <project-root>

Input:
    <project-root>/.understand-anything/intermediate/batch-*.json

Output:
    <project-root>/.understand-anything/intermediate/assembled-graph.json
"""

import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any


# ── Configuration ─────────────────────────────────────────────────────────

VALID_NODE_PREFIXES = {
    "file", "func", "function", "class", "module", "concept",
    "config", "document", "service", "table", "endpoint",
    "pipeline", "schema", "resource",
    "domain", "flow", "step",
}

# node.type → canonical ID prefix
TYPE_TO_PREFIX: dict[str, str] = {
    "file": "file",
    "function": "function",
    "func": "function",
    "class": "class",
    "module": "module",
    "concept": "concept",
    "config": "config",
    "document": "document",
    "service": "service",
    "table": "table",
    "endpoint": "endpoint",
    "pipeline": "pipeline",
    "schema": "schema",
    "resource": "resource",
    "domain": "domain",
    "flow": "flow",
    "step": "step",
}

COMPLEXITY_MAP: dict[str, str] = {
    "low": "simple",
    "easy": "simple",
    "medium": "moderate",
    "intermediate": "moderate",
    "high": "complex",
    "hard": "complex",
    "difficult": "complex",
}

VALID_COMPLEXITY = {"simple", "moderate", "complex"}


def _num(v: Any) -> float:
    """Coerce a value to float for safe comparison (handles string weights)."""
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


# ── Batch loading ─────────────────────────────────────────────────────────

def load_batch(path: Path) -> dict[str, Any] | None:
    """Load a batch JSON file, tolerating malformed files."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        print(f"  Warning: skipping {path.name}: {e}", file=sys.stderr)
        return None

    if not isinstance(data.get("nodes"), list):
        print(f"  Warning: skipping {path.name}: missing or invalid 'nodes' array", file=sys.stderr)
        return None
    if not isinstance(data.get("edges"), list):
        print(f"  Warning: skipping {path.name}: missing or invalid 'edges' array", file=sys.stderr)
        return None

    return data


# ── ID normalization ──────────────────────────────────────────────────────

def classify_id_fix(original: str, corrected: str) -> str:
    """Return a human-readable pattern label for an ID correction."""
    # Double prefix: "file:file:..." → "file:..."
    for prefix in VALID_NODE_PREFIXES:
        if original.startswith(f"{prefix}:{prefix}:"):
            return f"{prefix}:{prefix}: → {prefix}: (double prefix)"

    # Project-name prefix: "my-project:file:..." → "file:..."
    parts = original.split(":")
    if len(parts) >= 3 and parts[0] not in VALID_NODE_PREFIXES and parts[1] in VALID_NODE_PREFIXES:
        return f"<project>:{parts[1]}: → {parts[1]}: (project-name prefix)"

    # Legacy func: → function:
    if original.startswith("func:") and corrected.startswith("function:"):
        return "func: → function: (prefix canonicalization)"

    # Bare path → prefixed
    if not any(original.startswith(f"{p}:") for p in VALID_NODE_PREFIXES):
        prefix = corrected.split(":")[0]
        return f"bare path → {prefix}: (missing prefix)"

    return f"{original} → {corrected}"


def normalize_node_id(node_id: str, node: dict[str, Any]) -> str:
    """Normalize a node ID, returning the corrected version."""
    nid = node_id

    # Strip double prefix: "file:file:src/foo.ts" → "file:src/foo.ts"
    for prefix in VALID_NODE_PREFIXES:
        double = f"{prefix}:{prefix}:"
        if nid.startswith(double):
            nid = nid[len(prefix) + 1:]
            break

    # Strip project-name prefix: "my-project:file:src/foo.ts" → "file:src/foo.ts"
    # Pattern: <word>:<valid-prefix>:<path>
    match = re.match(r"^[^:]+:(" + "|".join(re.escape(p) for p in VALID_NODE_PREFIXES) + r"):(.+)$", nid)
    if match:
        # Only strip if the first segment is NOT a valid prefix itself
        first_seg = nid.split(":")[0]
        if first_seg not in VALID_NODE_PREFIXES:
            nid = f"{match.group(1)}:{match.group(2)}"

    # Canonicalize legacy prefix: func: → function:
    if nid.startswith("func:") and not nid.startswith("function:"):
        nid = "function:" + nid[5:]

    # Add missing prefix for bare file paths
    has_prefix = any(nid.startswith(f"{p}:") for p in VALID_NODE_PREFIXES)
    if not has_prefix:
        node_type = node.get("type", "file")
        prefix = TYPE_TO_PREFIX.get(node_type, "file")
        if node_type in ("function", "class"):
            file_path = node.get("filePath", "")
            name = node.get("name", nid)
            nid = f"{prefix}:{file_path}:{name}" if file_path else f"{prefix}:{nid}"
        else:
            nid = f"{prefix}:{nid}"

    return nid


def normalize_complexity(value: Any) -> tuple[str, str]:
    """Normalize a complexity value. Returns (normalized, status).

    status is one of:
      "valid"    — already a valid value, no change needed
      "mapped"   — known alias, confidently mapped (goes to Fixed report)
      "unknown"  — unrecognized value, defaulted to moderate (goes to Could-not-fix report)
    """
    if isinstance(value, str):
        lower = value.strip().lower()
        if lower in VALID_COMPLEXITY:
            return lower, "valid"
        if lower in COMPLEXITY_MAP:
            return COMPLEXITY_MAP[lower], "mapped"
        # Unknown string — default but flag it
        return "moderate", "unknown"
    elif isinstance(value, (int, float)):
        n = int(value)
        if n <= 3:
            return "simple", "mapped"
        elif n <= 6:
            return "moderate", "mapped"
        else:
            return "complex", "mapped"
    # None or other type — default but flag it
    return "moderate", "unknown"


# ── Main merge + normalize ────────────────────────────────────────────────

def merge_and_normalize(batches: list[dict[str, Any]]) -> tuple[dict[str, Any], list[str]]:
    """Merge batch results and normalize. Returns (assembled_graph, report_lines)."""

    # ── Pattern counters for "Fixed" report ──────────────────────────
    id_fix_patterns: Counter[str] = Counter()
    complexity_fix_patterns: Counter[str] = Counter()

    # ── Detail lists for "Could not fix" report ──────────────────────
    unfixable: list[str] = []

    # ── Step 1: Combine all nodes and edges ──────────────────────────
    all_nodes: list[dict] = []
    all_edges: list[dict] = []
    for batch in batches:
        all_nodes.extend(batch.get("nodes", []))
        all_edges.extend(batch.get("edges", []))

    total_input_nodes = len(all_nodes)
    total_input_edges = len(all_edges)

    # ── Step 2: Normalize node IDs and build ID mapping ──────────────
    id_mapping: dict[str, str] = {}  # original → corrected
    nodes_with_ids: list[dict] = []
    unknown_node_types: Counter[str] = Counter()

    for i, node in enumerate(all_nodes):
        original_id = node.get("id")
        if not original_id:
            unfixable.append(f"Node[{i}] has no 'id' field (name={node.get('name', '?')}, type={node.get('type', '?')})")
            continue

        # Flag unknown node types
        node_type = node.get("type", "")
        if node_type and node_type not in TYPE_TO_PREFIX:
            unknown_node_types[node_type] += 1

        nodes_with_ids.append(node)
        corrected_id = normalize_node_id(original_id, node)
        if corrected_id != original_id:
            pattern = classify_id_fix(original_id, corrected_id)
            id_fix_patterns[pattern] += 1
            id_mapping[original_id] = corrected_id
            node["id"] = corrected_id

    # ── Step 3: Normalize complexity ─────────────────────────────────
    complexity_unknown_patterns: Counter[str] = Counter()

    for node in nodes_with_ids:
        original = node.get("complexity")
        normalized, status = normalize_complexity(original)

        if status == "mapped":
            orig_repr = repr(original) if not isinstance(original, str) else f'"{original}"'
            complexity_fix_patterns[f"{orig_repr} → \"{normalized}\""] += 1
        elif status == "unknown":
            orig_repr = repr(original) if not isinstance(original, str) else f'"{original}"'
            complexity_unknown_patterns[f"complexity {orig_repr} → defaulted to \"moderate\""] += 1

        node["complexity"] = normalized

    # ── Step 4: Rewrite edge references ──────────────────────────────
    edges_rewritten = 0
    for edge in all_edges:
        src = edge.get("source", "")
        tgt = edge.get("target", "")
        new_src = id_mapping.get(src, src)
        new_tgt = id_mapping.get(tgt, tgt)
        if new_src != src or new_tgt != tgt:
            edges_rewritten += 1
            edge["source"] = new_src
            edge["target"] = new_tgt

    # ── Step 5: Deduplicate nodes by ID (keep last) ─────────────────
    duplicate_count = 0
    nodes_by_id: dict[str, dict] = {}
    for node in nodes_with_ids:
        nid = node.get("id", "")
        if nid in nodes_by_id:
            duplicate_count += 1
        nodes_by_id[nid] = node

    # ── Step 6: Deduplicate edges, drop dangling ─────────────────────
    node_ids = set(nodes_by_id.keys())
    edges_by_key: dict[tuple[str, str, str], dict] = {}
    for edge in all_edges:
        src = edge.get("source", "")
        tgt = edge.get("target", "")
        etype = edge.get("type", "")

        if src not in node_ids or tgt not in node_ids:
            missing = []
            if src not in node_ids:
                missing.append(f"source '{src}'")
            if tgt not in node_ids:
                missing.append(f"target '{tgt}'")
            unfixable.append(f"Edge {src} → {tgt} ({etype}): dropped, missing {', '.join(missing)}")
            continue

        key = (src, tgt, etype)
        existing = edges_by_key.get(key)
        if existing is None or _num(edge.get("weight", 0)) > _num(existing.get("weight", 0)):
            edges_by_key[key] = edge

    # ── Build report ─────────────────────────────────────────────────
    report: list[str] = []
    report.append(f"Input: {total_input_nodes} nodes, {total_input_edges} edges")

    # Fixed section — grouped by pattern
    fixed_lines: list[str] = []
    if id_fix_patterns:
        for pattern, count in id_fix_patterns.most_common():
            fixed_lines.append(f"  {count:>4} × {pattern}")
    if complexity_fix_patterns:
        for pattern, count in complexity_fix_patterns.most_common():
            fixed_lines.append(f"  {count:>4} × complexity {pattern}")
    if edges_rewritten:
        fixed_lines.append(f"  {edges_rewritten:>4} × edge references rewritten after ID normalization")
    if duplicate_count:
        fixed_lines.append(f"  {duplicate_count:>4} × duplicate node IDs removed (kept last)")

    if fixed_lines:
        report.append("")
        report.append(f"Fixed ({sum(id_fix_patterns.values()) + sum(complexity_fix_patterns.values()) + edges_rewritten + duplicate_count} corrections):")
        report.extend(fixed_lines)

    # Could not fix section — unknown patterns (grouped) + individual details
    unfixable_total = (
        len(unfixable)
        + sum(complexity_unknown_patterns.values())
        + sum(unknown_node_types.values())
    )
    if unfixable_total:
        report.append("")
        report.append(f"Could not fix ({unfixable_total} issues — needs agent review):")
        # Unknown node types (grouped by count)
        for ntype, count in unknown_node_types.most_common():
            report.append(f"  {count:>4} × unknown node type \"{ntype}\" (not in schema, kept as-is)")
        # Unknown complexity patterns (grouped by count)
        for pattern, count in complexity_unknown_patterns.most_common():
            report.append(f"  {count:>4} × {pattern}")
        # Individual unfixable items
        for detail in unfixable:
            report.append(f"  - {detail}")

    # Output stats
    report.append("")
    report.append(f"Output: {len(nodes_by_id)} nodes, {len(edges_by_key)} edges")

    assembled = {
        "nodes": list(nodes_by_id.values()),
        "edges": list(edges_by_key.values()),
    }

    return assembled, report


# ── Main ──────────────────────────────────────────────────────────────────

def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python merge-batch-graphs.py <project-root>", file=sys.stderr)
        sys.exit(1)

    project_root = Path(sys.argv[1]).resolve()
    intermediate_dir = project_root / ".understand-anything" / "intermediate"

    if not intermediate_dir.is_dir():
        print(f"Error: {intermediate_dir} does not exist", file=sys.stderr)
        sys.exit(1)

    # Discover batch files, sorted by numeric index (not lexicographic)
    batch_files = sorted(
        intermediate_dir.glob("batch-*.json"),
        key=lambda p: int(re.search(r"batch-(\d+)", p.stem).group(1))
        if re.search(r"batch-(\d+)", p.stem)
        else 0,
    )
    if not batch_files:
        print("Error: no batch-*.json files found in intermediate/", file=sys.stderr)
        sys.exit(1)

    print(f"Found {len(batch_files)} batch files:", file=sys.stderr)

    # Load batches
    batches: list[dict[str, Any]] = []
    for f in batch_files:
        batch = load_batch(f)
        if batch is not None:
            batches.append(batch)
            n = len(batch.get("nodes", []))
            e = len(batch.get("edges", []))
            print(f"  {f.name}: {n} nodes, {e} edges", file=sys.stderr)

    if not batches:
        print("Error: no valid batch files loaded", file=sys.stderr)
        sys.exit(1)

    # Merge and normalize
    assembled, report = merge_and_normalize(batches)

    # Print report
    print("", file=sys.stderr)
    for line in report:
        print(line, file=sys.stderr)

    # Write output
    output_path = intermediate_dir / "assembled-graph.json"
    output_path.write_text(json.dumps(assembled, indent=2, ensure_ascii=False), encoding="utf-8")

    size_kb = output_path.stat().st_size / 1024
    print(f"\nWritten to {output_path} ({size_kb:.0f} KB)", file=sys.stderr)


if __name__ == "__main__":
    main()
