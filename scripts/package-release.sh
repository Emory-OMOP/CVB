#!/bin/bash
set -euo pipefail

# -------------------------------------------------------------------
# Package vocabulary releases as zip archives.
#
# Usage:
#   ./scripts/package-release.sh [VERSION] [VOCAB_NAME ...]
#
# VERSION defaults to YYYY.MM.DD. Packages all vocabs if none specified.
# Only vocabs with an Ontology/ directory are packaged.
#
# Output: release/{VOCAB}-v{VERSION}.zip
# -------------------------------------------------------------------

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

VERSION="${1:-$(date +%Y.%m.%d)}"
shift 2>/dev/null || true

RELEASE_DIR="${REPO_DIR}/release"
mkdir -p "${RELEASE_DIR}"

# Discover vocabs with Ontology/ dirs
VOCABS=()
if [[ $# -gt 0 ]]; then
    VOCABS=("$@")
else
    for dir in "${REPO_DIR}"/*/; do
        name="$(basename "${dir}")"
        [[ "${name}" == _* ]] && continue
        [[ "${name}" == .* ]] && continue
        [[ -d "${dir}/Ontology" ]] && VOCABS+=("${name}")
    done
fi

if [[ ${#VOCABS[@]} -eq 0 ]]; then
    echo "No vocabularies with Ontology/ directories found."
    exit 1
fi

echo "=== Packaging Release v${VERSION} ==="
echo ""

for vocab in "${VOCABS[@]}"; do
    ontology_dir="${REPO_DIR}/${vocab}/Ontology"
    if [[ ! -d "${ontology_dir}" ]]; then
        echo "SKIP: ${vocab} — no Ontology/ directory"
        continue
    fi

    zip_name="${vocab}-v${VERSION}.zip"
    zip_path="${RELEASE_DIR}/${zip_name}"

    (cd "${ontology_dir}" && zip -r "${zip_path}" . -x '.*' '*/.*') > /dev/null

    size=$(du -h "${zip_path}" | cut -f1)
    echo "  ${zip_name} (${size})"
done

echo ""
echo "=== Release packages in: ${RELEASE_DIR} ==="
ls -lh "${RELEASE_DIR}"/*.zip 2>/dev/null || echo "  (no packages created)"
