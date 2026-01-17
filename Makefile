.PHONY: help lint-fix lint-check lint-check-python lint-check-markdown code-quality report

# Default target
help:
	@echo "Available targets:"
	@echo "  make lint-fix              - Fix all linting errors (Python and Markdown)"
	@echo "  make lint-check            - Check for linting errors (dry-run)"
	@echo "  make lint-check-python     - Check Python linting errors only"
	@echo "  make lint-check-markdown   - Check Markdown linting errors only"
	@echo "  make code-quality          - Run code quality analyzer and generate score report"
	@echo "  make report                - Generate comprehensive project report (tests + coverage + quality + review)"

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

# Run code quality analyzer (CodeHealthAnalyzer - similar to CodeClimate/SonarQube)
code-quality:
	@echo "📊 Analyzing code quality..."
	@python3 -m codehealthanalyzer analyze function_app/ scripts/ --format html --output outputs/code-quality-report/ || true
	@python3 -m codehealthanalyzer score function_app/ scripts/ || true

# Generate comprehensive project report (all-in-one)
report:
	@echo "📊 Generating comprehensive project report..."
	@python3 scripts/generate_project_report.py
	@echo ""
	@echo "✅ Report saved to: docs/comprehensive-report.md"

# Generate comprehensive project report (all-in-one: tests + coverage + quality + review)
report:
	@echo "📊 Generating comprehensive project report..."
	@python3 scripts/generate_project_report.py
	@echo ""
	@echo "✅ Report saved to: docs/comprehensive-report.md"
