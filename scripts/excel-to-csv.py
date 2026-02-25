#!/usr/bin/env python3
"""
Excel-to-CSV converter for CVB mapping spreadsheets.

Reads an .xlsx file, validates required columns are present,
normalizes dates, strips whitespace, and exports UTF-8 CSV.

Usage:
    python scripts/excel-to-csv.py INPUT.xlsx [OUTPUT.csv] [--sheet SHEET_NAME]

If OUTPUT is omitted, writes to the same path with .csv extension.
"""

import argparse
import sys
from pathlib import Path

try:
    import pandas as pd
except ImportError:
    print("ERROR: pandas is required. Install with: pip install pandas openpyxl", file=sys.stderr)
    sys.exit(1)

REQUIRED_COLUMNS = {
    "source_concept_code",
    "source_vocabulary_id",
    "source_description",
    "predicate_id",
    "confidence",
    "target_concept_id",
}

EXPECTED_COLUMNS = [
    "source_concept_code",
    "source_concept_id",
    "source_vocabulary_id",
    "source_domain",
    "source_concept_class_id",
    "source_description",
    "source_description_synonym",
    "relationship_id",
    "predicate_id",
    "confidence",
    "target_concept_id",
    "target_concept_name",
    "target_vocabulary_id",
    "target_domain_id",
    "mapping_justification",
    "author_label",
    "review_date",
    "reviewer_name",
    "reviewer_specialty",
    "status",
]


def normalize_column_name(name: str) -> str:
    """Normalize column names: lowercase, strip, replace spaces with underscores."""
    return name.strip().lower().replace(" ", "_").replace("-", "_")


def convert(input_path: str, output_path: str, sheet_name: str | None = None) -> None:
    """Convert Excel file to normalized CSV."""
    input_file = Path(input_path)
    if not input_file.exists():
        print(f"ERROR: File not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    if not input_file.suffix.lower() in (".xlsx", ".xls"):
        print(f"ERROR: Expected .xlsx or .xls file, got: {input_file.suffix}", file=sys.stderr)
        sys.exit(1)

    # Read Excel
    kwargs = {"engine": "openpyxl"}
    if sheet_name:
        kwargs["sheet_name"] = sheet_name

    df = pd.read_excel(input_path, **kwargs)

    # Normalize column names
    df.columns = [normalize_column_name(c) for c in df.columns]

    # Validate required columns
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        print(f"ERROR: Missing required columns: {', '.join(sorted(missing))}", file=sys.stderr)
        print(f"Found columns: {', '.join(df.columns)}", file=sys.stderr)
        sys.exit(1)

    # Strip whitespace from string columns
    for col in df.select_dtypes(include=["object"]).columns:
        df[col] = df[col].str.strip()

    # Normalize date columns
    date_cols = [c for c in df.columns if "date" in c.lower()]
    for col in date_cols:
        try:
            df[col] = pd.to_datetime(df[col], errors="coerce").dt.strftime("%Y-%m-%d")
        except Exception:
            pass  # Leave as-is if conversion fails

    # Ensure confidence is numeric
    if "confidence" in df.columns:
        df["confidence"] = pd.to_numeric(df["confidence"], errors="coerce")

    # Ensure target_concept_id is integer
    if "target_concept_id" in df.columns:
        df["target_concept_id"] = pd.to_numeric(df["target_concept_id"], errors="coerce").fillna(0).astype(int)

    # Ensure source_concept_id is integer
    if "source_concept_id" in df.columns:
        df["source_concept_id"] = pd.to_numeric(df["source_concept_id"], errors="coerce").fillna(0).astype(int)

    # Reorder columns to match expected order (extras at the end)
    ordered = [c for c in EXPECTED_COLUMNS if c in df.columns]
    extras = [c for c in df.columns if c not in EXPECTED_COLUMNS]
    df = df[ordered + extras]

    # Drop completely empty rows
    df = df.dropna(how="all")

    # Write CSV
    df.to_csv(output_path, index=False, encoding="utf-8")

    print(f"Converted {len(df)} rows")
    print(f"Columns: {', '.join(df.columns)}")
    print(f"Output: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Convert Excel mapping file to CSV")
    parser.add_argument("input", help="Input .xlsx file")
    parser.add_argument("output", nargs="?", help="Output .csv file (default: same name with .csv)")
    parser.add_argument("--sheet", help="Sheet name to read (default: first sheet)")

    args = parser.parse_args()

    output = args.output or str(Path(args.input).with_suffix(".csv"))

    convert(args.input, output, args.sheet)


if __name__ == "__main__":
    main()
