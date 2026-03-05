#!/bin/bash
# FCA Pipeline Runner — orchestrates all steps
# Run from EU2_Flowsheets/:
#   cd EU2_Flowsheets && bash fca/run_pipeline.sh
#
# Or from anywhere:
#   bash EU2_Flowsheets/fca/run_pipeline.sh

set -euo pipefail

PROJECT_DIR="/Users/danielsmith/git_repos/org__Emory-OMOP/CVB/EU2_Flowsheets"
RAW_DIR="$PROJECT_DIR/raw_for_fca"
MAPPINGS_DIR="$PROJECT_DIR/Mappings"

cd "$PROJECT_DIR"

echo "=== FCA Pipeline ==="
echo "Working directory: $PROJECT_DIR"
echo "Started: $(date)"

# Find master extract (supports versioned filenames like fca_master_extract__v20260304.csv)
INPUT=""
for f in "$RAW_DIR"/fca_master_extract*.csv; do
    [ -f "$f" ] && INPUT="$f" && break
done
if [ -z "$INPUT" ]; then
    # Fall back to partial extract
    if [ -f "$RAW_DIR/template_lines.csv" ]; then
        INPUT="$RAW_DIR/template_lines.csv"
        echo "Using partial extract (template_lines.csv) for proof-of-concept"
    else
        echo "ERROR: No input CSV found. Run the Clarity export queries first."
        echo "Expected: $RAW_DIR/fca_master_extract*.csv"
        exit 1
    fi
else
    echo "Using master extract: $INPUT"
fi

# Find custom lists (supports versioned filenames)
CUSTOM_FLAG=""
for f in "$RAW_DIR"/fca_custom_lists*.csv; do
    if [ -f "$f" ]; then
        CUSTOM_FLAG="--custom-lists $f"
        echo "Custom lists: $f"
        break
    fi
done

# Step 2: Build formal context
echo ""
echo "=== Step 2: Build Formal Context ==="
uv run python -m fca.build_context \
    --master "$INPUT" \
    $CUSTOM_FLAG \
    --output-dir "$RAW_DIR"

# Step 3: Compute concept lattice
echo ""
echo "=== Step 3: Compute Concept Lattice ==="
uv run python -m fca.compute_lattice \
    --context-dir "$RAW_DIR" \
    --output "$RAW_DIR/fca_lattice.json"

# Step 4: Classify concepts
echo ""
echo "=== Step 4: Classify Concepts ==="
uv run python -m fca.classify_concepts \
    --lattice "$RAW_DIR/fca_lattice.json" \
    --output "$RAW_DIR/fca_classification.json"

# Step 5: Generate mappings
echo ""
echo "=== Step 5: Generate Mappings ==="
uv run python -m fca.generate_mappings \
    --classification "$RAW_DIR/fca_classification.json" \
    --metadata "$RAW_DIR/fca_metadata.json" \
    --output-dir "$MAPPINGS_DIR"

# Step 6: Validate
echo ""
echo "=== Step 6: Validate ==="
uv run python -m fca.validate \
    --context-dir "$RAW_DIR" \
    --lattice "$RAW_DIR/fca_lattice.json" \
    --classification "$RAW_DIR/fca_classification.json" \
    --output "$RAW_DIR/fca_validation.json"

echo ""
echo "=== Pipeline Complete ==="
echo "Finished: $(date)"
echo ""
echo "Output files:"
ls -la "$RAW_DIR"/fca_*.json "$RAW_DIR"/fca_*.npz 2>/dev/null
ls -la "$MAPPINGS_DIR"/compositional_mapping.csv "$MAPPINGS_DIR"/atomic_items.csv "$MAPPINGS_DIR"/unmappable_items.csv 2>/dev/null
