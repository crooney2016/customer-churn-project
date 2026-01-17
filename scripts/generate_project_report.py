#!/usr/bin/env python3
"""
Generate comprehensive project report combining:
- Test suite execution and coverage
- Code quality analysis (CodeHealthAnalyzer)
- Code review analysis (linting, performance patterns)
- All in one unified report
"""

import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

PROJECT_ROOT = Path(__file__).parent.parent
OUTPUT_DIR = PROJECT_ROOT / "docs"
OUTPUT_DIR.mkdir(exist_ok=True)
FUNCTION_APP_DIR = PROJECT_ROOT / "function_app"
REPORT_FILE = OUTPUT_DIR / "comprehensive-report.md"


def run_command(cmd, capture_output=True, check=False, timeout=None):
    """Run a shell command and return the result."""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=capture_output,
            text=True,
            check=check,
            timeout=timeout
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return 1, "", "Command timed out"
    except (OSError, subprocess.SubprocessError) as e:
        # pylint: disable=broad-exception-caught
        return 1, "", str(e)


def run_tests():
    """Run pytest and return results."""
    print("🧪 Running test suite...")
    cmd = (
        "python3 -m pytest --cov=function_app --cov-report=json "
        "--cov-report=term-missing -v --tb=short"
    )
    returncode, stdout, stderr = run_command(cmd, check=False, timeout=300)

    # Try to read coverage JSON
    coverage_data = {}
    coverage_json = PROJECT_ROOT / "coverage.json"
    if coverage_json.exists():
        try:
            with open(coverage_json, 'r', encoding='utf-8') as f:
                coverage_data = json.load(f)
        except (json.JSONDecodeError, OSError):
            # pylint: disable=broad-exception-caught
            pass

    return returncode == 0, stdout, stderr, coverage_data


def get_code_quality_scores():
    """Get code quality scores using CodeHealthAnalyzer."""
    print("📊 Analyzing code quality with CodeHealthAnalyzer...")
    scores = {}

    directories = ['function_app', 'tests', 'scripts']
    for target_dir in directories:
        print(f"  Analyzing {target_dir}/...")
        try:
            from codehealthanalyzer import CodeAnalyzer

            analyzer = CodeAnalyzer(str(PROJECT_ROOT / target_dir))
            score = analyzer.get_quality_score()
            violations = analyzer.analyze_violations()
            errors = analyzer.analyze_errors()

            status = (
                'excellent' if score >= 80
                else 'good' if score >= 60
                else 'needs_improvement'
            )
            scores[target_dir] = {
                'score': score,
                'violations_count': len(violations) if violations else 0,
                'errors_count': len(errors) if errors else 0,
                'status': status
            }
            print(f"    {target_dir}/: {score}/100")
        except ImportError:
            print(f"    ⚠️  CodeHealthAnalyzer not available for {target_dir}")
        except Exception as e:
            # pylint: disable=broad-exception-caught
            print(f"    ⚠️  Error analyzing {target_dir}: {e}")

    return scores


def check_linting():
    """Run linting checks."""
    print("🔍 Running linting checks...")
    results = {}

    # Ruff check
    returncode, stdout, _ = run_command(
        "python3 -m ruff check function_app/ --output-format=json",
        check=False,
        timeout=60
    )
    ruff_issues = []
    if returncode == 0 and stdout:
        try:
            ruff_issues = json.loads(stdout) if stdout else []
        except json.JSONDecodeError:
            pass
    results['ruff'] = {
        'passed': returncode == 0 and not ruff_issues,
        'issues': ruff_issues[:20],  # Limit to 20 issues
        'count': len(ruff_issues)
    }

    # Pyright with timeout
    stdout = ""
    returncode = 1
    try:
        import subprocess as sp
        proc = sp.Popen(
            ["python3", "-m", "pyright", "function_app/", "--outputjson"],
            stdout=sp.PIPE,
            stderr=sp.PIPE,
            text=True
        )
        try:
            stdout, _stderr = proc.communicate(timeout=30)
            returncode = proc.returncode
            stdout = stdout or ""
        except sp.TimeoutExpired:
            proc.kill()
            proc.wait()
            stdout = "Timeout: Pyright took longer than 30 seconds"
    except (OSError, ValueError, TypeError) as e:
        # pylint: disable=broad-exception-caught
        stdout = f"Error: {e}"

    pyright_issues = []
    if stdout and not stdout.startswith("Timeout:") and not stdout.startswith("Error:"):
        try:
            pyright_data = json.loads(stdout)
            pyright_issues = pyright_data.get('generalDiagnostics', [])[:20]
        except (json.JSONDecodeError, KeyError):
            pass

    results['pyright'] = {
        'passed': returncode == 0 and not pyright_issues,
        'issues': pyright_issues,
        'count': len(pyright_issues)
    }

    return results


