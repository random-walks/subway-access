#!/usr/bin/env bash
# Combine case study sections into a single CASESTUDY.md
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SECTIONS_DIR="$SCRIPT_DIR/sections"
OUTPUT="$SCRIPT_DIR/../CASESTUDY.md"

: > "$OUTPUT"

sections=("$SECTIONS_DIR"/[0-9]*.md)
for i in "${!sections[@]}"; do
    cat "${sections[$i]}" >> "$OUTPUT"
    # Add separator between sections, but not after the last one
    if (( i < ${#sections[@]} - 1 )); then
        printf '\n\n' >> "$OUTPUT"
    fi
done
# Ensure exactly one trailing newline (end-of-file-fixer)
printf '\n' >> "$OUTPUT"

echo "Written to $OUTPUT ($(wc -l < "$OUTPUT") lines)"
