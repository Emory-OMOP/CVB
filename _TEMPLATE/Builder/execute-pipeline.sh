#!/bin/bash
set -euo pipefail

# -------------------------------------------------------------------
# CVB Execute Pipeline
# Orchestrates the full vocabulary build from mapping CSVs to delta exports.
#
# Usage (from repo root):
#   docker compose run runner VOCAB_NAME/Builder/execute-pipeline.sh
#
# Or locally:
#   VOCAB_NAME/Builder/execute-pipeline.sh [pg_host]
# -------------------------------------------------------------------

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VOCAB_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
REPO_DIR="$(cd "${VOCAB_DIR}/.." && pwd)"

# Load configuration
source "${VOCAB_DIR}/vocab.env"

# Shared SQL lives in the repo-level Builder/sql/shared/
SHARED_SQL="${REPO_DIR}/Builder/sql/shared"

# Vocab-specific SQL
LOCAL_SQL="${SCRIPT_DIR}/sql"

# Mappings directory
MAP_DIR="${VOCAB_DIR}/Mappings"

# PostgreSQL connection — use env vars from docker-compose or pass host as $1
PG_HOST="${PGHOST:-${1:-localhost}}"
PG_USER="${PGUSER:-postgres}"
PG_DB="${DB_NAME}"

PSQL="psql -h ${PG_HOST} -U ${PG_USER} -d ${PG_DB}"

# Output directory
rm -rf /tmp/output
mkdir -p /tmp/output

echo "=== CVB Pipeline: ${VOCAB_NAME} ==="
echo "Database: ${PG_DB} @ ${PG_HOST}"
echo ""

# ------------------------------------------------------------------
# STEP 0: Register vocabulary (first run only — uncomment if needed)
# ------------------------------------------------------------------
# ${PSQL} -f "${LOCAL_SQL}/create-general-concepts.sql"

# ------------------------------------------------------------------
# STEP 1: Create staging tables for source mapping files
# ------------------------------------------------------------------
echo "[1/12] Creating source staging tables..."
${PSQL} -f "${LOCAL_SQL}/source-ddl.sql"

# ------------------------------------------------------------------
# STEP 2: Load mapping CSVs into staging tables
# ------------------------------------------------------------------
echo "[2/12] Loading mapping CSVs..."
IFS=' ' read -ra FILES <<< "${MAPPING_FILES}"
IFS=' ' read -ra TABLES <<< "${STAGING_TABLES}"
for i in "${!FILES[@]}"; do
    echo "  Loading ${FILES[$i]} -> ${TABLES[$i]}"
    ${PSQL} -c "\\copy ${TABLES[$i]} FROM '${MAP_DIR}/${FILES[$i]}' CSV HEADER"
done

# ------------------------------------------------------------------
# STEP 3: Transform raw mappings to source_to_update
# ------------------------------------------------------------------
echo "[3/12] Transforming mappings..."
${PSQL} -f "${LOCAL_SQL}/load-source.sql"

# ------------------------------------------------------------------
# STEP 4: Reset ID sequence
# ------------------------------------------------------------------
echo "[4/12] Resetting ID sequence..."
${PSQL} \
    -v id_range_min=${ID_RANGE_MIN} \
    -v id_range_max=${ID_RANGE_MAX} \
    -v id_range_start=${ID_RANGE_START} \
    -f "${SHARED_SQL}/revert-id-sequence.sql"

# ------------------------------------------------------------------
# STEP 5: Evaluate differences (new vs existing concepts)
# ------------------------------------------------------------------
echo "[5/12] Evaluating differences..."
${PSQL} \
    -v id_range_min=${NS_RANGE_MIN} \
    -v id_range_max=${ID_RANGE_MAX} \
    -f "${SHARED_SQL}/evaluate-difference.sql"

