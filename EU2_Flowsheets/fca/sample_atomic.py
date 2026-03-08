#!/usr/bin/env python3
"""Draw a 200-item stratified random sample from atomic_enriched.csv.

Stratifies by fca_assessments (proportional to group size, min 1 per non-empty
group up to available budget). Outputs a sample CSV for pilot review.

Usage:
    uv run python -m fca.sample_atomic [--n 200] [--seed 42]
"""
import argparse
import csv
import random
from collections import defaultdict
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
ENRICHED = BASE / "Mappings" / "atomic_enriched.csv"
OUTPUT = BASE / "Mappings" / "atomic_sample_200.csv"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=200, help="Sample size")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    args = parser.parse_args()

    random.seed(args.seed)

    # Group rows by fca_assessments
    groups = defaultdict(list)
    header = None
    with open(ENRICHED) as f:
        reader = csv.DictReader(f)
        header = reader.fieldnames
        for row in reader:
            key = row.get("fca_assessments", "").strip() or "(blank)"
            groups[key].append(row)

    total = sum(len(v) for v in groups.values())
    print(f"Total items: {total}")
    print(f"Assessment groups: {len(groups)}")
    print(f"Target sample size: {args.n}\n")

    # Proportional allocation with min-1 guarantee for non-empty groups
    # (blank) group gets proportional share, not min-1 boosted
    allocations = {}
    remaining = args.n

    # First pass: guarantee 1 per non-blank group (if group has items)
    non_blank = {k: v for k, v in groups.items() if k != "(blank)"}
    guaranteed = min(len(non_blank), args.n // 2)  # cap at half the budget
    for k in sorted(non_blank.keys()):
        allocations[k] = 1
    remaining -= len(non_blank)

    # Second pass: distribute remaining proportionally
    if remaining > 0:
        for k, v in groups.items():
            extra = int(round(len(v) / total * remaining))
            allocations[k] = allocations.get(k, 0) + extra

    # Adjust to hit exact target
    current = sum(allocations.values())
    if current < args.n:
        # Add to largest group
        largest = max(groups.keys(), key=lambda k: len(groups[k]))
        allocations[largest] += args.n - current
    elif current > args.n:
        # Remove from largest group
        largest = max(groups.keys(), key=lambda k: len(groups[k]))
        allocations[largest] -= current - args.n

    # Sample from each group
    sampled = []
    for k in sorted(groups.keys()):
        n_sample = min(allocations.get(k, 0), len(groups[k]))
        if n_sample > 0:
            chosen = random.sample(groups[k], n_sample)
            sampled.extend(chosen)

    # Shuffle final sample
    random.shuffle(sampled)

    # Write output
    with open(OUTPUT, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=header)
        writer.writeheader()
        writer.writerows(sampled)

    # Print summary
    print(f"Sampled: {len(sampled)} items\n")
    print("Allocation by assessment group:")
    print(f"  {'Group':<30} {'Pop':>6} {'Sample':>6}")
    print(f"  {'-'*30} {'-'*6} {'-'*6}")
    for k in sorted(allocations.keys(), key=lambda x: -allocations.get(x, 0)):
        alloc = min(allocations.get(k, 0), len(groups[k]))
        print(f"  {k:<30} {len(groups[k]):>6} {alloc:>6}")

    print(f"\nOutput: {OUTPUT}")


if __name__ == "__main__":
    main()
