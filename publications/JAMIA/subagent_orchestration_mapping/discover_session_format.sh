#!/bin/bash
# Discover Claude Code session log format so we can build a parser.
# Run from terminal: bash publications/JAMIA/subagent_orchestration_mapping/discover_session_format.sh

OUT_DIR="publications/JAMIA/subagent_orchestration_mapping"
OUT="$OUT_DIR/session_format_discovery.txt"

echo "=== Claude Code Session Log Discovery ===" > "$OUT"
echo "Date: $(date)" >> "$OUT"
echo "" >> "$OUT"

# Find the projects directory
CLAUDE_DIR="$HOME/.claude"
echo "=== Projects directory listing ===" >> "$OUT"
ls -la "$CLAUDE_DIR/projects/" >> "$OUT" 2>&1
echo "" >> "$OUT"

# Find session directories for the CVB project
echo "=== Looking for CVB-related project dirs ===" >> "$OUT"
for d in "$CLAUDE_DIR/projects/"*; do
    if [ -d "$d" ]; then
        basename "$d" >> "$OUT"
        # Check if it has a sessions subdir
        if [ -d "$d/sessions" ]; then
            echo "  -> has sessions/ dir" >> "$OUT"
            echo "  -> session count: $(ls "$d/sessions/" 2>/dev/null | wc -l)" >> "$OUT"
        fi
    fi
done
echo "" >> "$OUT"

# For each project dir with sessions, grab the most recent session file
echo "=== Most recent session file structure ===" >> "$OUT"
for d in "$CLAUDE_DIR/projects/"*/sessions; do
    if [ -d "$d" ]; then
        LATEST=$(ls -t "$d"/*.jsonl 2>/dev/null | head -1)
        if [ -z "$LATEST" ]; then
            LATEST=$(ls -t "$d"/* 2>/dev/null | head -1)
        fi
        if [ -n "$LATEST" ]; then
            echo "--- File: $LATEST ---" >> "$OUT"
            echo "Size: $(wc -c < "$LATEST") bytes" >> "$OUT"
            echo "Lines: $(wc -l < "$LATEST")" >> "$OUT"
            echo "" >> "$OUT"
            echo "First 3 lines (pretty-printed if JSON):" >> "$OUT"
            head -3 "$LATEST" | python3 -m json.tool 2>/dev/null || head -3 "$LATEST" >> "$OUT"
            echo "" >> "$OUT"
            echo "--- Keys in first line ---" >> "$OUT"
            head -1 "$LATEST" | python3 -c "
import json, sys
obj = json.loads(sys.stdin.readline())
def show_keys(d, prefix=''):
    if isinstance(d, dict):
        for k, v in d.items():
            t = type(v).__name__
            if isinstance(v, dict):
                print(f'{prefix}{k}: {{dict with {len(v)} keys}}')
                show_keys(v, prefix + '  ')
            elif isinstance(v, list):
                print(f'{prefix}{k}: [list of {len(v)}]')
                if v and isinstance(v[0], dict):
                    show_keys(v[0], prefix + '  [0].')
            else:
                val_preview = str(v)[:80]
                print(f'{prefix}{k}: ({t}) {val_preview}')
show_keys(obj)
" >> "$OUT" 2>&1
            echo "" >> "$OUT"

            # Look for usage/token fields anywhere in the file
            echo "--- Lines containing 'usage' or 'token' (first 10) ---" >> "$OUT"
            grep -n -i 'usage\|token' "$LATEST" | head -10 | python3 -c "
import sys, json
for line in sys.stdin:
    linenum, _, content = line.partition(':')
    # content may have more colons from the JSON
    rest = content.strip() if ':' not in content else ':'.join(line.split(':')[1:]).strip()
    try:
        obj = json.loads(rest)
        # Extract just usage-related fields
        def find_usage(d, path=''):
            if isinstance(d, dict):
                for k, v in d.items():
                    if 'usage' in k.lower() or 'token' in k.lower():
                        print(f'  Line {linenum}: {path}{k} = {v}')
                    elif isinstance(v, dict):
                        find_usage(v, path + k + '.')
        find_usage(obj)
    except:
        print(f'  Line {linenum}: {rest[:120]}')
" >> "$OUT" 2>&1
            echo "" >> "$OUT"

            # Sample a line that contains 'usage' and pretty-print it
            echo "--- Full sample line with 'usage' (first match, pretty-printed) ---" >> "$OUT"
            grep -m1 'usage' "$LATEST" | python3 -m json.tool >> "$OUT" 2>&1
            echo "" >> "$OUT"
            break  # Just need one project's data
        fi
    fi
done

echo "Results written to: $OUT"
