#!/usr/bin/env python3
"""
Test script to verify review-rules.md methodology works correctly.

Tests that:
1. All referenced rule files exist
2. All referenced prompt files exist
3. Review-rules.md follows its own structure guidelines
4. No broken references
"""

import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
RULES_DIR = PROJECT_ROOT / ".cursor" / "rules"
PROMPTS_DIR = RULES_DIR / "prompts"
REVIEW_RULES_FILE = PROMPTS_DIR / "review-rules.md"


def test_all_core_rules_exist():
    """Test that all core rules listed in review-rules.md actually exist."""
    core_rules = [
        "overview.md",
        "python.md",
        "testing.md",
        "linting.md",
        "logging.md",
        "markdown.md",
        "error-handling.md",
        "secrets.md",
    ]

    missing = []
    for rule in core_rules:
        rule_path = RULES_DIR / rule
        if not rule_path.exists():
            missing.append(rule)

    assert not missing, f"Missing core rule files: {missing}"
    print("✓ All core rule files exist")


def test_all_domain_rules_exist():
    """Test that all domain-specific rules listed in review-rules.md actually exist."""
    # Note: dax.md and power-bi.md removed - now using Logic Apps for DAX queries
    domain_rules = [
        "function-app.md",
        "sql.md",
        "scoring.md",
        "notebooks.md",
        "deployment.md",
    ]

    missing = []
    for rule in domain_rules:
        rule_path = RULES_DIR / rule
        if not rule_path.exists():
            missing.append(rule)

    assert not missing, f"Missing domain rule files: {missing}"
    print("✓ All domain rule files exist")


def test_all_prompts_exist():
    """Test that all prompts listed in review-rules.md actually exist."""
    prompts = [
        "build-function.md",
        "build-sql.md",
        "code-review.md",
        "local-scoring.md",
        "review-rules.md",
    ]

    missing = []
    for prompt in prompts:
        prompt_path = PROMPTS_DIR / prompt
        if not prompt_path.exists():
            missing.append(prompt)

    assert not missing, f"Missing prompt files: {missing}"
    print("✓ All prompt files exist")


def test_review_rules_structure():
    """Test that review-rules.md follows its own structure guidelines."""
    content = REVIEW_RULES_FILE.read_text(encoding='utf-8')

    # Check for required sections
    required_sections = [
        "## Load All Rules",
        "## Review Tasks",
        "### 1. Consistency Check",
        "### 2. Redundancy Check",
        "### 3. Quality Check",
        "### 4. Prompt Quality",
        "### 5. Rule Dependencies",
        "### 6. Output Format",
        "## Review Process",
        "## Linting Requirements",
    ]

    missing_sections = []
    for section in required_sections:
        if section not in content:
            missing_sections.append(section)

    assert not missing_sections, f"Missing required sections: {missing_sections}"
    print("✓ All required sections present")


def test_no_broken_markdown_references():
    """Test that markdown.md references in review-rules.md are correct."""
    content = REVIEW_RULES_FILE.read_text(encoding='utf-8')

    # Check if markdown.md is referenced correctly
    markdown_ref_pattern = r'`markdown\.md`|\.cursor/rules/markdown\.md'
    matches = re.findall(markdown_ref_pattern, content)

    assert len(matches) > 0, "review-rules.md should reference markdown.md"
    print(f"✓ Found {len(matches)} references to markdown.md")


def test_linting_script_references():
    """Test that linting script commands in review-rules.md are correct."""
    content = REVIEW_RULES_FILE.read_text(encoding='utf-8')

    # Check if fix-markdown-lint.py is referenced
    script_ref = "fix-markdown-lint.py"
    assert script_ref in content, "review-rules.md should reference fix-markdown-lint.py"

    # Verify script exists
    script_path = PROJECT_ROOT / "scripts" / "fix-markdown-lint.py"
    assert script_path.exists(), "fix-markdown-lint.py script should exist"

    print("✓ Linting script references are correct")


def test_output_reference():
    """Test that output file reference is correct."""
    content = REVIEW_RULES_FILE.read_text(encoding='utf-8')

    # Check if .internal/ directory is mentioned for output
    output_ref = ".internal/"
    assert output_ref in content, "review-rules.md should specify output location"

    print("✓ Output reference is correct")


def test_checklist_structure():
    """Test that checklists in review-rules.md are properly formatted."""
    content = REVIEW_RULES_FILE.read_text(encoding='utf-8')

    # Check for checklist markers
    checklist_items = content.count("- [ ]")
    assert checklist_items > 0, "review-rules.md should contain checklists"

    print(f"✓ Found {checklist_items} checklist items")


def test_all_rule_files_exist():
    """Test that all actual rule files in .cursor/rules/ are accounted for."""
    actual_files = {f.name for f in RULES_DIR.glob("*.md") if f.is_file()}
    expected_core = {
        "overview.md", "python.md", "testing.md", "linting.md",
        "logging.md", "markdown.md", "error-handling.md", "secrets.md"
    }
    expected_domain = {
        "function-app.md", "sql.md", "scoring.md",
        "notebooks.md", "deployment.md"
    }
    expected_all = expected_core | expected_domain

    # Check for files not listed in review-rules.md
    additional_files = {
        "markdown-quick-reference.md",
        "documentation.md",
        "linting-markdown.md",
        "linting-python-scripts.md"
    }
    unexpected = actual_files - expected_all - additional_files

    if unexpected:
        print(f"⚠️  Note: Additional rule files found (not necessarily an error): {unexpected}")

    print(f"✓ Found {len(actual_files)} rule files total")


def main():
    """Run all tests."""
    print("Testing review-rules.md methodology...")
    print()

    tests = [
        test_all_core_rules_exist,
        test_all_domain_rules_exist,
        test_all_prompts_exist,
        test_review_rules_structure,
        test_no_broken_markdown_references,
        test_linting_script_references,
        test_output_reference,
        test_checklist_structure,
        test_all_rule_files_exist,
    ]

    passed = 0
    failed = 0

    for test_func in tests:
        try:
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"✗ {test_func.__name__}: {e}")
            failed += 1
        except Exception as e:  # pylint: disable=W0718
            print(f"✗ {test_func.__name__}: Unexpected error: {e}")
            failed += 1

    print()
    print(f"Tests passed: {passed}/{len(tests)}")
    if failed > 0:
        print(f"Tests failed: {failed}/{len(tests)}")
        return 1
    else:
        print("✅ All tests passed!")
        return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
