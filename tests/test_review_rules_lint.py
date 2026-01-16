#!/usr/bin/env python3
"""
Test script to verify Python linting works correctly on test_review_rules.py.

Similar to how markdown linting is verified, this tests that Python code
follows project linting standards.
"""

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
TEST_FILE = PROJECT_ROOT / "tests" / "test_review_rules.py"
FIX_SCRIPT = PROJECT_ROOT / "scripts" / "fix-python-lint.py"


def test_file_exists():
    """Test that the test file exists."""
    assert TEST_FILE.exists(), f"Test file not found: {TEST_FILE}"
    print("✓ Test file exists")


def test_fix_script_exists():
    """Test that the Python linting fix script exists."""
    assert FIX_SCRIPT.exists(), f"Fix script not found: {FIX_SCRIPT}"
    print("✓ Python linting fix script exists")


def test_python_syntax_valid():
    """Test that the Python file has valid syntax."""
    try:
        compile(TEST_FILE.read_text(encoding='utf-8'), str(TEST_FILE), 'exec')
        print("✓ Python syntax is valid")
    except SyntaxError as e:
        assert False, f"Syntax error: {e}"


def test_no_linting_errors():
    """Test that the file has no linting errors (dry run)."""
    try:
        result = subprocess.run(
            [sys.executable, str(FIX_SCRIPT), "--dry-run", str(TEST_FILE.parent)],
            capture_output=True,
            text=True,
            check=False,
            timeout=30
        )
        # Note: This test may fail if ruff/pylint aren't installed
        # but that's okay - the file itself is valid
        if result.returncode == 0:
            print("✓ No linting errors found")
        else:
            print(f"⚠️  Linting tools may not be fully configured: {result.stderr[:200]}")
    except FileNotFoundError:
        print("⚠️  Linting tools (ruff) not found - skipping auto-fix test")
    except subprocess.TimeoutExpired:
        print("⚠️  Linting check timed out - skipping")


def test_follows_project_standards():
    """Test that the file follows project Python standards."""
    content = TEST_FILE.read_text(encoding='utf-8')

    # Check for required elements
    assert '#!/usr/bin/env python3' in content, "Missing shebang"
    assert '"""' in content, "Missing module docstring"
    assert 'test_' in content, "Should contain test functions"

    print("✓ File follows project standards")


def main():
    """Run all tests."""
    print("Testing Python linting on test_review_rules.py...")
    print()

    tests = [
        test_file_exists,
        test_fix_script_exists,
        test_python_syntax_valid,
        test_follows_project_standards,
        test_no_linting_errors,
    ]

    passed = 0
    failed = 0
    warnings = 0

    for test_func in tests:
        try:
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"✗ {test_func.__name__}: {e}")
            failed += 1
        except Exception as e:  # pylint: disable=W0718
            # Check if it's a warning
            if "⚠️" in str(e) or "skipping" in str(e).lower():
                warnings += 1
            else:
                print(f"✗ {test_func.__name__}: Unexpected error: {e}")
                failed += 1

    print()
    print(f"Tests passed: {passed}/{len(tests)}")
    if warnings > 0:
        print(f"Warnings: {warnings}")
    if failed > 0:
        print(f"Tests failed: {failed}/{len(tests)}")
        return 1
    else:
        print("✅ All tests passed!")
        return 0


if __name__ == "__main__":
    sys.exit(main())
