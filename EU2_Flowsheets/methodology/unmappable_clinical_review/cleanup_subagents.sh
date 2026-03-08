#!/bin/bash
# Clean up old sub-agent scripts and CSVs before a new batch.
# Run this BEFORE creating new sub-agent scripts.
#
# Usage: bash EU2_Flowsheets/fca/cleanup_subagents.sh

REPO="$(cd "$(dirname "$0")/../.." && pwd)"
PY_DIR="$REPO/.private/subagents/py"
CSV_DIR="$REPO/.private/subagents/csv"
PREFIX="clinical_review__subagent_"

echo "=== Cleaning old sub-agent artifacts ==="

count=0
for dir in "$PY_DIR" "$CSV_DIR"; do
    for f in "$dir/${PREFIX}"*.py "$dir/${PREFIX}"*.csv "$dir/clinical_review__accumulated.csv"; do
        if [ -f "$f" ]; then
            rm "$f"
            echo "Deleted: $f"
            ((count++))
        fi
    done
done

# Also clean legacy /tmp/claude location
for f in /tmp/claude/${PREFIX}*.py /tmp/claude/${PREFIX}*.csv /tmp/claude/clinical_review__accumulated.csv; do
    if [ -f "$f" ]; then
        rm "$f"
        echo "Deleted (legacy): $f"
        ((count++))
    fi
done

echo ""
echo "Deleted $count files."

# Ensure dirs exist for next batch
mkdir -p "$PY_DIR" "$CSV_DIR"
echo "Ensured dirs exist: $PY_DIR, $CSV_DIR"
