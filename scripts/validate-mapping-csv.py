#!/usr/bin/env python3
"""
Validate CVB mapping CSV files against OHDSI-aligned conventions.

Checks:
  1. UTF-8 readable, well-formed CSV
  2. Header normalization via COLUMN_ALIASES
  3. Required columns (warn if missing — some Mappings/ CSVs are non-mapping files)
  4. Row-by-row validation (when required columns present):
     - predicate_id normalization + validation (rejects relatedMatch)
     - confidence in [0, 1]
     - target_concept_id = 0 when noMatch, > 0 otherwise
     - mapping_tool taxonomy (warn, not error)
  5. Duplicate source_concept_code check within file
  6. GitHub Actions ::error annotations

Usage:
    python scripts/validate-mapping-csv.py FILE1.csv [FILE2.csv ...]

Exit code 1 if any errors found, 0 otherwise. Warnings do not cause failure.

Requires only Python stdlib.
"""

import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cvb_constants import (
    REQUIRED_MAPPING_COLUMNS,
    PREDICATE_ALIASES,
    VALID_PREDICATES,
    VALID_MAPPING_TOOLS,
    normalize_column_name,
)

REJECTED_PREDICATES = {"relatedMatch", "skos:relatedMatch"}


def gh_annotation(level, file, line, msg):
    """Emit GitHub Actions annotation."""
    print(f"::{level} file={file},line={line}::{msg}")


def validate_file(filepath):
    """Validate a single CSV file. Returns (error_count, warning_count)."""
    errors = 0
    warnings = 0

    # 1. UTF-8 readable
    try:
        with open(filepath, encoding="utf-8", newline="") as f:
            content = f.read()
    except UnicodeDecodeError:
        gh_annotation("error", filepath, 1, "File is not valid UTF-8")
        return 1, 0

    # 2. Well-formed CSV with header normalization
    try:
        reader = csv.DictReader(content.splitlines())
        if reader.fieldnames is None:
            gh_annotation("error", filepath, 1, "Empty CSV or missing header row")
            return 1, 0
        raw_headers = list(reader.fieldnames)
        normalized_headers = [normalize_column_name(h) for h in raw_headers]
    except csv.Error as e:
        gh_annotation("error", filepath, 1, f"Malformed CSV: {e}")
        return 1, 0

    # 3. Check required columns (warn, not error)
    header_set = set(normalized_headers)
    missing = REQUIRED_MAPPING_COLUMNS - header_set
    if missing:
        gh_annotation(
            "warning", filepath, 1,
            f"Missing required mapping columns (may not be a mapping file): {', '.join(sorted(missing))}"
        )
        warnings += 1
        # Cannot do row-level checks without required columns
        return errors, warnings

    # Build column index mapping (raw header -> normalized)
    col_map = {raw: norm for raw, norm in zip(raw_headers, normalized_headers)}

    # Re-read with normalized headers
    rows = []
    for raw_row in csv.DictReader(content.splitlines()):
        row = {normalize_column_name(k): v for k, v in raw_row.items()}
        rows.append(row)

    # 4. Row-by-row checks
    seen_codes = {}
    has_mapping_tool = "mapping_tool" in header_set

    for i, row in enumerate(rows, start=2):  # line 1 is header
        predicate = (row.get("predicate_id") or "").strip()

        # Reject relatedMatch
        if predicate in REJECTED_PREDICATES:
            gh_annotation("error", filepath, i,
                          f"Rejected predicate '{predicate}' — relatedMatch is not supported")
            errors += 1
            continue

        # Normalize predicate via aliases (strip skos: prefix)
        normalized_pred = PREDICATE_ALIASES.get(predicate, predicate)

        # Validate predicate
        if normalized_pred and normalized_pred not in VALID_PREDICATES:
            gh_annotation("error", filepath, i,
                          f"Invalid predicate_id '{predicate}' (normalized: '{normalized_pred}')")
            errors += 1

        # Confidence check
        confidence_str = (row.get("confidence") or "").strip()
        if confidence_str:
            try:
                conf = float(confidence_str)
                if conf < 0 or conf > 1:
                    gh_annotation("error", filepath, i,
                                  f"confidence={conf} out of range [0, 1]")
                    errors += 1
            except ValueError:
                gh_annotation("error", filepath, i,
                              f"confidence '{confidence_str}' is not a valid number")
                errors += 1

        # target_concept_id consistency with noMatch
        target_str = (row.get("target_concept_id") or "").strip()
        if target_str:
            try:
                target_id = int(float(target_str))  # handle "0.0" etc.
                if normalized_pred == "noMatch" and target_id != 0:
                    gh_annotation("error", filepath, i,
                                  f"noMatch predicate requires target_concept_id=0, got {target_id}")
                    errors += 1
                elif normalized_pred != "noMatch" and normalized_pred in VALID_PREDICATES and target_id == 0:
                    gh_annotation("warning", filepath, i,
                                  f"target_concept_id=0 with predicate '{normalized_pred}' (expected noMatch)")
                    warnings += 1
            except ValueError:
                gh_annotation("error", filepath, i,
                              f"target_concept_id '{target_str}' is not a valid integer")
                errors += 1

        # mapping_tool taxonomy (warn only, column is optional)
        if has_mapping_tool:
            tool = (row.get("mapping_tool") or "").strip()
            if tool and tool not in VALID_MAPPING_TOOLS:
                gh_annotation("warning", filepath, i,
                              f"mapping_tool '{tool}' not in OHDSI taxonomy: {', '.join(sorted(VALID_MAPPING_TOOLS))}")
                warnings += 1

        # 5. Duplicate source_concept_code check
        code = (row.get("source_concept_code") or "").strip()
        if code:
            if code in seen_codes:
                gh_annotation("warning", filepath, i,
                              f"Duplicate source_concept_code '{code}' (first seen line {seen_codes[code]})")
                warnings += 1
            else:
                seen_codes[code] = i

    return errors, warnings


def main():
    if len(sys.argv) < 2:
        print("Usage: validate-mapping-csv.py FILE1.csv [FILE2.csv ...]", file=sys.stderr)
        sys.exit(1)

    total_errors = 0
    total_warnings = 0

    for filepath in sys.argv[1:]:
        if not os.path.isfile(filepath):
            print(f"::warning file={filepath}::File not found, skipping")
            total_warnings += 1
            continue

        errs, warns = validate_file(filepath)
        total_errors += errs
        total_warnings += warns

        status = "PASS" if errs == 0 else "FAIL"
        print(f"{status}: {filepath} ({errs} errors, {warns} warnings)")

    print(f"\nTotal: {total_errors} errors, {total_warnings} warnings across {len(sys.argv) - 1} files")

    sys.exit(1 if total_errors > 0 else 0)


if __name__ == "__main__":
    main()
