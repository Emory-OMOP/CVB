#!/usr/bin/env python3
"""
Validate CVB mapping CSV files against OHDSI-aligned conventions.

Checks:
  1. UTF-8 readable, well-formed CSV
  2. Header normalization via COLUMN_ALIASES
  3. Required columns (warn if missing — some Mappings/ CSVs are non-mapping files)
  4. Column registration (warn): canonical columns present; extras beyond the
     canonical 21 are registered in KNOWN_EXTENSION_COLUMNS
  5. Row-by-row validation (when required columns present):
     - predicate_id normalization + validation (rejects relatedMatch)
     - confidence in [0, 1]
     - target_concept_id = 0 when noMatch, > 0 otherwise
     - mapping_tool taxonomy (warn, not error)
     - extension dates parseable ISO, valid_start_date <= valid_end_date
     - extension frequency numeric
  6. Duplicate row-identity check within file (error)
  7. GitHub Actions ::error annotations

Usage:
    python scripts/validate-mapping-csv.py FILE1.csv [FILE2.csv ...]

Exit code 1 if any errors found, 0 otherwise. Warnings do not cause failure.

Requires only Python stdlib.
"""

import csv
import os
import sys
from datetime import date, datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cvb_constants import (
    REQUIRED_MAPPING_COLUMNS,
    EXPECTED_COLUMNS,
    KNOWN_EXTENSION_COLUMNS,
    DATE_EXTENSION_COLUMNS,
    DATE_RANGE_PAIRS,
    NUMERIC_EXTENSION_COLUMNS,
    ROW_IDENTITY_COLUMNS,
    PREDICATE_ALIASES,
    VALID_PREDICATES,
    VALID_MAPPING_TOOLS,
    normalize_column_name,
)

REJECTED_PREDICATES = {"relatedMatch", "skos:relatedMatch"}


def gh_annotation(level, file, line, msg):
    """Emit GitHub Actions annotation."""
    print(f"::{level} file={file},line={line}::{msg}")


def parse_iso_date(value):
    """Parse an ISO date, tolerating a trailing time component. None if unparseable."""
    try:
        return date.fromisoformat(value)
    except ValueError:
        pass
    try:
        return datetime.fromisoformat(value).date()
    except ValueError:
        return None


def normalize_target_id(value):
    """Canonical form of target_concept_id for identity comparison ('0.0' -> '0')."""
    try:
        return str(int(float(value)))
    except ValueError:
        return value


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

    # 4. Column registration (warn only — neither case blocks a curator's PR)
    missing_canonical = [c for c in EXPECTED_COLUMNS if c not in header_set]
    if missing_canonical:
        gh_annotation(
            "warning", filepath, 1,
            f"Missing canonical columns: {', '.join(missing_canonical)}"
        )
        warnings += 1

    unregistered = sorted(header_set - set(EXPECTED_COLUMNS) - KNOWN_EXTENSION_COLUMNS)
    if unregistered:
        gh_annotation(
            "warning", filepath, 1,
            f"Unregistered extension columns (dropped at release; register in "
            f"cvb_constants.KNOWN_EXTENSION_COLUMNS): {', '.join(unregistered)}"
        )
        warnings += 1

    # Re-read with normalized headers
    rows = []
    for raw_row in csv.DictReader(content.splitlines()):
        row = {normalize_column_name(k): v for k, v in raw_row.items()}
        rows.append(row)

    # 5. Row-by-row checks
    seen_identities = {}
    has_mapping_tool = "mapping_tool" in header_set
    date_cols = [c for c in DATE_EXTENSION_COLUMNS if c in header_set]
    date_pairs = [(s, e) for s, e in DATE_RANGE_PAIRS if s in header_set and e in header_set]
    numeric_cols = [c for c in NUMERIC_EXTENSION_COLUMNS if c in header_set]

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

        # Extension dates: parseable ISO
        parsed_dates = {}
        for col in date_cols:
            raw_value = (row.get(col) or "").strip()
            if not raw_value:
                continue
            parsed = parse_iso_date(raw_value)
            if parsed is None:
                gh_annotation("error", filepath, i,
                              f"{col} '{raw_value}' is not a parseable ISO date (expected YYYY-MM-DD)")
                errors += 1
            else:
                parsed_dates[col] = parsed

        # Extension dates: start <= end
        for start_col, end_col in date_pairs:
            start, end = parsed_dates.get(start_col), parsed_dates.get(end_col)
            if start and end and start > end:
                gh_annotation("error", filepath, i,
                              f"{start_col} {start} is after {end_col} {end}")
                errors += 1

        # Extension frequency: numeric
        for col in numeric_cols:
            freq = (row.get(col) or "").strip()
            if not freq:
                continue
            try:
                float(freq)
            except ValueError:
                gh_annotation("error", filepath, i,
                              f"{col} '{freq}' is not a valid number")
                errors += 1

        # 6. Duplicate row-identity check. Identity is the full tuple: repeating a
        # source code is legitimate (multi-mapping; *_VAL rows are keyed by
        # description). Only a fully identical tuple is a duplicate.
        identity = tuple(
            normalize_target_id((row.get(col) or "").strip())
            if col == "target_concept_id"
            else (row.get(col) or "").strip()
            for col in ROW_IDENTITY_COLUMNS
        )
        if any(identity):
            if identity in seen_identities:
                gh_annotation(
                    "error", filepath, i,
                    f"Duplicate row identity {ROW_IDENTITY_COLUMNS} = {identity} "
                    f"(first seen line {seen_identities[identity]})"
                )
                errors += 1
            else:
                seen_identities[identity] = i

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
