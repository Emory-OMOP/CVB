#!/bin/bash
set -euo pipefail

# -------------------------------------------------------------------
# Promote built deltas into a vocabulary package's Ontology/
#
# Usage:
#   ./scripts/promote-deltas.sh VOCAB_NAME [--apply]
#
# Without --apply this is a dry run: it shows the drift and lists what
# would be copied, and touches nothing.
#
# The build (VOCAB/Builder/execute-pipeline.sh) deliberately stops at
# ./output/ and never writes Ontology/. Promotion is a separate, explicit
# act because committed Ontology/ is the row-level id-registry-of-record
# for a vocabulary: it is what downstream consumers pin to, so a build
# that can mint ids must not write it unattended.
#
# This script never runs git. Committing the promoted files — normally via
# PR — is the human act that defines a release.
# -------------------------------------------------------------------

usage() {
    echo "Usage: $0 VOCAB_NAME [--apply]"
    echo ""
    echo "  VOCAB_NAME  Vocabulary package to promote into (e.g. EU2_Flowsheets)"
    echo "  --apply     Perform the copy. Omit for a dry run."
    echo ""
    echo "Compares ./output/ against VOCAB_NAME/Ontology/, then copies on --apply."
    exit 1
}

[[ $# -lt 1 ]] && usage

VOCAB_NAME="$1"
shift

APPLY=false
while [[ $# -gt 0 ]]; do
    case "$1" in
        --apply) APPLY=true; shift ;;
        -h|--help) usage ;;
        *) echo "ERROR: unknown argument '$1'"; echo ""; usage ;;
    esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

VOCAB_DIR="${REPO_DIR}/${VOCAB_NAME}"
ONTOLOGY_DIR="${VOCAB_DIR}/Ontology"
BUILT="${REPO_DIR}/output"

# --- Preconditions -------------------------------------------------

if [[ ! -d "${VOCAB_DIR}" ]]; then
    echo "ERROR: vocabulary package ${VOCAB_DIR} not found."
    exit 1
fi

if [[ ! -d "${BUILT}" ]]; then
    echo "ERROR: ${BUILT} not found. Run the pipeline first:"
    echo "  docker compose run runner ${VOCAB_NAME}/Builder/execute-pipeline.sh"
    exit 1
fi

shopt -s nullglob
BUILT_FILES=("${BUILT}"/*)
shopt -u nullglob

if [[ ${#BUILT_FILES[@]} -eq 0 ]]; then
    echo "ERROR: ${BUILT} is empty. Run the pipeline first:"
    echo "  docker compose run runner ${VOCAB_NAME}/Builder/execute-pipeline.sh"
    exit 1
fi

echo "=== Promote deltas: ${VOCAB_NAME} ==="
echo "  Built:    ${BUILT}"
echo "  Ontology: ${ONTOLOGY_DIR}"
echo "  Mode:     $([[ "${APPLY}" == true ]] && echo 'APPLY' || echo 'dry run (pass --apply to copy)')"
echo ""

# --- Drift check, always before any copy ---------------------------
# Advisory only: diff-deltas.sh reports differences but does not gate.
# Hardening it (git-HEAD baseline, volatile-column normalization, non-zero
# exit on drift) is a separate chore and will not change this interface.

if [[ -d "${ONTOLOGY_DIR}" ]] && compgen -G "${ONTOLOGY_DIR}/*.csv" > /dev/null; then
    echo "--- Drift vs the current Ontology/ baseline ---"
    # Invoked via `bash` rather than executed: diff-deltas.sh is mode 100644 in
    # git, so `./diff-deltas.sh` dies with "Permission denied".
    #
    # A non-zero exit here means the drift check FAILED TO RUN — today's
    # diff-deltas.sh is display-only and exits 0 even when it finds drift. So we
    # refuse to copy rather than promote with an unrun check, which would be the
    # silent-skip failure this pipeline already has a history of.
    #
    # NOTE for the diff-deltas hardening chore (ADR D6.5): once diff-deltas.sh
    # exits non-zero *on drift*, this test starts conflating "found drift" (the
    # normal promote case) with "could not run", and must be revisited.
    if ! bash "${SCRIPT_DIR}/diff-deltas.sh" "${VOCAB_NAME}"; then
        echo ""
        echo "ERROR: the drift check did not complete (see output above)."
        if [[ "${APPLY}" == true ]]; then
            echo "Refusing to promote: --apply requires a completed drift check."
            exit 1
        fi
        echo "Dry run continues, but treat the comparison above as unreliable."
    fi
else
    echo "--- No Ontology/ baseline yet: this is the first promote for ${VOCAB_NAME}."
    echo "    Nothing to diff against. Review the update log below carefully."
    echo ""
    if [[ -f "${BUILT}/update_log.csv" ]]; then
        echo "=== Update Log ==="
        cat "${BUILT}/update_log.csv"
        echo ""
    fi
fi

# --- Copy ----------------------------------------------------------

echo "--- Files to promote (${#BUILT_FILES[@]}) ---"
for f in "${BUILT_FILES[@]}"; do
    printf "    %-40s %8s bytes\n" "$(basename "${f}")" "$(wc -c < "${f}" | tr -d ' ')"
done
echo ""

if [[ "${APPLY}" != true ]]; then
    echo "Dry run — nothing was copied."
    echo "Re-run with --apply to promote these into ${VOCAB_NAME}/Ontology/:"
    echo "  ./scripts/promote-deltas.sh ${VOCAB_NAME} --apply"
    exit 0
fi

mkdir -p "${ONTOLOGY_DIR}"
cp "${BUILT_FILES[@]}" "${ONTOLOGY_DIR}/"

echo "Promoted ${#BUILT_FILES[@]} file(s) into ${VOCAB_NAME}/Ontology/."
echo ""
echo "Nothing has been committed. Review and commit to define the release:"
echo "  git add ${VOCAB_NAME}/Ontology"
echo "  git status"
