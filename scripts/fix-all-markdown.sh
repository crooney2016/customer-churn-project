#!/bin/bash
# Fix all markdown linting errors in the project
#
# Usage:
#   ./scripts/fix-all-markdown.sh [directory]
#   ./scripts/fix-all-markdown.sh .cursor/rules/
#   ./scripts/fix-all-markdown.sh docs/

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TARGET_DIR="${1:-$PROJECT_ROOT}"

echo "Fixing markdown linting errors in: $TARGET_DIR"
echo ""

# Check if Python script exists
if [ ! -f "$SCRIPT_DIR/fix-markdown-lint.py" ]; then
    echo "Error: fix-markdown-lint.py not found at $SCRIPT_DIR/fix-markdown-lint.py"
    exit 1
fi

# Note: This script uses comprehensive mode (default)
# For JSON diagnostics mode, use: python3 scripts/fix-markdown-lint.py --json errors.json

# Make script executable
chmod +x "$SCRIPT_DIR/fix-markdown-lint.py"

# Run the fixer
cd "$PROJECT_ROOT"
python3 "$SCRIPT_DIR/fix-markdown-lint.py" "$TARGET_DIR"

echo ""
echo "✅ Markdown linting fixes complete!"