def detect_performance_patterns():
    """Detect performance anti-patterns."""
    print("⚡ Detecting performance anti-patterns...")
    patterns = {
        'iterrows': {
            'pattern': r'\.iterrows\(\)',
            'severity': 'Critical',
            'description': 'iterrows() usage (10-100× slower)',
            'fix': 'Use itertuples() or vectorized operations'
        },
        'apply_on_dataframe': {
            'pattern': r'\.apply\([^,)]+\)',
            'severity': 'Moderate',
            'description': 'apply() on DataFrame (row-by-row)',
            'fix': 'Use vectorized NumPy/pandas operations'
        },
    }

    findings = []
    for pattern_name, pattern_info in patterns.items():
        regex = re.compile(pattern_info['pattern'], re.MULTILINE | re.DOTALL)
        for py_file in FUNCTION_APP_DIR.rglob("*.py"):
            try:
                content = py_file.read_text(encoding='utf-8')
                matches = regex.finditer(content)
                for match in matches:
                    line_num = content[:match.start()].count('\n') + 1
                    findings.append({
                        'file': str(py_file.relative_to(PROJECT_ROOT)),
                        'line': line_num,
                        'pattern': pattern_name,
                        'severity': pattern_info['severity'],
                        'description': pattern_info['description'],
                        'fix': pattern_info['fix']
                    })
            except (OSError, UnicodeDecodeError):
                continue

    print(f"  Found {len(findings)} performance issues")
    return findings