# ------------------------------------------------------------------
# STEP 6: Populate standard concept staging
# ------------------------------------------------------------------
echo "[6/12] Staging standard concepts..."
${PSQL} -f "${SHARED_SQL}/update-standard.sql"

# ------------------------------------------------------------------
# STEP 7: Populate non-standard concept staging
# ------------------------------------------------------------------
echo "[7/12] Staging non-standard concepts..."
${PSQL} \
    -v ns_range_min=${NS_RANGE_MIN} \
    -v ns_range_max=${NS_RANGE_MAX} \
    -f "${SHARED_SQL}/update-nonstandard.sql"

# ------------------------------------------------------------------
# STEP 8: Populate synonym staging
# ------------------------------------------------------------------
echo "[8/12] Staging synonyms..."
${PSQL} -f "${SHARED_SQL}/update-synonym.sql"

# ------------------------------------------------------------------
# STEP 9: Check for mapping updates and deprecations
# ------------------------------------------------------------------
echo "[9/12] Checking for updates and deprecations..."
${PSQL} -f "${SHARED_SQL}/deprecate-and-update.sql"

# ------------------------------------------------------------------
# STEP 10: Remove duplicates from staging
# ------------------------------------------------------------------
echo "[10/12] Removing duplicates..."
${PSQL} -f "${SHARED_SQL}/pre-update.sql"

# ------------------------------------------------------------------
# STEP 11: Apply core update to vocab tables
# ------------------------------------------------------------------
echo "[11/12] Applying core update..."
${PSQL} \
    -v vocab_id="${VOCAB_ID}" \
    -v vocab_concept_id=${VOCAB_CONCEPT_ID} \
    -f "${SHARED_SQL}/execute-core-update.sql"

# ------------------------------------------------------------------
# STEP 12: Logging and counts
# ------------------------------------------------------------------
echo "[12/12] Generating update log..."
${PSQL} -f "${SHARED_SQL}/message-log.sql"

# ==================================================================
# EXPORT DELTA TABLES
# ==================================================================
echo ""
echo "=== Exporting delta tables ==="

# Create delta tables
${PSQL} \
    -v vocab_id="${VOCAB_ID}" \
    -v id_range_min=${NS_RANGE_MIN} \
    -v id_range_max=${ID_RANGE_MAX} \
    -f "${SHARED_SQL}/create-delta-tables.sql"

# Export restore.sql via pg_dump
echo "-- EXECUTE THE CODE BELOW TO UPDATE YOUR VOCABULARY TABLES WITH ${VOCAB_NAME} CONCEPTS" >> /tmp/output/restore.sql

pg_dump -h "${PG_HOST}" -U "${PG_USER}" \
    --table=temp.concept_delta \
    --table=temp.concept_relationship_delta \
    --table=temp.concept_synonym_delta \
    --table=temp.concept_ancestor_delta \
    --table=temp.vocabulary_delta \
    --table=temp.concept_class_delta \
    --table=temp.source_to_concept_map_delta \
    --table=temp.mapping_metadata_delta \
    --column-inserts "${PG_DB}" >> /tmp/output/restore.sql

# Export delta CSVs
DELTA_TABLES=(
    "concept_delta"
    "concept_relationship_delta"
    "concept_synonym_delta"
    "concept_ancestor_delta"
    "vocabulary_delta"
    "concept_class_delta"
    "relationship_delta"
    "domain_delta"
    "source_to_concept_map_delta"
    "mapping_metadata_delta"
)

for table in "${DELTA_TABLES[@]}"; do
    echo "  Exporting ${table}..."
    ${PSQL} -c "\\copy temp.${table} TO '/tmp/output/${table}.csv' CSV HEADER"
done

# Export update log
${PSQL} -c "\\copy temp.UPDATE_LOG TO '/tmp/output/update_log.csv' CSV HEADER"

echo ""
echo "=== Pipeline complete ==="
echo "Delta files written to /tmp/output/"
echo "  (mounted at ./output/ on the host)"
