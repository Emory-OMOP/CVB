#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
CONFIG="$DIR/mermaid.config.json"

for mmd in "$DIR"/*.mmd; do
  svg="${mmd%.mmd}.svg"
  echo "Rendering $(basename "$mmd") → $(basename "$svg")"
  npx -y @mermaid-js/mermaid-cli -i "$mmd" -o "$svg" -b transparent -c "$CONFIG" -w 800
done

echo "Done. SVGs in $DIR/"
