# Linting Automation

Comprehensive documentation for automated linting and fixing of Python and Markdown files.

## Overview

This project uses automated linting with zero-touch fixes via pre-commit hooks and convenient manual commands.

#### Key Features

- **Automatic fixes** before commits (pre-commit hooks)
- **Unified commands** for manual fixes
- **CI/CD integration** for safety net
- **Recursive auto-fix** for complex cases

## Quick Start

### Automatic (Recommended)

Linting errors are **automatically fixed** before commits via pre-commit hooks. No action needed!

If hooks aren't installed yet:

```bash
pip install pre-commit
pre-commit install
```

### Manual Fixes

Fix all linting errors with one command:

```bash
# Fix all Python and Markdown files
./scripts/fix-all-lint.sh

# Or using Make 1
make lint-fix

# Preview what would be fixed (dry-run)
./scripts/fix-all-lint.sh --dry-run
make lint-check
```

## Commands

### Unified Commands (Commands)

#### `./scripts/fix-all-lint.sh` (Recommended)

Fixes both Python and Markdown linting errors in one command.

```bash
# Fix all files in project 1
./scripts/fix-all-lint.sh

# Fix specific directory 1
./scripts/fix-all-lint.sh function_app/
./scripts/fix-all-lint.sh docs/

./scripts/fix-all-lint.sh --dry-run

./scripts/fix-all-lint.sh --auto-fix
```

## `make lint-fix` / `make lint-check`

Makefile targets for convenience:

```bash
# Fix all linting errors
make lint-fix

# Check for errors (dry-run)
make lint-check

# Check specific file types
make lint-check-python
make lint-check-markdown
```

## Individual Commands (Check specific file types)

### Python Linting (Individual Commands)

```bash
# Fix all Python files
python3 scripts/fix-python-lint.py function_app/ scripts/

# Fix specific file
python3 scripts/fix-python-lint.py function_app/scorer.py

# Fix from JSON diagnostics 1
python3 scripts/fix-python-lint.py --json errors.json

# Recursive auto-fix 2
python3 scripts/fix-python-lint.py --auto-fix function_app/
```

See [`README_PYTHON_SCRIPTS.md`](README_PYTHON_SCRIPTS.md) for detailed Python linting documentation.

## Markdown Linting (Recursive auto-fix)

```bash
# Fix all Markdown files
python3 scripts/fix-markdown-lint.py .

# Fix specific directory 2
python3 scripts/fix-markdown-lint.py docs/

# Fix from JSON diagnostics 2
python3 scripts/fix-markdown-lint.py --json errors.json

# Dry-run 2
python3 scripts/fix-markdown-lint.py --dry-run docs/
```

See [`README_MARKDOWN_SCRIPTS.md`](README_MARKDOWN_SCRIPTS.md) for detailed Markdown linting documentation.

## Pre-commit Hooks

Pre-commit hooks **automatically fix** linting errors before each commit.

### Installation

```bash
pip install pre-commit
pre-commit install
```

### How It Works

1. Edit your code
1. Stage files (`git add`)
1. Commit (`git commit`)
1. Pre-commit hooks automatically run and fix linting errors
1. Fixed files are auto-staged
1. Commit proceeds

### Manual Execution

Run hooks manually on all files:

```bash
pre-commit run --all-files
```

Run specific hook:

```bash
pre-commit run fix-markdown-lint --all-files
pre-commit run fix-python-lint --all-files
```

### Configuration

Pre-commit hooks are configured in [`.pre-commit-config.yaml`](../.pre-commit-config.yaml):

- **Markdown hook**: Fixes all `.md` files
- **Python hook**: Fixes all `.py` files in `function_app/` and `scripts/`

## What Gets Fixed

### Python Linting (What Gets Fixed)

**Auto-fixed by ruff** (comprehensive mode):

- Import organization (isort)
- Code style issues (PEP 8)
- Unused imports/variables
- Code formatting (line length, spacing, etc.)

**Auto-fixed by script** (JSON mode):

- **W1309**: f-string-without-interpolation
- **W0612**: unused-variable
- **C0303**: trailing-whitespace
- **C0304**: missing-final-newline
- **C0321**: multiple-statements

### Markdown Linting (What Gets Fixed)

**Auto-fixed by script**:

- **MD001**: Heading increment
- **MD007**: Unordered list indentation
- **MD009**: Trailing spaces
- **MD012**: Multiple blank lines
- **MD024**: Duplicate headings
- **MD026**: Trailing punctuation in headings
- **MD029**: Ordered list numbering
- **MD031**: Blank lines around code fences
- **MD032**: Blank lines around lists
- **MD034**: Bare URLs
- **MD036**: Emphasis as heading
- **MD038**: Spaces inside code spans
- **MD040**: Fenced code language
- **MD047**: Trailing newline
- **MD056**: Table column count
- **MD060**: Table spacing

