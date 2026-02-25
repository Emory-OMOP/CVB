#!/bin/bash
set -euo pipefail

# -------------------------------------------------------------------
# CVB Revert Database
# Removes all custom vocabulary additions and re-registers the vocabulary.
#
# Usage:
#   docker compose run runner VOCAB_NAME/Builder/revert-db.sh
# -------------------------------------------------------------------

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VOCAB_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
REPO_DIR="$(cd "${VOCAB_DIR}/.." && pwd)"

source "${VOCAB_DIR}/vocab.env"

SHARED_SQL="${REPO_DIR}/Builder/sql/shared"
LOCAL_SQL="${SCRIPT_DIR}/sql"

PG_HOST="${PGHOST:-${1:-localhost}}"
PG_USER="${PGUSER:-postgres}"
PG_DB="${DB_NAME}"

PSQL="psql -h ${PG_HOST} -U ${PG_USER} -d ${PG_DB}"

echo "=== CVB Revert: ${VOCAB_NAME} ==="
echo "WARNING: This will remove all custom concepts from ${PG_DB}"
echo ""

# Remove all custom additions
echo "Running hard reset..."
${PSQL} -f "${SHARED_SQL}/hard-reset.sql"

# Re-register vocabulary
echo "Re-registering vocabulary..."
${PSQL} -f "${LOCAL_SQL}/create-general-concepts.sql"

# Reset ID sequence
echo "Resetting ID sequence..."
${PSQL} \
    -v id_range_min=${ID_RANGE_MIN} \
    -v id_range_max=${ID_RANGE_MAX} \
    -v id_range_start=${ID_RANGE_START} \
    -f "${SHARED_SQL}/revert-id-sequence.sql"

echo ""
echo "=== Revert complete ==="
