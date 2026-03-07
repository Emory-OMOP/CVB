#!/bin/bash
# Deeper probe of Claude Code session storage
OUT_DIR="publications/JAMIA/subagent_orchestration_mapping"
OUT="$OUT_DIR/session_format_discovery_v2.txt"

CLAUDE_DIR="$HOME/.claude"
CVB_DIR="$CLAUDE_DIR/projects/-Users-danielsmith-git-repos-org--Emory-OMOP-CVB--private"

echo "=== CVB project dir contents ===" > "$OUT"
ls -la "$CVB_DIR/" >> "$OUT" 2>&1
echo "" >> "$OUT"

echo "=== File types in CVB project dir ===" >> "$OUT"
find "$CVB_DIR" -maxdepth 1 -type f | head -20 >> "$OUT" 2>&1
echo "" >> "$OUT"

echo "=== Subdirs in CVB project dir ===" >> "$OUT"
find "$CVB_DIR" -maxdepth 1 -type d >> "$OUT" 2>&1
echo "" >> "$OUT"

# Check for JSONL files anywhere under the project dir
echo "=== JSONL files ===" >> "$OUT"
find "$CVB_DIR" -name "*.jsonl" -type f 2>/dev/null | head -10 >> "$OUT"
echo "" >> "$OUT"

# Check for JSON files
echo "=== JSON files ===" >> "$OUT"
find "$CVB_DIR" -name "*.json" -type f 2>/dev/null | head -10 >> "$OUT"
echo "" >> "$OUT"

# Check all file extensions
echo "=== All file extensions ===" >> "$OUT"
find "$CVB_DIR" -type f | sed 's/.*\.//' | sort | uniq -c | sort -rn >> "$OUT" 2>&1
echo "" >> "$OUT"

# Also check the broader .claude directory for session storage
echo "=== Global .claude dir contents ===" >> "$OUT"
ls -la "$CLAUDE_DIR/" >> "$OUT" 2>&1
echo "" >> "$OUT"

# Check for any sessions directory anywhere
echo "=== Any 'sessions' dirs under .claude ===" >> "$OUT"
find "$CLAUDE_DIR" -name "sessions" -type d 2>/dev/null | head -10 >> "$OUT"
echo "" >> "$OUT"

# Check for any jsonl files anywhere under .claude
echo "=== Any JSONL files under .claude (first 10) ===" >> "$OUT"
find "$CLAUDE_DIR" -name "*.jsonl" -type f 2>/dev/null | head -10 >> "$OUT"
echo "" >> "$OUT"

# If we find any jsonl, inspect the first one
FIRST_JSONL=$(find "$CLAUDE_DIR" -name "*.jsonl" -type f 2>/dev/null | head -1)
if [ -n "$FIRST_JSONL" ]; then
    echo "=== First JSONL file: $FIRST_JSONL ===" >> "$OUT"
    echo "Size: $(wc -c < "$FIRST_JSONL") bytes, Lines: $(wc -l < "$FIRST_JSONL")" >> "$OUT"
    echo "" >> "$OUT"
    echo "--- First line keys ---" >> "$OUT"
    head -1 "$FIRST_JSONL" | python3 -c "
import json, sys
obj = json.loads(sys.stdin.readline())
def show(d, prefix=''):
    if isinstance(d, dict):
        for k, v in d.items():
            t = type(v).__name__
            if isinstance(v, dict):
                print(f'{prefix}{k}: {{dict {len(v)} keys}}')
                show(v, prefix + '  ')
            elif isinstance(v, list):
                print(f'{prefix}{k}: [list {len(v)}]')
            else:
                print(f'{prefix}{k}: ({t}) {str(v)[:60]}')
show(obj)
" >> "$OUT" 2>&1
    echo "" >> "$OUT"
    echo "--- Lines with usage/token (first 5) ---" >> "$OUT"
    grep -n -i 'usage\|input_token\|output_token' "$FIRST_JSONL" | head -5 | while IFS= read -r line; do
        linenum=$(echo "$line" | cut -d: -f1)
        echo "Line $linenum:" >> "$OUT"
        sed -n "${linenum}p" "$FIRST_JSONL" | python3 -c "
import json, sys
obj = json.loads(sys.stdin.readline())
def find(d, path=''):
    if isinstance(d, dict):
        for k, v in d.items():
            if any(x in k.lower() for x in ['usage','token','cost']):
                print(f'  {path}{k} = {json.dumps(v)}')
            elif isinstance(v, dict):
                find(v, path + k + '.')
find(obj)
" >> "$OUT" 2>&1
    done
fi

echo "" >> "$OUT"
echo "Results written to: $OUT"
