# Python Linting Scripts

Documentation for Python linting convenience scripts.

#### For comprehensive linting automation (Python + Markdown), see [`README_LINTING.md`](README_LINTING.md)

## Script

### `fix-python-lint.py`

**Python linting fixer** with auto-fix capabilities for common pylint errors.

Can operate in two modes:

1. **Comprehensive mode (default)**: Runs ruff/pylint/pyright tools
1. **Specific mode (`--json`)**: Fixes only errors specified in JSON diagnostics file

#### What it does

#### Comprehensive Mode

1. Runs `ruff check --fix` - Auto-fixes linting issues (imports, style, etc.)
1. Runs `ruff format` - Formats code according to project style
1. Optionally runs `pyright` - Type checking (read-only, no fixes)
1. Optionally runs `pylint` - Style checking (read-only, no fixes)

#### Specific Mode (`--json`)

- Fixes common pylint errors from JSON diagnostics:
  - **W1309**: f-string-without-interpolation (convert to regular string)
  - **W0612**: unused-variable (remove unused variable assignments)
  - **C0303**: trailing-whitespace (remove trailing spaces)
  - **C0304**: missing-final-newline (add final newline)
  - **C0321**: multiple-statements (split to separate lines)

## Quick Start

### Unified Command (Recommended)

For fixing both Python and Markdown linting errors:

```bash
# Fix all linting errors (Python + Markdown)
./scripts/fix-all-lint.sh

# Or using Make
make lint-fix

# Preview changes (dry-run)
./scripts/fix-all-lint.sh --dry-run
make lint-check
```

See [`README_LINTING.md`](README_LINTING.md) for comprehensive linting automation documentation.

## Usage

### Comprehensive Mode (Default)

```bash
# Fix all Python files in function_app/
python3 scripts/fix-python-lint.py function_app/

# Fix specific file
python3 scripts/fix-python-lint.py function_app/scorer.py

# Fix all Python files (default target)
python3 scripts/fix-python-lint.py
```

## Specific Mode (JSON Diagnostics)

Fix only errors from JSON diagnostics (e.g., from VS Code or pylint):

```bash
# Fix errors from JSON file
python3 scripts/fix-python-lint.py --json errors.json

# Fix errors from stdin
python3 scripts/fix-python-lint.py --json -

# Example: Pipe pylint JSON output
pylint --output-format=json file.py | python3 scripts/fix-python-lint.py --json -
```

#### JSON Input Format

Expects JSON array of error objects (same format as VS Code diagnostics):

```json

[

  {
    "resource": "/path/to/file.py",
    "code": {"value": "W1309:f-string-without-interpolation"},
    "startLineNumber": 48,
    "startColumn": 11
  }
]
```

## Dry Run

Preview what would be fixed without making changes:

```bash
python3 scripts/fix-python-lint.py --dry-run function_app/
```

### Type Checking

