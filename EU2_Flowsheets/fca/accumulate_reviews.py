#!/usr/bin/env python3
"""Run clinical review sub-agent scripts and accumulate results.

Usage:
    # Run sub-agents, accumulate, and QA (does NOT push to clinical_review.csv)
    python accumulate_reviews.py

    # Same, but override config values via CLI
    python accumulate_reviews.py --dir /tmp/claude --count 10

    # Push accumulated CSV to clinical_review.csv (append)
    python accumulate_reviews.py --push

    # Skip running sub-agents, just accumulate existing CSVs and QA
    python accumulate_reviews.py --skip-run

    # Just push (no run, no accumulate)
    python accumulate_reviews.py --skip-run --push
"""
import argparse
import csv
import os
import subprocess
import sys
from collections import Counter
from pathlib import Path

# Import defaults from config (can be overridden via CLI)
from subagent_config import (
    ACCUMULATED_CSV,
    CLINICAL_REVIEW_CSV,
    SUBAGENT_COUNT,
    SUBAGENT_CSV_DIR,
    SUBAGENT_DIR,
    SUBAGENT_PREFIX,
    SUBAGENT_SCRIPT_DIR,
)

HEADER = [
    "source_concept_code", "source_description", "decision",
    "target_concept_id", "target_concept_name",
    "target_vocabulary_id", "target_concept_code",
    "predicate_id", "confidence", "domain_id",
    "qualifier_concept_id", "qualifier_concept_name",
    "qualifier_relationship_id", "mapping_justification",
    "needs_source_data", "mapping_tool", "reviewer_name",
    "reviewer_type", "review_date",
]


