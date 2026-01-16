#!/bin/bash
# Fix all linting errors in the project (Python and Markdown)
#
# Usage:
#   ./scripts/fix-all-lint.sh [directory]
#   ./scripts/fix-all-lint.sh --dry-run
#   ./scripts/fix-all-lint.sh --auto-fix
#   ./scripts/fix-all-lint.sh function_app/
#
# Options:
#   --dry-run    Preview what would be fixed without making changes
#   --auto-fix   Recursively fix errors until no more fixable errors remain

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Parse arguments
DRY_RUN=false
AUTO_FIX=false
TARGET_DIR=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --auto-fix)
            AUTO_FIX=true
            shift
            ;;
        --*)
            echo "Unknown option: $1"
            echo "Usage: $0 [--dry-run] [--auto-fix] [directory]"
            exit 1
            ;;
        *)
            TARGET_DIR="$1"
            shift
            ;;
    esac
done

# Default to project root if no directory specified
if [ -z "$TARGET_DIR" ]; then
    TARGET_DIR="$PROJECT_ROOT"
fi

echo "🔧 Fixing linting errors in: $TARGET_DIR"
if [ "$DRY_RUN" = true ]; then
    echo "📋 DRY RUN MODE - No files will be modified"
fi
if [ "$AUTO_FIX" = true ]; then
    echo "♻️  AUTO-FIX MODE - Will recursively fix until clean"
fi
echo ""

# Check if Python scripts exist
if [ ! -f "$SCRIPT_DIR/fix-markdown-lint.py" ]; then
    echo "Error: fix-markdown-lint.py not found at $SCRIPT_DIR/fix-markdown-lint.py"
    exit 1
fi

if [ ! -f "$SCRIPT_DIR/fix-python-lint.py" ]; then
    echo "Error: fix-python-lint.py not found at $SCRIPT_DIR/fix-python-lint.py"
    exit 1
fi

# Make scripts executable
chmod +x "$SCRIPT_DIR/fix-markdown-lint.py" 2>/dev/null || true
chmod +x "$SCRIPT_DIR/fix-python-lint.py" 2>/dev/null || true

cd "$PROJECT_ROOT"

# Fix Markdown files
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📝 Fixing Markdown files..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

MARKDOWN_ARGS=("$TARGET_DIR")
if [ "$DRY_RUN" = true ]; then
    MARKDOWN_ARGS+=("--dry-run")
fi

python3 "$SCRIPT_DIR/fix-markdown-lint.py" "${MARKDOWN_ARGS[@]}"

MARKDOWN_EXIT=$?

# Fix Python files
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🐍 Fixing Python files..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

PYTHON_ARGS=("$TARGET_DIR")
if [ "$DRY_RUN" = true ]; then
    PYTHON_ARGS+=("--dry-run")
fi
if [ "$AUTO_FIX" = true ]; then
    PYTHON_ARGS+=("--auto-fix")
fi

python3 "$SCRIPT_DIR/fix-python-lint.py" "${PYTHON_ARGS[@]}"

PYTHON_EXIT=$?

# Summary
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 Summary"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

EXIT_CODE=0

if [ "$MARKDOWN_EXIT" -eq 0 ] && [ "$PYTHON_EXIT" -eq 0 ]; then
    echo "✅ All linting fixes complete!"
else
    if [ "$MARKDOWN_EXIT" -ne 0 ]; then
        echo "⚠️  Markdown linting had issues (exit code: $MARKDOWN_EXIT)"
        EXIT_CODE=1
    fi
    if [ "$PYTHON_EXIT" -ne 0 ]; then
        echo "⚠️  Python linting had issues (exit code: $PYTHON_EXIT)"
        EXIT_CODE=1
    fi
fi

if [ "$DRY_RUN" = true ]; then
    echo ""
    echo "💡 To apply fixes, run without --dry-run:"
    echo "   ./scripts/fix-all-lint.sh $TARGET_DIR"
fi

exit $EXIT_CODE
