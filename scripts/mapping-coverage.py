#!/usr/bin/env python3
"""
Generate a mapping coverage dashboard (COVERAGE.md) for CVB vocabularies.

Discovers vocab directories with Mappings/ subdirectories, analyzes each
mapping CSV, and produces a summary report.

Usage:
    python scripts/mapping-coverage.py [VOCAB_NAME ...]

If no vocab names are given, all vocabs are scanned (excluding _TEMPLATE).

Requires only Python stdlib. Imports shared constants from cvb_constants.py.
"""

import csv
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cvb_constants import (
    REQUIRED_MAPPING_COLUMNS,
    PREDICATE_ALIASES,
    VALID_PREDICATES,
    normalize_column_name,
)


def git_last_modified(filepath):
    """Get last modified date from git log."""
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%ci", "--", filepath],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip().split(" ")[0]  # YYYY-MM-DD
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return "unknown"


def analyze_csv(filepath):
    """Analyze a mapping CSV file. Returns dict of stats or None if not a mapping file."""
    try:
        with open(filepath, encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            if reader.fieldnames is None:
                return None

            headers = {normalize_column_name(h) for h in reader.fieldnames}
            if not REQUIRED_MAPPING_COLUMNS.issubset(headers):
                return None

            rows = []
            for raw_row in reader:
                row = {normalize_column_name(k): v for k, v in raw_row.items()}
                rows.append(row)
    except (UnicodeDecodeError, csv.Error):
        return None

    if not rows:
        return {"total": 0, "mapped": 0, "unmapped": 0, "coverage": 0.0,
                "predicates": {}, "confidence": {},
                "metadata_completeness": {
                    "mapping_tool": {"count": 0, "total": 0},
                    "mapper": {"count": 0, "total": 0},
                    "reviewer": {"count": 0, "total": 0},
                },
                "top_unmapped": []}

    total = len(rows)
    predicate_counts = {}
    confidences = []
    has_tool = 0
    has_mapper = 0
    has_reviewer = 0
    mapped = 0
    unmapped = 0
    has_frequency = "ws_frequency" in headers

    for row in rows:
        pred = (row.get("predicate_id") or "").strip()
        pred = PREDICATE_ALIASES.get(pred, pred)

        predicate_counts[pred] = predicate_counts.get(pred, 0) + 1

        if pred == "noMatch":
            unmapped += 1
        else:
            mapped += 1

        conf_str = (row.get("confidence") or "").strip()
        if conf_str:
            try:
                confidences.append(float(conf_str))
            except ValueError:
                pass

        if (row.get("mapping_tool") or "").strip():
            has_tool += 1
        if (row.get("author_label") or row.get("mapper") or "").strip():
            has_mapper += 1
        if (row.get("reviewer_name") or row.get("reviewer") or "").strip():
            has_reviewer += 1

    coverage = round(mapped / total * 100, 1) if total > 0 else 0.0

    confidence_stats = {}
    if confidences:
        confidence_stats = {
            "mean": round(sum(confidences) / len(confidences), 2),
            "min": round(min(confidences), 2),
            "max": round(max(confidences), 2),
        }

    metadata_completeness = {
        "mapping_tool": {"count": has_tool, "total": total},
        "mapper": {"count": has_mapper, "total": total},
        "reviewer": {"count": has_reviewer, "total": total},
    }

    # Top unmapped items by workspace frequency (if ws_frequency column present)
    top_unmapped = []
    if has_frequency:
        unmapped_rows = []
        for row in rows:
            pred = (row.get("predicate_id") or "").strip()
            pred = PREDICATE_ALIASES.get(pred, pred)
            if pred == "noMatch":
                freq_str = (row.get("ws_frequency") or "0").strip()
                try:
                    freq = int(float(freq_str))
                except ValueError:
                    freq = 0
                unmapped_rows.append({
                    "code": (row.get("source_concept_code") or "").strip(),
                    "description": (row.get("source_description") or "").strip()[:60],
                    "frequency": freq,
                    "status": (row.get("status") or "").strip(),
                })
        unmapped_rows.sort(key=lambda r: r["frequency"], reverse=True)
        top_unmapped = unmapped_rows[:20]

    return {
        "total": total,
        "mapped": mapped,
        "unmapped": unmapped,
        "coverage": coverage,
        "predicates": predicate_counts,
        "confidence": confidence_stats,
        "metadata_completeness": metadata_completeness,
        "top_unmapped": top_unmapped,
    }


def discover_vocabs(repo_dir, filter_names=None):
    """Discover vocab directories with Mappings/ subdirs."""
    vocabs = []
    for entry in sorted(os.listdir(repo_dir)):
        if entry.startswith(("_", ".")):
            continue
        mappings_dir = os.path.join(repo_dir, entry, "Mappings")
        if os.path.isdir(mappings_dir):
            if filter_names and entry not in filter_names:
                continue
            vocabs.append(entry)
    return vocabs


def build_json(repo_dir, vocabs):
    """Build a JSON-serializable dict of all coverage data."""
    generated = subprocess.run(
        ["date", "+%Y-%m-%d"], capture_output=True, text=True,
    ).stdout.strip()

    vocab_data = []
    grand_total = grand_mapped = grand_unmapped = 0

    for vocab in vocabs:
        mappings_dir = os.path.join(repo_dir, vocab, "Mappings")
        csv_files = sorted(
            f for f in os.listdir(mappings_dir) if f.lower().endswith(".csv")
        )

        files = []
        v_total = v_mapped = v_unmapped = 0

        for csv_file in csv_files:
            filepath = os.path.join(mappings_dir, csv_file)
            stats = analyze_csv(filepath)
            if stats is None:
                continue

            v_total += stats["total"]
            v_mapped += stats["mapped"]
            v_unmapped += stats["unmapped"]

            files.append({
                "filename": csv_file,
                "last_modified": git_last_modified(filepath),
                **stats,
            })

        grand_total += v_total
        grand_mapped += v_mapped
        grand_unmapped += v_unmapped

        vocab_data.append({
            "name": vocab,
            "files": files,
            "totals": {
                "total": v_total,
                "mapped": v_mapped,
                "unmapped": v_unmapped,
                "coverage": round(v_mapped / v_total * 100, 1) if v_total else 0.0,
            },
            "source_mappings": [
                {
                    "file": csv_file_info["filename"],
                    "url": f"https://github.com/Emory-OMOP/CVB/blob/main/{vocab}/Mappings/{csv_file_info['filename']}",
                }
                for csv_file_info in files
            ],
        })

    return {
        "generated": generated,
        "summary": {
            "total_vocabs": len(vocabs),
            "total_rows": grand_total,
            "total_mapped": grand_mapped,
            "total_unmapped": grand_unmapped,
            "overall_coverage": round(grand_mapped / grand_total * 100, 1) if grand_total else 0.0,
        },
        "vocabs": vocab_data,
    }


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_dir = os.path.dirname(script_dir)

    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = {a for a in sys.argv[1:] if a.startswith("--")}
    output_json = "--json" in flags

    filter_names = set(args) if args else None
    vocabs = discover_vocabs(repo_dir, filter_names)

    if not vocabs:
        print("No vocabularies found with Mappings/ directories.", file=sys.stderr)
        sys.exit(1)

    lines = [
        "# CVB Mapping Coverage Dashboard",
        "",
        f"*Generated on {subprocess.run(['date', '+%Y-%m-%d'], capture_output=True, text=True).stdout.strip()}*",
        "",
    ]

    for vocab in vocabs:
        mappings_dir = os.path.join(repo_dir, vocab, "Mappings")
        csv_files = sorted(
            f for f in os.listdir(mappings_dir)
            if f.lower().endswith(".csv")
        )

        lines.append(f"## {vocab}")
        lines.append("")

        if not csv_files:
            lines.append("*No CSV files found.*")
            lines.append("")
            continue

        for csv_file in csv_files:
            filepath = os.path.join(mappings_dir, csv_file)
            stats = analyze_csv(filepath)
            last_mod = git_last_modified(filepath)

            if stats is None:
                lines.append(f"### {csv_file}")
                lines.append(f"*Not a mapping file (missing required columns)* | Last modified: {last_mod}")
                lines.append("")
                continue

            lines.append(f"### {csv_file}")
            lines.append(f"Last modified: {last_mod}")
            lines.append("")
            lines.append(f"| Metric | Value |")
            lines.append(f"|--------|-------|")
            lines.append(f"| Total rows | {stats['total']} |")
            lines.append(f"| Mapped | {stats['mapped']} |")
            lines.append(f"| Unmapped (noMatch) | {stats['unmapped']} |")
            lines.append(f"| Coverage | {stats['coverage']:.1f}% |")
            lines.append("")

            if stats["predicates"]:
                lines.append("**Predicate distribution:**")
                lines.append("")
                lines.append("| Predicate | Count |")
                lines.append("|-----------|-------|")
                for pred, count in sorted(stats["predicates"].items()):
                    lines.append(f"| {pred} | {count} |")
                lines.append("")

            if stats["confidence"]:
                c = stats["confidence"]
                lines.append(f"**Confidence:** mean={c['mean']:.2f}, min={c['min']:.2f}, max={c['max']:.2f}")
                lines.append("")

            mc = stats["metadata_completeness"]
            lines.append("**Metadata completeness:**")
            lines.append("")
            lines.append("| Field | Coverage |")
            lines.append("|-------|----------|")
            for field in ("mapping_tool", "mapper", "reviewer"):
                m = mc[field]
                pct = (m["count"] / m["total"] * 100) if m["total"] else 0
                lines.append(f"| {field} | {m['count']}/{m['total']} ({pct:.0f}%) |")
            lines.append("")

            if stats.get("top_unmapped"):
                lines.append("**Top unmapped items by frequency:**")
                lines.append("")
                lines.append("| Code | Description | Frequency | Status |")
                lines.append("|------|-------------|-----------|--------|")
                for item in stats["top_unmapped"]:
                    freq_fmt = f"{item['frequency']:,}"
                    lines.append(f"| {item['code']} | {item['description']} | {freq_fmt} | {item['status']} |")
                lines.append("")

    # Write COVERAGE.md
    output_path = os.path.join(repo_dir, "COVERAGE.md")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print(f"Coverage report written to: {output_path}")
    print(f"Vocabularies analyzed: {', '.join(vocabs)}")

    # Write JSON if requested
    if output_json:
        json_data = build_json(repo_dir, vocabs)
        json_path = os.path.join(repo_dir, "coverage-data.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(json_data, f, indent=2)
        print(f"JSON data written to: {json_path}")


if __name__ == "__main__":
    main()
