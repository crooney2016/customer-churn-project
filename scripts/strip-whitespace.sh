#!/bin/bash
# Strip trailing whitespace from Python files
#
# Usage:
#   ./scripts/strip-whitespace.sh                    # All Python files in function_app/ and tests/
#   ./scripts/strip-whitespace.sh path/to/file.py   # Specific file(s)
#   ./scripts/strip-whitespace.sh --check           # Check only, don't modify

set -e

check_only=false
files=()

# Parse arguments
for arg in "$@"; do
    if [[ "$arg" == "--check" ]]; then
        check_only=true
    else
        files+=("$arg")
    fi
done

# If no files specified, use default directories
if [[ ${#files[@]} -eq 0 ]]; then
    # Find all Python files in function_app/ and tests/
    while IFS= read -r -d '' file; do
        files+=("$file")
    done < <(find function_app tests -name "*.py" -print0 2>/dev/null)
fi

if [[ ${#files[@]} -eq 0 ]]; then
    echo "No Python files found."
    exit 0
fi

has_whitespace=false

for file in "${files[@]}"; do
    if [[ ! -f "$file" ]]; then
        echo "File not found: $file"
        continue
    fi

    # Check for trailing whitespace
    if grep -q '[[:space:]]$' "$file"; then
        if $check_only; then
            echo "Trailing whitespace found: $file"
            has_whitespace=true
        else
            # macOS sed requires '' after -i, Linux doesn't
            if [[ "$OSTYPE" == "darwin"* ]]; then
                sed -i '' 's/[[:space:]]*$//' "$file"
            else
                sed -i 's/[[:space:]]*$//' "$file"
            fi
            echo "Fixed: $file"
        fi
    fi
done

if $check_only && $has_whitespace; then
    echo ""
    echo "Run './scripts/strip-whitespace.sh' to fix."
    exit 1
fi

echo "Done."