def run_subagents(agent_dir, prefix, count, script_dir=None):
    """Execute each sub-agent Python script. Returns list of failures."""
    script_dir = script_dir or agent_dir
    failures = []
    for i in range(1, count + 1):
        script = os.path.join(script_dir, f"{prefix}{i}.py")
        if not os.path.exists(script):
            print(f"  MISSING: {script}")
            failures.append(i)
            continue
        print(f"  Running sub-agent {i}...", end=" ", flush=True)
        result = subprocess.run(
            [sys.executable, script],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            print("FAILED")
            print(f"    stderr: {result.stderr.strip()}")
            failures.append(i)
        else:
            # Show the sub-agent's summary line (last line of stdout)
            lines = result.stdout.strip().splitlines()
            summary = lines[-1] if lines else ""
            print(summary)
    return failures


def accumulate(agent_dir, prefix, count, output_path):
    """Merge sub-agent CSVs into a single accumulated CSV with header."""
    all_rows = []
    for i in range(1, count + 1):
        csv_path = os.path.join(agent_dir, f"{prefix}{i}.csv")
        if not os.path.exists(csv_path):
            print(f"  WARNING: {csv_path} not found, skipping")
            continue
        with open(csv_path, newline="") as f:
            reader = csv.reader(f)
            rows = list(reader)
            # Skip header row if present (check if first field matches)
            if rows and rows[0][0] == HEADER[0]:
                rows = rows[1:]
            all_rows.extend(rows)
        print(f"  Sub-agent {i}: {len(rows)} rows from {csv_path}")

    with open(output_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(HEADER)
        writer.writerows(all_rows)

    print(f"\n  Accumulated {len(all_rows)} rows → {output_path}")
    return all_rows


def qa_check(rows):
    """Run QA checks on accumulated rows. Returns list of issues."""
    issues = []

    # 1. Duplicate source_concept_codes
    codes = [r[0] for r in rows]
    dupes = [code for code, n in Counter(codes).items() if n > 1]
    if dupes:
        issues.append(f"Duplicate source_concept_codes ({len(dupes)}): {dupes[:10]}")

    # 2. Decision breakdown
    decisions = Counter(r[2] for r in rows)
    print(f"\n  Decision breakdown: {dict(decisions)}")

    # 3. Empty source_concept_code
    empty_codes = sum(1 for r in rows if not r[0].strip())
    if empty_codes:
        issues.append(f"Rows with empty source_concept_code: {empty_codes}")

    # 4. Mapped rows missing target_concept_id
    missing_target = [r for r in rows if r[2] == "map" and not r[3].strip()]
    if missing_target:
        issues.append(
            f"Mapped rows missing target_concept_id: {len(missing_target)}"
        )

    # 5. Mapped rows missing predicate_id
    missing_pred = [r for r in rows if r[2] == "map" and not r[7].strip()]
    if missing_pred:
        issues.append(
            f"Mapped rows missing predicate_id: {len(missing_pred)}"
        )

    # 6. Wrong column count
    bad_cols = [
        (i, len(r)) for i, r in enumerate(rows) if len(r) != len(HEADER)
    ]
    if bad_cols:
        issues.append(
            f"Rows with wrong column count (expected {len(HEADER)}): "
            f"{bad_cols[:5]}"
        )

    # 7. Check for codes that already exist in clinical_review.csv
    if os.path.exists(CLINICAL_REVIEW_CSV):
        with open(CLINICAL_REVIEW_CSV, newline="") as f:
            reader = csv.reader(f)
            next(reader, None)  # skip header
            existing_codes = {r[0] for r in reader if r}
        overlap = set(codes) & existing_codes
        if overlap:
            issues.append(
                f"Source codes already in clinical_review.csv ({len(overlap)}): "
                f"{sorted(overlap)[:10]}"
            )

    return issues


def push(accumulated_path, dest_path):
    """Append accumulated rows (no header) to the destination CSV."""
    with open(accumulated_path, newline="") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        rows = list(reader)

    if not rows:
        print("  Nothing to push (0 rows).")
        return

    # Verify dest exists and has matching header
    if os.path.exists(dest_path):
        with open(dest_path, newline="") as f:
            dest_header = next(csv.reader(f), None)
        if dest_header != HEADER:
            print(f"  ERROR: Header mismatch between accumulated and {dest_path}")
            print(f"    Accumulated: {header}")
            print(f"    Destination: {dest_header}")
            return

    with open(dest_path, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerows(rows)

    print(f"  Appended {len(rows)} rows to {dest_path}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dir", default=SUBAGENT_CSV_DIR,
                        help="Directory containing sub-agent CSV output")
    parser.add_argument("--script-dir", default=SUBAGENT_SCRIPT_DIR,
                        help="Directory containing sub-agent Python scripts")
    parser.add_argument("--prefix", default=SUBAGENT_PREFIX,
                        help="Sub-agent filename prefix")
    parser.add_argument("--count", type=int, default=SUBAGENT_COUNT,
                        help="Number of sub-agents")
    parser.add_argument("--output", default=ACCUMULATED_CSV,
                        help="Accumulated CSV output path")
    parser.add_argument("--dest", default=CLINICAL_REVIEW_CSV,
                        help="Final clinical_review.csv path")
    parser.add_argument("--skip-run", action="store_true",
                        help="Skip running sub-agents (just accumulate)")
    parser.add_argument("--push", action="store_true",
                        help="Push accumulated CSV to clinical_review.csv")
    args = parser.parse_args()

    # Step 1: Run sub-agents
    if not args.skip_run:
        print("=== Running sub-agents ===")
        failures = run_subagents(
            args.dir, args.prefix, args.count, script_dir=args.script_dir
        )
        if failures:
            print(f"\n  FAILED sub-agents: {failures}")
            print("  Fix failures before accumulating. Aborting.")
            sys.exit(1)
        print()

    # Step 2: Accumulate
    if not (args.skip_run and args.push):
        print("=== Accumulating ===")
        rows = accumulate(args.dir, args.prefix, args.count, args.output)

        # Step 3: QA
        print("\n=== QA Checks ===")
        issues = qa_check(rows)
        if issues:
            print("\n  ISSUES FOUND:")
            for issue in issues:
                print(f"    - {issue}")
            if args.push:
                print("\n  Blocking push due to QA issues.")
                sys.exit(1)
        else:
            print("  All checks passed.")

    # Step 4: Push
    if args.push:
        print(f"\n=== Pushing to {args.dest} ===")
        push(args.output, args.dest)

    print("\nDone.")


if __name__ == "__main__":
    main()
