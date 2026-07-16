#!/usr/bin/env python3
"""
Emit the release artifact for a CVB mapping sheet: the canonical 21 SSSOM
columns plus the registered date extensions (cvb_constants.RELEASE_COLUMNS),
as quoted CSV for the Athena external table omop_etl.src_mapping_sssom.

This is the seam between the sheet and the warehouse. Three widths exist and
they are all prefixes of the same sheet — see EU1_CDW/README.md:

    1-21  canonical      -> Postgres Builder staging (trim-csv-columns.py)
    1-23  release        -> omop_etl.src_mapping_sssom (this script)
    1-24  sheet          -> git, curators

Columns are selected BY NAME, not by position, so a sheet whose extension
columns drifted inward (EU2_Flowsheets puts ws_frequency at 21) still releases
correctly rather than silently shifting.

Serde contract — the external table reads OpenCSVSerde with
quoteChar='"' and escapeChar='\\', so this script:
  - quotes every field (QUOTE_ALL), keeping the header row for
    skip.header.line.count=1;
  - doubles backslashes, which opencsv un-escapes back to one;
  - refuses embedded newlines, which a line-oriented serde cannot represent.
The legacy manual ingest used LazySimpleSerDe and column-shifted 1,644 rows on
embedded commas alone (ADR audit finding 2). That must not recur silently.

Two escape mechanisms are in play here deliberately, and they are not
interchangeable — do not "simplify" one into the other:

    embedded quote      "  ->  ""      (RFC4180 doubling, via QUOTE_ALL)
    embedded backslash  \  ->  \\      (escapeChar, via escape_for_opencsv)

opencsv accepts both: inside a quoted field it treats a doubled quote as one
literal quote, and it un-escapes '\\' to one backslash. Collapsing to a single
mechanism breaks the other case — emitting \" for quotes would leave the
doubled-quote path unhandled, and dropping the backslash doubling would let a
description ending in '\' escape its own closing quote and shift every
subsequent column. That is the exact 1,644-row failure this file exists to
prevent. Verified by round-trip in /tmp/claude/verify-release-artifact.sh.

Usage:
    python scripts/package-mapping-release.py INPUT.csv OUTPUT.csv

Exit code 1 on error. Requires only Python stdlib.
"""

import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cvb_constants import RELEASE_COLUMNS, normalize_column_name

# A 255-char description with a pathological quote run is still nowhere near
# this; the limit only stops a runaway field from wedging the csv reader.
csv.field_size_limit(1024 * 1024)


def escape_for_opencsv(value):
    """Escape a field for OpenCSVSerde. Doubling '\\' is what opencsv un-escapes."""
    return value.replace("\\", "\\\\")


def package(input_path, output_path):
    """Write the release artifact. Returns an error count."""
    errors = 0

    with open(input_path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            print(f"ERROR: {input_path} is empty or has no header row", file=sys.stderr)
            return 1

        normalized = [normalize_column_name(h) for h in reader.fieldnames]
        missing = [c for c in RELEASE_COLUMNS if c not in normalized]
        if missing:
            print(
                f"ERROR: {input_path} is missing release columns: {', '.join(missing)}",
                file=sys.stderr,
            )
            return 1

        rows = []
        for line_no, raw_row in enumerate(reader, start=2):
            row = {normalize_column_name(k): (v or "") for k, v in raw_row.items()}
            out_row = []
            for col in RELEASE_COLUMNS:
                value = row[col]
                if "\n" in value or "\r" in value:
                    print(
                        f"ERROR: {input_path}:{line_no}: {col} contains an embedded "
                        f"newline, which OpenCSVSerde cannot read",
                        file=sys.stderr,
                    )
                    errors += 1
                    value = value.replace("\r", " ").replace("\n", " ")
                out_row.append(escape_for_opencsv(value))
            rows.append(out_row)

    if errors:
        return errors

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, quoting=csv.QUOTE_ALL, lineterminator="\n")
        writer.writerow(RELEASE_COLUMNS)
        writer.writerows(rows)

    print(
        f"Wrote {output_path}: {len(rows)} rows x {len(RELEASE_COLUMNS)} columns"
    )
    return 0


def main():
    if len(sys.argv) != 3:
        print(
            "Usage: package-mapping-release.py INPUT.csv OUTPUT.csv", file=sys.stderr
        )
        sys.exit(1)

    sys.exit(1 if package(sys.argv[1], sys.argv[2]) else 0)


if __name__ == "__main__":
    main()
