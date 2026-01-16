# Markdown Linting Fix Scripts

Automated scripts for fixing common markdownlint errors following `.cursor/rules/markdown.md` guidelines.

## For comprehensive linting automation (Python + Markdown), see [`README_LINTING.md`](README_LINTING.md)

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

## Fix all markdown files in project

```bash
./scripts/fix-all-markdown.sh
```

### Fix specific directory (Fix all markdown files in project)

```bash
python3 scripts/fix-markdown-lint.py docs/
python3 scripts/fix-markdown-lint.py .cursor/rules/
```

#### Fix single file

```bash
python3 scripts/fix-markdown-lint.py file.md
```

```bash
python3 scripts/fix-markdown-lint.py --dry-run docs/
```

## Script

### `fix-markdown-lint.py`

**Unified markdown fixer** - Can operate in two modes:

1. **Comprehensive mode (default)** - Scans and fixes all common errors in files/directories
1. **Specific mode (`--json`)** - Fixes only errors specified in JSON diagnostics file

#### Fixes

- **MD001** - Heading increment (fixes heading level jumps)
- **MD007** - Unordered list indentation (normalizes to 0 for top-level, 2 spaces per level)
- **MD009** - Trailing spaces (removes trailing spaces)
- **MD012** - Multiple blank lines (normalizes to single blank line)
- **MD024** - Duplicate headings (adds context to make unique)
- **MD026** - Trailing punctuation in headings (removes punctuation)
- **MD029** - Ordered list numbering (normalizes to 1/1/1 style)
- **MD031** - Blank lines around code fences
- **MD032** - Blank lines around lists
- **MD034** - Bare URLs (converts to markdown links)
- **MD036** - Emphasis as heading (converts to proper heading)
- **MD038** - Spaces inside code spans (removes spaces from backticks)
- **MD040** - Fenced code language (adds default 'text' if missing)
- **MD047** - Trailing newline (ensures exactly one)
- **MD056** - Table column count (fixes mismatched table columns)
- **MD060** - Table spacing (adds spaces around pipes)

```bash
# Comprehensive mode (default) - fix all errors
python3 scripts/fix-markdown-lint.py docs/
python3 scripts/fix-markdown-lint.py .cursor/rules/
python3 scripts/fix-markdown-lint.py README.md

# Specific mode - fix only errors from JSON diagnostics
python3 scripts/fix-markdown-lint.py --json errors.json
python3 scripts/fix-markdown-lint.py --json -  # Read from stdin

python3 scripts/fix-markdown-lint.py --dry-run docs/
python3 scripts/fix-markdown-lint.py --json --dry-run errors.json
```

**JSON Input Format** (for `--json` mode):

Expects JSON array of error objects (same format as VS Code diagnostics):

```json

[

  {
    "resource": "/path/to/file.md",
    "code": {"value": "MD032"},
    "startLineNumber": 10,
    "startColumn": 1
  }
]
```

## `fix-all-markdown.sh`

**Convenience wrapper** - Runs the Python fixer on entire project.

```bash
# Fix all markdown files in project 2
./scripts/fix-all-markdown.sh

# Fix specific directory 2
./scripts/fix-all-markdown.sh docs/
./scripts/fix-all-markdown.sh .cursor/rules/
```

## Integration with VS Code

### Option 1: Manual Fix

When VS Code shows markdownlint errors:

1. Copy error diagnostics (JSON format)
1. Save to file: `errors.json`
1. Run: `python3 scripts/fix-markdown-lint.py --json errors.json`

### Option 2: Use Main Fixer

For most errors, use the comprehensive fixer:

```bash
python3 scripts/fix-markdown-lint.py .
```

This will fix all common errors in all markdown files.

### Option 3: VS Code Task

Add to `.vscode/tasks.json`:

```json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "Fix Markdown Lint",
      "type": "shell",
      "command": "python3",
      "args": ["${workspaceFolder}/scripts/fix-markdown-lint.py", "${workspaceFolder}"],
      "problemMatcher": []
    }
  ]
}
```

Run via: **Terminal → Run Task → Fix Markdown Lint**

## Common Errors and Fixes

### MD007: Unordered list indentation

**Error:** Unordered list indentation [Expected: 0; Actual: 1] (or similar)

**Fix:** Script normalizes unordered list indentation:

- Top-level lists start at column 0 (no indentation)
- Nested lists use 2 spaces per nesting level (level 1 = 2 spaces, level 2 = 4 spaces, etc.)
- Preserves bullet style (`-`, `*`, or `+`)
- Handles nested lists correctly by tracking list context

### MD032: Blank lines around lists

**Error:** Lists should be surrounded by blank lines

**Fix:** Script adds blank lines before and after lists automatically

### MD031: Blank lines around code fences

**Error:** Fenced code blocks should be surrounded by blank lines

**Fix:** Script adds blank lines before and after code fences automatically

### MD029: Ordered list numbering

