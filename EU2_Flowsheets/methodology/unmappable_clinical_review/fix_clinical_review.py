#!/usr/bin/env python3
"""Fix all known issues in clinical_review.csv:

1. Merged code+description fields (commas in descriptions caused bad quoting)
2. Off-by-one source code errors (verified against enriched CSV)
3. Cosmetic description mismatches (trailing *, encoding, extra spaces, truncation)

Usage:
    # Dry run — show what would change
    python fix_clinical_review.py

    # Apply fixes in-place
    python fix_clinical_review.py --apply
"""
import argparse
import csv
import re
import sys
from pathlib import Path

MAPPINGS_DIR = Path(__file__).resolve().parent.parent / "Mappings"
REVIEW_PATH = MAPPINGS_DIR / "clinical_review.csv"
ENRICHED_PATH = MAPPINGS_DIR / "unmappable_enriched.csv"


def load_enriched(path):
    code_to_desc = {}
    desc_to_codes = {}
    with open(path, newline="") as f:
        reader = csv.reader(f)
        next(reader)  # skip header
        for row in reader:
            if len(row) < 2:
                continue
            code = row[0].strip()
            desc = row[1].strip()
            code_to_desc[code] = desc
            desc_to_codes.setdefault(desc, []).append(code)
    return code_to_desc, desc_to_codes


def fix_merged_field(field_value):
    """Detect and split a merged code+description field.

    Pattern: the field looks like '11355,"9. When I am talking..."'
    where code and description got concatenated with a comma.
    """
    # Match: digits, comma, then the rest (with possible surrounding quotes)
    m = re.match(r'^(\d+),\s*"?(.+?)"?$', field_value)
    if m:
        return m.group(1), m.group(2)
    # Also handle without quotes
    m = re.match(r'^(\d+),(.+)$', field_value)
    if m and not m.group(2).strip().startswith(("map", "skip", "flag")):
        return m.group(1), m.group(2).strip()
    return None, None


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true",
                        help="Apply fixes in-place")
    args = parser.parse_args()

    code_to_desc, desc_to_codes = load_enriched(ENRICHED_PATH)

    with open(REVIEW_PATH, newline="") as f:
        reader = csv.reader(f)
        header = next(reader)
        rows = list(reader)

    fixes = []

    for i, row in enumerate(rows):
        line_num = i + 2
        if len(row) < 3:
            continue

        original_code = row[0].strip()
        original_desc = row[1].strip()

        # --- Fix 1: Merged code+description fields ---
        # Detection: code field contains a comma (merged with description)
        # and the description field is a decision value
        if row[1].strip() in ("map", "skip", "flag") or "," in row[0]:
            split_code, split_desc = fix_merged_field(row[0])
            if split_code:
                # The row is shifted: col0=merged, col1=decision, col2+=rest
                # We need to unshift: insert the split desc as col1,
                # but the decision is currently in col1
                new_row = [split_code, split_desc] + row[1:]
                # Trim to correct column count (the merge ate one column,
                # so there's one fewer than expected — pad if needed)
                while len(new_row) < len(header):
                    new_row.append("")
                new_row = new_row[:len(header)]
                fixes.append({
                    "line": line_num,
                    "type": "merged_field",
                    "old_code": row[0][:60],
                    "new_code": split_code,
                    "new_desc": split_desc[:60],
                })
                rows[i] = new_row
                original_code = split_code
                original_desc = split_desc

        # --- Fix 2: Off-by-one / wrong source codes ---
        if original_code not in code_to_desc:
            candidates = desc_to_codes.get(original_desc, [])
            if len(candidates) == 1:
                fixes.append({
                    "line": line_num,
                    "type": "wrong_code",
                    "old_code": original_code,
                    "new_code": candidates[0],
                    "desc": original_desc[:60],
                })
                rows[i][0] = candidates[0]
            elif len(candidates) > 1:
                fixes.append({
                    "line": line_num,
                    "type": "ambiguous_code",
                    "old_code": original_code,
                    "candidates": candidates,
                    "desc": original_desc[:60],
                })
        elif code_to_desc[original_code] != original_desc:
            # --- Fix 3: Cosmetic description mismatches ---
            correct_desc = code_to_desc[original_code]
            fixes.append({
                "line": line_num,
                "type": "desc_mismatch",
                "code": original_code,
                "old_desc": original_desc[:60],
                "new_desc": correct_desc[:60],
            })
            rows[i][1] = correct_desc

    # Report
    by_type = {}
    for fix in fixes:
        by_type.setdefault(fix["type"], []).append(fix)

    print(f"Total fixes: {len(fixes)}\n")

    if "merged_field" in by_type:
        group = by_type["merged_field"]
        print(f"=== Merged code+description fields: {len(group)} ===")
        for f in group:
            print(f"  Line {f['line']}: {f['old_code'][:50]} → code={f['new_code']}, desc={f['new_desc']}")
        print()

    if "wrong_code" in by_type:
        group = by_type["wrong_code"]
        print(f"=== Wrong source codes (auto-fixable): {len(group)} ===")
        for f in group:
            print(f"  Line {f['line']}: {f['old_code']} → {f['new_code']} ({f['desc']})")
        print()

    if "ambiguous_code" in by_type:
        group = by_type["ambiguous_code"]
        print(f"=== Ambiguous codes (MANUAL review needed): {len(group)} ===")
        for f in group:
            print(f"  Line {f['line']}: {f['old_code']} candidates={f['candidates']} ({f['desc']})")
        print()

    if "desc_mismatch" in by_type:
        group = by_type["desc_mismatch"]
        print(f"=== Description normalization: {len(group)} ===")
        for f in group:
            print(f"  Line {f['line']}: code={f['code']}")
            print(f"    old: {f['old_desc']}")
            print(f"    new: {f['new_desc']}")
        print()

    if args.apply:
        with open(REVIEW_PATH, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(header)
            writer.writerows(rows)
        print(f"Applied {len(fixes)} fixes to {REVIEW_PATH}")
    else:
        print("Dry run — use --apply to write changes.")


if __name__ == "__main__":
    main()
