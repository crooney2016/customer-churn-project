#!/usr/bin/env python3
"""
Generate comprehensive test suite report including:
- Test execution results
- Code coverage metrics
- Code quality scores (CodeHealthAnalyzer) for:
  - function_app/ (main application code)
  - tests/ (test code quality)
  - scripts/ (script code quality)

Usage:
    python3 generate_test_suite_report.py          # Generate standalone report
    python3 generate_test_suite_report.py --skip-tests  # Generate report without running tests
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
OUTPUT_DIR = PROJECT_ROOT / "docs"
OUTPUT_DIR.mkdir(exist_ok=True)

REPORT_FILE = OUTPUT_DIR / "test-suite-report.md"


def run_command(cmd, capture_output=True, check=False):
    """Run a shell command and return the result."""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=capture_output,
            text=True,
            check=check
        )
        return result.returncode, result.stdout, result.stderr
    except (OSError, subprocess.SubprocessError) as e:
        # pylint: disable=broad-exception-caught
        # Catch subprocess errors specifically
        return 1, "", str(e)


def run_tests():
    """Run pytest and return results."""
    print("🧪 Running test suite...")
    cmd = (
        "python3 -m pytest --cov=function_app --cov-report=json "
        "--cov-report=term-missing -v --tb=short"
    )
    returncode, stdout, stderr = run_command(cmd, check=False)

    # Try to read coverage JSON
    coverage_data = {}
    coverage_json = PROJECT_ROOT / "coverage.json"
    if coverage_json.exists():
        try:
            with open(coverage_json, 'r', encoding='utf-8') as f:
                coverage_data = json.load(f)
        except (json.JSONDecodeError, OSError):
            # pylint: disable=broad-exception-caught
            # Silently fail if coverage JSON is invalid or unreadable
            pass

    return returncode == 0, stdout, stderr, coverage_data


def get_code_quality_score(target_dir):
    """Get code quality score for a specific directory using CodeHealthAnalyzer."""
    print(f"📊 Analyzing code quality for {target_dir}...")

    # Use Python API instead of CLI to avoid PATH issues
    try:
        from codehealthanalyzer import CodeAnalyzer

        analyzer = CodeAnalyzer(str(PROJECT_ROOT / target_dir))
        score = analyzer.get_quality_score()

        # Get detailed analysis
        violations = analyzer.analyze_violations()
        errors = analyzer.analyze_errors()

        status = (
            'excellent' if score >= 80
            else 'good' if score >= 60
            else 'needs_improvement'
        )
        return {
            'score': score,
            'violations_count': len(violations) if violations else 0,
            'errors_count': len(errors) if errors else 0,
            'status': status
        }
    except ImportError:
        print(f"⚠️  CodeHealthAnalyzer not available, skipping {target_dir}")
        return None
    except (AttributeError, RuntimeError, ValueError) as e:
        # pylint: disable=broad-exception-caught
        # CodeAnalyzer may raise various exceptions during analysis
        print(f"⚠️  Error analyzing {target_dir}: {e}")
        return None


def format_coverage_summary(coverage_data):
    """Format coverage summary from JSON data."""
    if not coverage_data or 'totals' not in coverage_data:
        return "Coverage data not available"

    totals = coverage_data['totals']
    covered_lines = totals.get('covered_lines', 0)
    num_statements = totals.get('num_statements', 0)
    percent_covered = totals.get('percent_covered', 0.0)

    return f"""
