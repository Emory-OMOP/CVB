#!/bin/bash
set -euo pipefail

# finalize_batch.sh -- Single-command pipeline finalization
#
# Runs after sub-agents complete their work. Chains:
#   1. Accumulate sub-agent CSVs (with QA gate)
#   2. Push accumulated rows to clinical_review.csv
#   3. Validate source codes against enriched CSV
#   4. Auto-fix issues (merged fields, off-by-one codes, descriptions)
#   5. Re-validate to confirm clean state
#
# Usage:
#   bash EU2_Flowsheets/fca/finalize_batch.sh
#   bash EU2_Flowsheets/fca/finalize_batch.sh --dry-run

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
FCA_DIR="$SCRIPT_DIR"

DRY_RUN=false
if [[ "${1:-}" == "--dry-run" ]]; then
    DRY_RUN=true
    echo "=== DRY RUN MODE (no push, no apply) ==="
    echo
fi

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BOLD='\033[1m'
NC='\033[0m'

step=0
fail() {
    echo -e "\n${RED}FAILED at step $step: $1${NC}" >&2
    exit 1
}

# Step 1: Accumulate sub-agent CSVs
step=1
echo -e "${BOLD}[$step] Running sub-agent scripts and accumulating CSVs...${NC}"
cd "$FCA_DIR"
uv run python accumulate_reviews.py 2>&1 || fail "accumulate_reviews.py"
echo

# Step 2: Push to clinical_review.csv
step=2
if $DRY_RUN; then
    echo -e "${BOLD}[$step] Push to clinical_review.csv... ${YELLOW}SKIPPED (dry-run)${NC}"
else
    echo -e "${BOLD}[$step] Pushing accumulated rows to clinical_review.csv...${NC}"
    uv run python accumulate_reviews.py --skip-run --push 2>&1 || fail "accumulate_reviews.py --push"
fi
echo

# Step 3: Validate source codes
step=3
echo -e "${BOLD}[$step] Validating source codes against enriched CSV...${NC}"
VALIDATE_OUT=$(uv run python validate_review_codes.py 2>&1) || true
echo "$VALIDATE_OUT"

if echo "$VALIDATE_OUT" | grep -q "All source codes validated successfully"; then
    echo -e "\n${GREEN}Validation clean -- no fixes needed.${NC}"
    echo
    echo -e "${GREEN}${BOLD}Pipeline finalization complete.${NC}"
    exit 0
fi

echo

# Step 4: Auto-fix issues
step=4
if $DRY_RUN; then
    echo -e "${BOLD}[$step] Fix clinical review (dry run preview)...${NC}"
    uv run python fix_clinical_review.py 2>&1 || fail "fix_clinical_review.py (dry run)"
else
    echo -e "${BOLD}[$step] Applying fixes to clinical_review.csv...${NC}"
    uv run python fix_clinical_review.py --apply 2>&1 || fail "fix_clinical_review.py --apply"
fi
echo

# Step 5: Re-validate
step=5
echo -e "${BOLD}[$step] Re-validating after fixes...${NC}"
REVALIDATE_OUT=$(uv run python validate_review_codes.py 2>&1) || true
echo "$REVALIDATE_OUT"

if echo "$REVALIDATE_OUT" | grep -q "All source codes validated successfully"; then
    echo -e "\n${GREEN}${BOLD}Pipeline finalization complete.${NC}"
    exit 0
else
    ISSUE_COUNT=$(echo "$REVALIDATE_OUT" | grep -c "Line " || true)
    echo -e "\n${YELLOW}${BOLD}$ISSUE_COUNT issues remain after auto-fix -- manual review needed.${NC}"
    exit 1
fi