**Error:** Ordered list item prefix [Expected: 1; Actual: 2]

**Fix:** Script normalizes ordered lists to use 1/1/1 style

### MD047: Trailing newline

**Error:** Files should end with a single newline character

**Fix:** Script ensures exactly one trailing newline

### MD060: Table spacing

**Error:** Table column style [missing space to the right/left]

**Fix:** Script adds proper spacing around table pipes

### MD034: Bare URLs

**Error:** Bare URL used

**Fix:** Script converts bare URLs to markdown links: `[url](url)`

### MD040: Fenced code language

**Error:** Fenced code blocks should have a language specified

**Fix:** Script adds default 'text' language if missing

### MD036: Emphasis as heading

**Error:** Emphasis used instead of a heading

**Fix:** Script converts bold emphasis used as headings to proper headings (h4)

## Adding New Rules

When a new markdownlint error is encountered:

1. **Fix it manually** first to understand the pattern
1. **Add to script** following the pattern in `fix-markdown-lint.py`:
- Create `fix_mdXXX_error_name()` comprehensive function
- Create `fix_mdXXX_specific()` for JSON mode
- Add to `fix_all()` pipeline (check order dependencies)
- Add to `SPECIFIC_FIX_FUNCTIONS` dictionary
- Update docstring with new error code
1. **Test** with known error cases
1. **Document** in `.cursor/rules/markdown.md` and `.cursor/rules/linting.md`
1. **Update this README** with the new error code

See the "Adding New Rules" section in `fix-markdown-lint.py` for detailed instructions.

## Limitations

The scripts handle **most common** markdownlint errors automatically, but some issues may require manual fixes:

- **MD013** - Line length (requires manual formatting decisions based on content)

**Note:** All other common errors (MD001, MD007, MD009, MD012, MD024, MD026, MD029, MD031, MD032, MD034, MD036, MD038, MD040, MD047, MD056, MD060) are now handled automatically by the script.

## Automation

### Pre-commit Hook

Automatically fix markdown files before committing.

#### Option 1: Pre-commit Framework (Recommended)

1. Install pre-commit:

   ```bash
   pip install pre-commit
   ```

1. Install the hook:

   ```bash
   pre-commit install
   ```

1. The hook will automatically run `fix-markdown-lint.py` on staged `.md` files before each commit.

1. To run manually:

   ```bash
   pre-commit run --all-files
   ```

#### Option 2: Git Hook Script

A Git hook script is available at `.git/hooks/pre-commit`. To enable:

1. Make it executable (if not already):

   ```bash
   chmod +x .git/hooks/pre-commit
   ```

1. The hook will automatically:
- Run the fix script on all markdown files
- Re-stage any fixed files
- Allow the commit to proceed

1. To disable temporarily:

   ```bash
   mv .git/hooks/pre-commit .git/hooks/pre-commit.disabled
   ```

1. To re-enable:

   ```bash
   mv .git/hooks/pre-commit.disabled .git/hooks/pre-commit
   ```

**Note:** Git hooks are not version controlled. The `.pre-commit-config.yaml` file is version controlled and recommended for team use.

### CI Pipeline Integration

The GitHub Actions CI pipeline (`.github/workflows/ci.yml`) includes a `markdown-lint` job that:

1. Runs the fix script in dry-run mode
1. Fails the build if any markdown errors are found
1. Provides clear error messages indicating which files need fixes

#### To fix errors found in CI

1. Run the fix script locally:

   ```bash
   python3 scripts/fix-markdown-lint.py .
   ```

1. Commit and push the fixes:

   ```bash
   git add .
   git commit -m "Fix markdown linting errors"
   git push
   ```

The CI pipeline will pass once all errors are fixed.

### VS Code Integration

#### On-Save Auto-Fix (Optional)

Add to `.vscode/settings.json`:

```json
{
  "markdownlint.config": {
    "default": true
  },
  "[markdown]": {
    "editor.formatOnSave": false,
    "editor.codeActionsOnSave": {
      "source.fixAll.markdownlint": false
    }
  }
}
```

**Note:** The fix script is more comprehensive than VS Code's built-in markdownlint fixes. Use the script for best results.

## Best Practices

1. **Run fixer before committing:**

   ```bash
   python3 scripts/fix-markdown-lint.py .
   ```

1. **Use dry-run to preview changes:**

   ```bash
   python3 scripts/fix-markdown-lint.py --dry-run docs/
   ```

1. **Fix specific directories incrementally:**

   ```bash
   python3 scripts/fix-markdown-lint.py docs/
   python3 scripts/fix-markdown-lint.py .cursor/rules/
   ```

1. **Review changes in git:**

   ```bash
   git diff
   ```

## References

- [`README_LINTING.md`](README_LINTING.md) - Comprehensive linting automation guide
- `.cursor/rules/markdown.md` - Markdown formatting rules and guidelines
- [markdownlint Documentation](https://github.com/DavidAnson/markdownlint)