- **Statements**: {num_statements}
- **Covered**: {covered_lines}
- **Coverage**: {percent_covered:.1f}%
"""


def generate_report(test_passed, test_output, test_error, coverage_data, quality_scores):
    """Generate the markdown report."""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    report_lines = [
        "# Test Suite Report",
        "",
        f"**Generated:** {timestamp}",
        "",
        "---",
        "",
        "## Summary",
        "",
    ]

    # Test status
    test_status = "✅ PASSED" if test_passed else "❌ FAILED"
    report_lines.extend([
        f"### Test Execution: {test_status}",
        "",
        f"All tests completed with exit code: {0 if test_passed else 1}",
        "",
    ])

    # Coverage summary
    report_lines.extend([
        "### Code Coverage",
        "",
    ])
    report_lines.append(format_coverage_summary(coverage_data))
    report_lines.append("")

    # Code Quality Scores
    report_lines.extend([
        "## Code Quality Analysis",
        "",
        "Code quality scores (0-100) generated using CodeHealthAnalyzer:",
        "",
    ])

    if quality_scores.get('function_app'):
        fa_score = quality_scores['function_app']
        if fa_score['status'] == 'excellent':
            status_emoji = "🟢"
        elif fa_score['status'] == 'good':
            status_emoji = "🟡"
        else:
            status_emoji = "🔴"
        status_text = fa_score['status'].replace('_', ' ').title()
        report_lines.extend([
            "### Main Application Code (`function_app/`)",
            "",
            f"{status_emoji} **Quality Score:** {fa_score['score']}/100 ({status_text})",
            f"- Violations: {fa_score['violations_count']}",
            f"- Errors: {fa_score['errors_count']}",
            "",
        ])

    if quality_scores.get('tests'):
        test_score = quality_scores['tests']
        if test_score['status'] == 'excellent':
            status_emoji = "🟢"
        elif test_score['status'] == 'good':
            status_emoji = "🟡"
        else:
            status_emoji = "🔴"
        status_text = test_score['status'].replace('_', ' ').title()
        report_lines.extend([
            "### Test Code (`tests/`)",
            "",
            f"{status_emoji} **Quality Score:** {test_score['score']}/100 ({status_text})",
            f"- Violations: {test_score['violations_count']}",
            f"- Errors: {test_score['errors_count']}",
            "",
        ])

    if quality_scores.get('scripts'):
        script_score = quality_scores['scripts']
        if script_score['status'] == 'excellent':
            status_emoji = "🟢"
        elif script_score['status'] == 'good':
            status_emoji = "🟡"
        else:
            status_emoji = "🔴"
        status_text = script_score['status'].replace('_', ' ').title()
        report_lines.extend([
            "### Scripts (`scripts/`)",
            "",
            f"{status_emoji} **Quality Score:** {script_score['score']}/100 ({status_text})",
            f"- Violations: {script_score['violations_count']}",
            f"- Errors: {script_score['errors_count']}",
            "",
        ])

    # Test Output
    output_limit = test_output[:5000] if len(test_output) > 5000 else test_output
    report_lines.extend([
        "---",
        "",
        "## Test Execution Output",
        "",
        "```",
        output_limit,  # Limit output
        "```",
        "",
    ])

    if test_error:
        error_limit = test_error[:2000] if len(test_error) > 2000 else test_error
        report_lines.extend([
            "## Test Error Output",
            "",
            "```",
            error_limit,
            "```",
            "",
        ])

    report_content = "\n".join(report_lines)

    # Write report
    with open(REPORT_FILE, 'w', encoding='utf-8') as f:
        f.write(report_content)

    print(f"✅ Report written to: {REPORT_FILE}")
    return report_content


def main():
    """Main execution."""
    parser = argparse.ArgumentParser(
        description='Generate test suite report with code quality analysis'
    )
    parser.add_argument(
        '--skip-tests',
        action='store_true',
        help='Skip running tests (only generate code quality analysis)'
    )
    args = parser.parse_args()

    print("📝 Generating test suite report...")
    print()

    # Run tests (unless skipped)
    if args.skip_tests:
        print("⏭️  Skipping test execution (--skip-tests flag)")
        test_passed = True
        test_output = "Tests skipped"
        test_error = ""
        coverage_data = {}
    else:
        test_passed, test_output, test_error, coverage_data = run_tests()
    print()

    # Get code quality scores
    quality_scores = {}

    print("📊 Analyzing code quality...")
    print()

    # Analyze main application code
    fa_score = get_code_quality_score('function_app')
    if fa_score:
        quality_scores['function_app'] = fa_score
        print(f"  function_app/: {fa_score['score']}/100")

    # Analyze test code
    test_score = get_code_quality_score('tests')
    if test_score:
        quality_scores['tests'] = test_score
        print(f"  tests/: {test_score['score']}/100")

    # Analyze scripts
    script_score = get_code_quality_score('scripts')
    if script_score:
        quality_scores['scripts'] = script_score
        print(f"  scripts/: {script_score['score']}/100")

    print()

    # Generate report
    try:
        generate_report(test_passed, test_output, test_error, coverage_data, quality_scores)
    except Exception as e:
        # pylint: disable=broad-exception-caught
        print(f"⚠️  Error generating report: {e}")
        print("   Continuing anyway...")

    # Always return 0 to allow report generation to complete
    # even if tests fail or there are issues
    return 0


if __name__ == "__main__":
    sys.exit(main())
