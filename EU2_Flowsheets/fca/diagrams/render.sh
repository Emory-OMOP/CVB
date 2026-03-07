#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"

for mmd in "$DIR"/*.mmd; do
  svg="${mmd%.mmd}.svg"
  echo "Rendering $(basename "$mmd") → $(basename "$svg")"
  npx -y @mermaid-js/mermaid-cli -i "$mmd" -o "$svg" -b transparent
done

echo "Done. SVGs in $DIR/"
