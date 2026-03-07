#!/usr/bin/env python3
"""Validate clinical_review.csv source codes against unmappable_enriched.csv.

Checks:
1. Every source_concept_code in clinical_review.csv exists in unmappable_enriched.csv
2. The source_description matches (catches off-by-one code errors)
3. Reports mismatches with the likely correct code

Usage:
    python validate_review_codes.py
    python validate_review_codes.py --review /path/to/clinical_review.csv
    python validate_review_codes.py --fix   # write corrected CSV
"""
import argparse
import csv
import sys
from pathlib import Path

MAPPINGS_DIR = Path(__file__).resolve().parent.parent / "Mappings"
DEFAULT_REVIEW = MAPPINGS_DIR / "clinical_review.csv"
DEFAULT_ENRICHED = MAPPINGS_DIR / "unmappable_enriched.csv"


def load_enriched(path):
    """Build two lookups from the enriched CSV:
    - code_to_desc: {source_code: source_description}
    - desc_to_code: {normalized_description: source_code}
    """
    code_to_desc = {}
    desc_to_codes = {}
    with open(path, newline="") as f:
        reader = csv.reader(f)
        header = next(reader)
        code_col = 0  # source_concept_code
        desc_col = 1  # source_description
        for row in reader:
            if len(row) < 2:
                continue
            code = row[code_col].strip()
            desc = row[desc_col].strip()
            code_to_desc[code] = desc
            desc_to_codes.setdefault(desc, []).append(code)
    return code_to_desc, desc_to_codes


def validate(review_path, enriched_path):
    code_to_desc, desc_to_codes = load_enriched(enriched_path)

    issues = []
    ok = 0

    with open(review_path, newline="") as f:
        reader = csv.reader(f)
        header = next(reader)
        for line_num, row in enumerate(reader, start=2):
            if len(row) < 2:
                continue
            review_code = row[0].strip()
            review_desc = row[1].strip()

            if review_code not in code_to_desc:
                # Code doesn't exist at all — try to find by description
                candidates = desc_to_codes.get(review_desc, [])
                issues.append({
                    "line": line_num,
                    "type": "missing_code",
                    "review_code": review_code,
                    "review_desc": review_desc,
                    "expected_desc": None,
                    "candidate_codes": candidates,
                })
            elif code_to_desc[review_code] != review_desc:
                # Code exists but description doesn't match
                actual_desc = code_to_desc[review_code]
                candidates = desc_to_codes.get(review_desc, [])
                issues.append({
                    "line": line_num,
                    "type": "desc_mismatch",
                    "review_code": review_code,
                    "review_desc": review_desc,
                    "expected_desc": actual_desc,
                    "candidate_codes": candidates,
                })
            else:
                ok += 1

    return issues, ok


def print_report(issues, ok):
    total = ok + len(issues)
    print(f"Validated {total} rows: {ok} OK, {len(issues)} issues\n")

    if not issues:
        print("All source codes validated successfully.")
        return

    by_type = {}
    for issue in issues:
        by_type.setdefault(issue["type"], []).append(issue)

    if "missing_code" in by_type:
        group = by_type["missing_code"]
        print(f"=== Missing codes ({len(group)}) ===")
        print("Code in review doesn't exist in enriched CSV.\n")
        for iss in group:
            print(f"  Line {iss['line']}: code={iss['review_code']}")
            print(f"    desc: {iss['review_desc'][:80]}")
            if iss["candidate_codes"]:
                print(f"    likely correct code: {iss['candidate_codes']}")
            else:
                print(f"    NO match found by description")
            print()

    if "desc_mismatch" in by_type:
        group = by_type["desc_mismatch"]
        print(f"=== Description mismatches ({len(group)}) ===")
        print("Code exists but description doesn't match (off-by-one?).\n")
        for iss in group:
            print(f"  Line {iss['line']}: code={iss['review_code']}")
            print(f"    review says: {iss['review_desc'][:80]}")
            print(f"    enriched has: {iss['expected_desc'][:80]}")
            if iss["candidate_codes"]:
                print(f"    likely correct code: {iss['candidate_codes']}")
            print()


def write_fixed(review_path, enriched_path, output_path):
    """Write a corrected CSV, auto-fixing codes where description match is unambiguous."""
    code_to_desc, desc_to_codes = load_enriched(enriched_path)

    fixed_count = 0
    unfixed = []

    with open(review_path, newline="") as f:
        reader = csv.reader(f)
        header = next(reader)
        rows = list(reader)

    for i, row in enumerate(rows):
        if len(row) < 2:
            continue
        review_code = row[0].strip()
        review_desc = row[1].strip()

        if review_code in code_to_desc and code_to_desc[review_code] == review_desc:
            continue  # already correct

        candidates = desc_to_codes.get(review_desc, [])
        if len(candidates) == 1:
            row[0] = candidates[0]
            fixed_count += 1
        elif len(candidates) > 1:
            unfixed.append((i + 2, review_code, review_desc, candidates))
        else:
            unfixed.append((i + 2, review_code, review_desc, []))

    with open(output_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)

    print(f"Auto-fixed {fixed_count} codes → {output_path}")
    if unfixed:
        print(f"\n{len(unfixed)} rows could NOT be auto-fixed:")
        for line, code, desc, cands in unfixed:
            print(f"  Line {line}: code={code}, candidates={cands}")
            print(f"    desc: {desc[:80]}")


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--review", default=str(DEFAULT_REVIEW),
                        help="Path to clinical_review.csv")
    parser.add_argument("--enriched", default=str(DEFAULT_ENRICHED),
                        help="Path to unmappable_enriched.csv")
    parser.add_argument("--fix", action="store_true",
                        help="Write auto-corrected CSV")
    parser.add_argument("--fix-output",
                        help="Output path for fixed CSV (default: <review>_fixed.csv)")
    args = parser.parse_args()

    if args.fix:
        output = args.fix_output or args.review.replace(".csv", "_fixed.csv")
        write_fixed(args.review, args.enriched, output)
    else:
        issues, ok = validate(args.review, args.enriched)
        print_report(issues, ok)

    return 0 if not args.fix else 0


if __name__ == "__main__":
    sys.exit(main())
