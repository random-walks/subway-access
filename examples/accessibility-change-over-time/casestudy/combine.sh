#!/usr/bin/env bash
# Combine case study sections into a single CASESTUDY.md
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SECTIONS_DIR="$SCRIPT_DIR/sections"
OUTPUT="$SCRIPT_DIR/../CASESTUDY.md"

: > "$OUTPUT"

for section in "$SECTIONS_DIR"/[0-9]*.md; do
    cat "$section" >> "$OUTPUT"
    printf '\n\n' >> "$OUTPUT"
done

echo "Written to $OUTPUT ($(wc -l < "$OUTPUT") lines)"