## CI/CD Integration

### GitHub Actions

The CI pipeline (`.github/workflows/ci.yml`) includes linting checks:

1. **Lint job**: Runs pylint, pyright, ruff
1. **Markdown-lint job**: Runs markdown fixer in dry-run mode

Linting errors in CI will block merges. Fix them locally:

```bash
# Fix all errors
./scripts/fix-all-lint.sh

# Commit and push
git add .
git commit -m "Fix linting errors"
git push
```

## Local CI Simulation

Simulate CI checks locally:

```bash
# Check for issues without fixing
./scripts/fix-all-lint.sh --dry-run

# Or using Make 2
make lint-check
```

## Workflows

### Daily Development (Recommended)

1. **Edit code** - Make your changes
1. **Stage files** - `git add .`
1. **Commit** - `git commit -m "message"` (hooks auto-fix)
1. **Push** - `git push`

**No manual linting needed!** Pre-commit hooks handle it automatically.

### Bulk Fixes

When fixing many files or onboarding:

```bash
# Fix all files in project 2
./scripts/fix-all-lint.sh

# Or using Make 3
make lint-fix
```

## VS Code Integration

When VS Code shows linting errors:

**Option 1: Use pre-commit hooks** (recommended)

- Just commit - hooks will auto-fix

#### Option 2: Manual fix

- Copy JSON diagnostics to `errors.json`
- Run: `python3 scripts/fix-python-lint.py --json errors.json`
- Or: `python3 scripts/fix-markdown-lint.py --json errors.json`

#### Option 3: Comprehensive fix

```bash
./scripts/fix-all-lint.sh
```

### Recursive Auto-Fix (VS Code Integration)

For complex cases with cascading fixes:

```bash
# Keep fixing until clean
./scripts/fix-all-lint.sh --auto-fix

# Or Python only
python3 scripts/fix-python-lint.py --auto-fix function_app/
```

This runs fixers multiple times until no more fixable errors remain (max 10 iterations).

## Troubleshooting

### Pre-commit hooks not running

#### Check installation

```bash
pre-commit --version
pre-commit install
```

#### Test hooks

```bash
pre-commit run --all-files
```

### Hooks are slow

Hooks run on staged files only, so they're usually fast. If slow:

1. Check hook configuration in `.pre-commit-config.yaml`
1. Ensure Python scripts are executable
1. Consider running hooks manually before commit

### Errors persist after fixing

Some errors require manual fixes (logic changes, type errors, etc.):

- **Type errors (pyright)**: Require code changes, not auto-fixed
- **Complex pylint warnings**: May require logic refactoring
- **MD013 (line length)**: Requires manual formatting decisions

For fixable errors:

```bash
# Try recursive auto-fix
./scripts/fix-all-lint.sh --auto-fix
```

## Script permissions

Make scripts executable:

```bash
chmod +x scripts/fix-all-lint.sh
chmod +x scripts/fix-markdown-lint.py
chmod +x scripts/fix-python-lint.py
```

Or run with `python3` explicitly:

```bash
python3 scripts/fix-markdown-lint.py .
python3 scripts/fix-python-lint.py function_app/
```

### Command not found: ruff

Install dependencies:

```bash
pip install -r requirements-dev.txt
```

Or install individually:

```bash
pip install ruff
```

## Best Practices

1. **Use pre-commit hooks** - Zero effort, automatic fixes
1. **Run `make lint-check` before PR** - Catch issues early
1. **Fix in CI** - If CI fails, run `./scripts/fix-all-lint.sh` locally
1. **Use dry-run first** - Preview changes before applying
1. **Commit often** - Hooks run on each commit, keeping code clean

## References

- [`README_PYTHON_SCRIPTS.md`](README_PYTHON_SCRIPTS.md) - Python linting details
- [`README_MARKDOWN_SCRIPTS.md`](README_MARKDOWN_SCRIPTS.md) - Markdown linting details
- [`.pre-commit-config.yaml`](../.pre-commit-config.yaml) - Pre-commit configuration
- [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) - CI pipeline configuration

## Command Reference

```bash
# Unified commands 2
./scripts/fix-all-lint.sh              # Fix all
./scripts/fix-all-lint.sh --dry-run    # Preview
./scripts/fix-all-lint.sh --auto-fix   # Recursive
make lint-fix                          # Fix all (Make)
make lint-check                        # Check (Make)

# Individual commands 2
python3 scripts/fix-python-lint.py function_app/
python3 scripts/fix-markdown-lint.py .
./scripts/fix-all-markdown.sh .

# Pre-commit
pre-commit run --all-files
pre-commit install
```
