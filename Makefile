.PHONY: help lint-fix lint-check lint-check-python lint-check-markdown

# Default target
help:
	@echo "Available targets:"
	@echo "  make lint-fix           - Fix all linting errors (Python and Markdown)"
	@echo "  make lint-check         - Check for linting errors (dry-run)"
	@echo "  make lint-check-python  - Check Python linting errors only"
	@echo "  make lint-check-markdown - Check Markdown linting errors only"

# Fix all linting errors (Python and Markdown)
lint-fix:
	@echo "🔧 Fixing all linting errors..."
	@./scripts/fix-all-lint.sh

# Check for linting errors without fixing (dry-run)
lint-check:
	@echo "📋 Checking for linting errors (dry-run)..."
	@./scripts/fix-all-lint.sh --dry-run

# Check Python linting errors only
lint-check-python:
	@echo "🐍 Checking Python linting errors..."
	@python3 scripts/fix-python-lint.py --dry-run function_app/ scripts/

# Check Markdown linting errors only
lint-check-markdown:
	@echo "📝 Checking Markdown linting errors..."
	@python3 scripts/fix-markdown-lint.py --dry-run .
