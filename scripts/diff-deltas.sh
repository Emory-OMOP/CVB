#!/bin/bash
set -euo pipefail

# -------------------------------------------------------------------
# Delta Comparison Tool
#
# Compares committed delta tables (VOCAB/Ontology/) against freshly
# built output (./output/) to show what changed.
#
# Usage:
#   ./scripts/diff-deltas.sh VOCAB_NAME
#
# Example:
#   ./scripts/diff-deltas.sh PSYCHIATRY
# -------------------------------------------------------------------

if [[ $# -lt 1 ]]; then
    echo "Usage: $0 VOCAB_NAME"
    echo ""
    echo "Compares VOCAB_NAME/Ontology/ (committed) vs ./output/ (just built)"
    exit 1
fi

VOCAB_NAME="$1"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

COMMITTED="${REPO_DIR}/${VOCAB_NAME}/Ontology"
BUILT="${REPO_DIR}/output"

if [[ ! -d "${COMMITTED}" ]]; then
    echo "ERROR: ${COMMITTED} not found."
    exit 1
fi

if [[ ! -d "${BUILT}" ]]; then
    echo "ERROR: ${BUILT} not found. Run the pipeline first."
    exit 1
fi

echo "=== Delta Comparison: ${VOCAB_NAME} ==="
echo "  Committed: ${COMMITTED}"
echo "  Built:     ${BUILT}"
echo ""

# Delta CSV files to compare
DELTA_FILES=(
    "concept_delta.csv"
    "concept_relationship_delta.csv"
    "concept_synonym_delta.csv"
    "concept_ancestor_delta.csv"
    "vocabulary_delta.csv"
    "concept_class_delta.csv"
    "relationship_delta.csv"
    "domain_delta.csv"
    "source_to_concept_map.csv"
    "mapping_metadata.csv"
    "update_log.csv"
)

# Also check for _delta suffix variants
printf "%-40s %10s %10s %10s\n" "FILE" "COMMITTED" "BUILT" "DIFF"
printf "%-40s %10s %10s %10s\n" "----" "---------" "-----" "----"

has_changes=false

for file in "${DELTA_FILES[@]}"; do
    committed_file="${COMMITTED}/${file}"
    built_file="${BUILT}/${file}"

    # Count rows (subtract 1 for header)
    if [[ -f "${committed_file}" ]]; then
        committed_count=$(( $(wc -l < "${committed_file}") - 1 ))
        [[ ${committed_count} -lt 0 ]] && committed_count=0
    else
        committed_count="-"
    fi

    if [[ -f "${built_file}" ]]; then
        built_count=$(( $(wc -l < "${built_file}") - 1 ))
        [[ ${built_count} -lt 0 ]] && built_count=0
    else
        built_count="-"
    fi

    # Compute diff
    if [[ "${committed_count}" == "-" ]] || [[ "${built_count}" == "-" ]]; then
        diff_str="N/A"
    else
        diff_val=$(( built_count - committed_count ))
        if [[ ${diff_val} -gt 0 ]]; then
            diff_str="+${diff_val}"
            has_changes=true
        elif [[ ${diff_val} -lt 0 ]]; then
            diff_str="${diff_val}"
            has_changes=true
        else
            diff_str="0"
        fi
    fi

    printf "%-40s %10s %10s %10s\n" "${file}" "${committed_count}" "${built_count}" "${diff_str}"
done

echo ""

# Show content differences for key files
if [[ "${has_changes}" == true ]]; then
    echo "=== Detailed Changes ==="
    echo ""
    for file in "concept_delta.csv" "concept_relationship_delta.csv" "source_to_concept_map.csv"; do
        committed_file="${COMMITTED}/${file}"
        built_file="${BUILT}/${file}"

        if [[ -f "${committed_file}" ]] && [[ -f "${built_file}" ]]; then
            # Sort both files and compare
            new_rows=$(comm -13 <(sort "${committed_file}") <(sort "${built_file}") | head -20)
            removed_rows=$(comm -23 <(sort "${committed_file}") <(sort "${built_file}") | head -20)

            if [[ -n "${new_rows}" ]] || [[ -n "${removed_rows}" ]]; then
                echo "--- ${file} ---"
                if [[ -n "${new_rows}" ]]; then
                    echo "  NEW rows (first 20):"
                    echo "${new_rows}" | sed 's/^/    /'
                fi
                if [[ -n "${removed_rows}" ]]; then
                    echo "  REMOVED rows (first 20):"
                    echo "${removed_rows}" | sed 's/^/    /'
                fi
                echo ""
            fi
        fi
    done
fi

# Show update log if present
if [[ -f "${BUILT}/update_log.csv" ]]; then
    echo "=== Update Log ==="
    cat "${BUILT}/update_log.csv"
    echo ""
fi

echo "=== Comparison complete ==="