Include type checking (read-only, reports errors but doesn't fix):

```bash
python3 scripts/fix-python-lint.py --check-types function_app/
```

### Pylint Checking

Include pylint checking (read-only, reports issues but doesn't fix):

```bash
python3 scripts/fix-python-lint.py --check-pylint function_app/
```

### Auto-Fix Recursive Mode

Automatically fix errors recursively until no more fixable errors remain:

```bash
# Auto-fix recursively (comprehensive mode)
python3 scripts/fix-python-lint.py --auto-fix function_app/

# Auto-fix recursively after JSON fixes
python3 scripts/fix-python-lint.py --json errors.json --auto-fix
```

## Combined Options

```bash
# Dry run with type checking
python3 scripts/fix-python-lint.py --dry-run --check-types function_app/

# Full check (fixes + type check + pylint)
python3 scripts/fix-python-lint.py --check-types --check-pylint function_app/

# JSON mode with dry run
python3 scripts/fix-python-lint.py --json errors.json --dry-run
```

## What Gets Fixed

### Auto-Fixed by Ruff (Comprehensive Mode)

- Import organization (isort)
- Code style issues (PEP 8)
- Unused imports/variables
- Code formatting (line length, spacing, etc.)

### Auto-Fixed by Script (JSON Mode)

- **W1309**: f-string-without-interpolation
  - Converts `f"string"` to `"string"` when no interpolation exists
- **W0612**: unused-variable
  - Comments out unused variable assignments
- **C0303**: trailing-whitespace
  - Removes trailing spaces from lines
- **C0304**: missing-final-newline
  - Ensures file ends with exactly one newline
- **C0321**: multiple-statements
  - Splits multiple statements on same line to separate lines

### Reported Only (Not Fixed)

- Type errors (pyright) - Require code changes
- Complex pylint warnings - May require logic changes
- Complex refactoring - Requires human review

## Integration with CI/CD

The script returns appropriate exit codes for CI/CD pipelines:

- Exit code 0: All checks passed
- Exit code 1: Linting/formatting issues found or fixed

### Example CI usage

```yaml
# .github/workflows/ci.yml

- name: Fix Python linting

  run: python3 scripts/fix-python-lint.py function_app/
  
- name: Check for changes

  run: |
    if [ -n "$(git status --porcelain)" ]; then
      echo "Linting fixes were applied. Please commit them."
      exit 1
    fi
```

## Comparison with Direct Tool Usage

### Using the Script

```bash
python3 scripts/fix-python-lint.py function_app/
```

- Single command for common workflow
- Consistent across team
- Easy to remember

### Using Tools Directly

```bash
ruff check --fix function_app/
ruff format function_app/
pyright function_app/
```

- More control over individual tools
- Can run tools separately
- Useful for debugging specific issues

**When to use script:** Daily development, pre-commit, CI/CD
**When to use tools directly:** Debugging, specific tool configuration, advanced usage

## Dependencies

The script requires:

- `ruff` - Primary linting and formatting tool (in `requirements-dev.txt`)
- `pyright` - Optional, for type checking (typically via VS Code extension or npm)
- `pylint` - Optional, for style checking (if using `--check-pylint`)

Install with:

```bash
pip install -r requirements-dev.txt
```

## Troubleshooting

### "Command not found: ruff"

Install ruff:

```bash
pip install ruff
```

Or install all dev dependencies:

```bash
pip install -r requirements-dev.txt
```

### Type errors reported but not fixed

This is expected. Type errors (pyright) require code changes and are not auto-fixed. Review the errors and fix manually.

### Pylint issues reported but not fixed

This is expected. Pylint issues may require logic changes and are not auto-fixed. Review the warnings and fix manually.

## Integration with VS Code

### Option 1: Manual Fix

When VS Code shows pylint errors:

1. Copy error diagnostics (JSON format)
1. Save to file: `errors.json`
1. Run: `python3 scripts/fix-python-lint.py --json errors.json`

### Option 2: Use Comprehensive Fixer

For most errors, use the comprehensive fixer:

```bash
python3 scripts/fix-python-lint.py function_app/
```

This will run ruff which handles most common issues automatically.

### Option 3: Auto-Fix Recursive

Automatically fix all issues without prompting:

```bash
python3 scripts/fix-python-lint.py --auto-fix function_app/
```

This will recursively fix errors until no more fixable errors remain.

## Adding New Fixers

To add support for a new pylint error:

1. Create fixer function: `fix_XXXX_error_name(file_path, line_num, content) -> str`
1. Add to `SPECIFIC_FIX_FUNCTIONS` dictionary: `'XXXX': fix_XXXX_error_name`
1. Update docstring at top of file with new error code
1. Test with known error cases
1. Document in this README

## References

- [`README_LINTING.md`](README_LINTING.md) - Comprehensive linting automation guide
- `.cursor/rules/python.md` - Python coding standards and linting rules
- `.cursor/rules/linting.md` - General linting philosophy
- `pyproject.toml` - Ruff configuration
- `.pylintrc` - Pylint configuration
- `pyrightconfig.json` - Pyright configuration
