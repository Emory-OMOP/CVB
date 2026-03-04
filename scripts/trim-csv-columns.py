#!/usr/bin/env python3
"""
Trim a CSV to its first N columns, stripping workspace columns.

Used by the pipeline to remove non-pipeline columns (column 22+) before
loading into PostgreSQL. Handles quoted fields with commas correctly.

Usage:
    python scripts/trim-csv-columns.py INPUT.csv OUTPUT.csv [MAX_COLUMNS]

MAX_COLUMNS defaults to 21 (the CVB pipeline column count).
Reads from stdin if INPUT is -, writes to stdout if OUTPUT is -.
"""

import csv
import sys


def trim_csv(input_path, output_path, max_columns=21):
    if input_path == "-":
        infile = sys.stdin
    else:
        infile = open(input_path, encoding="utf-8", newline="")

    if output_path == "-":
        outfile = sys.stdout
    else:
        outfile = open(output_path, "w", encoding="utf-8", newline="")

    try:
        reader = csv.reader(infile)
        writer = csv.writer(outfile)
        for row in reader:
            writer.writerow(row[:max_columns])
    finally:
        if infile is not sys.stdin:
            infile.close()
        if outfile is not sys.stdout:
            outfile.close()


def main():
    if len(sys.argv) < 3:
        print("Usage: trim-csv-columns.py INPUT.csv OUTPUT.csv [MAX_COLUMNS]", file=sys.stderr)
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2]
    max_columns = int(sys.argv[3]) if len(sys.argv) > 3 else 21

    trim_csv(input_path, output_path, max_columns)


if __name__ == "__main__":
    main()
