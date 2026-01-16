# Python Linting Scripts

Documentation for Python linting convenience scripts.

## Script

### `fix-python-lint.py`

**Convenience wrapper** around existing Python linting tools (ruff, pylint, pyright).

**Purpose:** Provides a single command to run common Python linting fixes, rather than a custom auto-fixer like the markdown script.

#### What it does

1. Runs `ruff check --fix` - Auto-fixes linting issues (imports, style, etc.)
1. Runs `ruff format` - Formats code according to project style
1. Optionally runs `pyright` - Type checking (read-only, no fixes)
1. Optionally runs `pylint` - Style checking (read-only, no fixes)

#### Why a wrapper, not a custom fixer

- Python tools (especially ruff) already have excellent auto-fix capabilities
- Type errors (pyright) and logic errors (pylint) shouldn't be auto-fixed
- Wrapper provides convenience without risk of breaking code

## Usage

### Basic Usage

```bash
# Fix all Python files in function_app/
python3 scripts/fix-python-lint.py function_app/

# Fix specific file
python3 scripts/fix-python-lint.py function_app/scorer.py

# Fix all Python files (default target)
python3 scripts/fix-python-lint.py
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

### Combined Options

```bash
# Dry run with type checking
python3 scripts/fix-python-lint.py --dry-run --check-types function_app/

# Full check (fixes + type check + pylint)
python3 scripts/fix-python-lint.py --check-types --check-pylint function_app/
```

## What Gets Fixed

### Auto-Fixed by Ruff

- Import organization (isort)
- Code style issues (PEP 8)
- Unused imports/variables
- Code formatting (line length, spacing, etc.)

### Reported Only (Not Fixed)

- Type errors (pyright) - Require code changes
- Pylint warnings - May require logic changes
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

## References

- `.cursor/rules/python.md` - Python coding standards and linting rules
- `.cursor/rules/linting.md` - General linting philosophy
- `pyproject.toml` - Ruff configuration
- `.pylintrc` - Pylint configuration
- `pyrightconfig.json` - Pyright configuration