def generate_report(test_results, coverage_data, quality_scores, linting_results, performance_findings):
    """Generate comprehensive markdown report."""
    test_passed, test_output, test_error, _coverage = test_results
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    report_lines = [
        "# Comprehensive Project Report",
        "",
        f"**Generated:** {timestamp}",
        "",
        "> This report combines test execution, code coverage, quality analysis,",
        "> linting results, and performance pattern detection.",
        "",
        "---",
        "",
        "## Executive Summary",
        "",
    ]

    # Overall status
    lint_passed = linting_results['ruff']['passed'] and linting_results['pyright']['passed']
    critical_issues = len([f for f in performance_findings if f['severity'] == 'Critical'])
    main_score = quality_scores.get('function_app', {}).get('score', 0)

    if test_passed and lint_passed and critical_issues == 0 and main_score >= 80:
        overall_status = "✅ **Overall Status: Excellent**"
    elif test_passed and lint_passed and critical_issues == 0:
        overall_status = "🟡 **Overall Status: Good**"
    else:
        overall_status = "🔴 **Overall Status: Needs Attention**"

    report_lines.extend([
        overall_status,
        "",
        f"- **Test Execution**: {'✅ Passed' if test_passed else '❌ Failed'}",
        f"- **Code Coverage**: {coverage_data.get('totals', {}).get('percent_covered', 0):.1f}%",
        f"- **Linting**: {'✅ Passed' if lint_passed else '❌ Issues found'}",
        f"- **Performance Issues**: {critical_issues} Critical",
        f"- **Code Quality (function_app/)**: {main_score}/100",
        "",
        "---",
        "",
    ])

    # Test Results
    report_lines.extend([
        "## Test Execution",
        "",
        f"**Status**: {'✅ PASSED' if test_passed else '❌ FAILED'}",
        "",
    ])

    if coverage_data and 'totals' in coverage_data:
        totals = coverage_data['totals']
        report_lines.extend([
            "### Code Coverage",
            "",
            f"- **Statements**: {totals.get('num_statements', 0)}",
            f"- **Covered**: {totals.get('covered_lines', 0)}",
            f"- **Coverage**: {totals.get('percent_covered', 0):.1f}%",
            "",
        ])

    report_lines.append("---")
    report_lines.append("")

    # Code Quality Analysis
    report_lines.extend([
        "## Code Quality Analysis",
        "",
        "Quality scores (0-100) from CodeHealthAnalyzer:",
        "",
    ])

    for dir_name in ['function_app', 'tests', 'scripts']:
        if dir_name in quality_scores:
            score_data = quality_scores[dir_name]
            status_emoji = (
                "🟢" if score_data['status'] == 'excellent'
                else "🟡" if score_data['status'] == 'good'
                else "🔴"
            )
            status_text = score_data['status'].replace('_', ' ').title()
            report_lines.extend([
                f"### {dir_name.title()} (`{dir_name}/`)",
                "",
                f"{status_emoji} **Score:** {score_data['score']}/100 ({status_text})",
                f"- Violations: {score_data['violations_count']}",
                f"- Errors: {score_data['errors_count']}",
                "",
            ])

    report_lines.append("---")
    report_lines.append("")

    # Linting Results
    report_lines.extend([
        "## Linting Results",
        "",
    ])

    ruff_status = "✅ Passed" if linting_results['ruff']['passed'] else f"❌ {linting_results['ruff']['count']} issues"
    pyright_status = "✅ Passed" if linting_results['pyright']['passed'] else f"❌ {linting_results['pyright']['count']} issues"

    report_lines.extend([
        f"- **Ruff**: {ruff_status}",
        f"- **Pyright**: {pyright_status}",
        "",
        "---",
        "",
    ])

    # Performance Issues
    if performance_findings:
        report_lines.extend([
            "## Performance Anti-Patterns",
            "",
            "| File | Line | Issue | Severity | Fix |",
            "|------|------|-------|----------|-----|",
        ])

        for finding in sorted(performance_findings, key=lambda x: (x['severity'] == 'Critical', x['file'])):
            severity_emoji = "🔴" if finding['severity'] == 'Critical' else "🟡"
            report_lines.append(
                f"| `{finding['file']}` | {finding['line']} | "
                f"{finding['description']} | {severity_emoji} {finding['severity']} | "
                f"{finding['fix']} |"
            )

        report_lines.append("")
        report_lines.append("---")
        report_lines.append("")

    # Recommendations
    report_lines.extend([
        "## Recommendations",
        "",
    ])

    recommendations = []
    if not test_passed:
        recommendations.append("1. **Fix failing tests**: Review test output and address issues.")
    if not lint_passed:
        recommendations.append("2. **Fix linting errors**: Run `make lint-fix` to auto-fix issues.")
    if critical_issues > 0:
        recommendations.append(f"3. **Address {critical_issues} critical performance issue(s)**: High cost impact.")
    if main_score < 80:
        recommendations.append("4. **Improve code quality score**: Focus on reducing violations.")

    if not recommendations:
        recommendations.append("✅ **No critical issues found**. Code quality is excellent!")

    report_lines.extend([rec + "\n" for rec in recommendations])

    # Write report
    report_content = "\n".join(report_lines)
    with open(REPORT_FILE, 'w', encoding='utf-8') as f:
        f.write(report_content)

    print(f"✅ Comprehensive report written to: {REPORT_FILE}")
    return report_content


def main():
    """Main execution."""
    print("📝 Generating comprehensive project report...")
    print()

    try:
        # Run tests
        test_results = run_tests()
        print()

        # Get code quality scores
        quality_scores = get_code_quality_scores()
        print()

        # Check linting
        linting_results = check_linting()
        print()

        # Detect performance patterns
        performance_findings = detect_performance_patterns()
        print()

        # Extract coverage from test results
        coverage_data = test_results[3] if len(test_results) > 3 else {}

        # Generate report
        generate_report(test_results, coverage_data, quality_scores, linting_results, performance_findings)

    except Exception as e:
        # pylint: disable=broad-exception-caught
        print(f"⚠️  Error generating report: {e}")
        import traceback
        traceback.print_exc()

    return 0


if __name__ == "__main__":
    sys.exit(main())
