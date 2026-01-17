#!/usr/bin/env python3
"""
Generate code review report based on .cursor/rules/prompts/code-review.md guidelines.

Performs automated code review including:
- Linting checks
- Code quality analysis
- Performance anti-pattern detection
- Rule compliance checking
- Structured findings report
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
REPORT_FILE = OUTPUT_DIR / "code-review.md"


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


def check_linting():
    """Run linting checks and return results."""
    print("🔍 Running linting checks...")
    results = {}

    # Ruff check
    returncode, stdout, _ = run_command(
        "python3 -m ruff check function_app/ --output-format=json",
        check=False
    )
    if returncode == 0:
        try:
            ruff_issues = json.loads(stdout) if stdout else []
        except json.JSONDecodeError:
            ruff_issues = []
    else:
        ruff_issues = []
    results['ruff'] = {
        'passed': returncode == 0 and not ruff_issues,
        'issues': ruff_issues,
        'output': stdout
    }

    # Pyright type checking (with timeout to prevent hanging)
    # Use subprocess with timeout instead of shell command
    pyright_issues = []
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
            stdout, _stderr = proc.communicate(timeout=30)  # 30 second timeout
            returncode = proc.returncode
            stdout = stdout or ""
        except sp.TimeoutExpired:
            proc.kill()
            proc.wait()
            returncode = 1
            stdout = "Timeout: Pyright took longer than 30 seconds"
            print("⚠️  Pyright timed out after 30 seconds, skipping detailed analysis")
    except (OSError, ValueError, TypeError) as e:
        # pylint: disable=broad-exception-caught
        # Catch subprocess-related errors
        returncode = 1
        stdout = f"Error running Pyright: {e}"
        print(f"⚠️  Error running Pyright: {e}")

    try:
        timeout_msg = "Timeout: Pyright took longer than 30 seconds"
        if stdout and stdout != timeout_msg and not stdout.startswith("Error running"):
            pyright_data = json.loads(stdout)
            pyright_issues = pyright_data.get('generalDiagnostics', [])
        else:
            pyright_issues = []
    except (json.JSONDecodeError, KeyError):
        pyright_issues = []
    try:
        if stdout and not stdout.startswith("Timeout:") and not stdout.startswith("Error running"):
            pyright_data = json.loads(stdout)
            pyright_issues = pyright_data.get('generalDiagnostics', [])
        else:
            pyright_issues = []
    except (json.JSONDecodeError, KeyError):
        pyright_issues = []
    results['pyright'] = {
        'passed': returncode == 0 and not pyright_issues,
        'issues': pyright_issues,
        'output': stdout
    }

    return results


def detect_performance_anti_patterns():
    """Detect performance anti-patterns in function_app/."""
    print("⚡ Detecting performance anti-patterns...")
    patterns = {
        'iterrows': {
            'pattern': r'\.iterrows\(\)',
            'severity': 'Critical',
            'description': 'iterrows() usage (10-100× slower than alternatives)',
            'fix': 'Use itertuples() or vectorized operations'
        },
        'apply_on_dataframe': {
            'pattern': r'\.apply\([^,)]+\)',
            'severity': 'Moderate',
            'description': 'apply() on DataFrame (row-by-row execution)',
            'fix': 'Use vectorized NumPy/pandas operations'
        },
        'iloc_loop': {
            'pattern': r'for\s+\w+\s+in\s+range\(len\([^)]+\)\):.*\.iloc\[',
            'severity': 'Moderate',
            'description': 'Index-based loops with iloc',
            'fix': 'Use itertuples() or vectorize'
        },
        'multiple_concat': {
            'pattern': r'pd\.concat\(.*\).*pd\.concat\(',
            'severity': 'Minor',
            'description': 'Multiple sequential concat operations',
            'fix': 'Combine in single concat operation'
        }
    }

    findings = []
    for pattern_name, pattern_info in patterns.items():
        regex = re.compile(pattern_info['pattern'], re.MULTILINE | re.DOTALL)
        for py_file in FUNCTION_APP_DIR.rglob("*.py"):
            try:
                content = py_file.read_text(encoding='utf-8')
                matches = regex.finditer(content)
                for match in matches:
                    # Get line number
                    line_num = content[:match.start()].count('\n') + 1
                    findings.append({
                        'file': str(py_file.relative_to(PROJECT_ROOT)),
                        'line': line_num,
                        'pattern': pattern_name,
                        'severity': pattern_info['severity'],
                        'description': pattern_info['description'],
                        'fix': pattern_info['fix'],
                        'code_snippet': content.split('\n')[line_num - 1].strip()
                    })
            except (OSError, UnicodeDecodeError):
                # pylint: disable=broad-exception-caught
                # Skip files that can't be read or decoded
                continue

    return findings


def get_code_quality_analysis():
    """Get code quality scores using CodeHealthAnalyzer."""
    print("📊 Analyzing code quality...")
    try:
        from codehealthanalyzer import CodeAnalyzer

        analyzer = CodeAnalyzer(str(FUNCTION_APP_DIR))
        score = analyzer.get_quality_score()
        violations = analyzer.analyze_violations()
        errors = analyzer.analyze_errors()

        return {
            'score': score,
            'status': (
                'excellent' if score >= 80
                else 'good' if score >= 60
                else 'needs_improvement'
            ),
            'violations_count': len(violations) if violations else 0,
            'errors_count': len(errors) if errors else 0,
            'violations': violations[:10] if violations else [],  # Limit for report
            'errors': errors[:10] if errors else []  # Limit for report
        }
    except ImportError:
        print("⚠️  CodeHealthAnalyzer not available")
        return None
    except (AttributeError, RuntimeError, ValueError) as e:
        # pylint: disable=broad-exception-caught
        # CodeAnalyzer may raise various exceptions during analysis
        print(f"⚠️  Error analyzing code quality: {e}")
        return None


def generate_report(
    linting_results: Dict,
    performance_findings: List[Dict],
    quality_analysis: Optional[Dict]
):
    """Generate the code review markdown report."""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    report_lines = [
        "# Code Review Report",
        "",
        f"**Generated:** {timestamp}",
        "",
        "> This report was generated using automated analysis based on",
        "> `.cursor/rules/prompts/code-review.md` guidelines.",
        "",
        "---",
        "",
        "## Executive Summary",
        "",
    ]

    # Overall status
    lint_passed = linting_results['ruff']['passed'] and linting_results['pyright']['passed']
    critical_issues = len([f for f in performance_findings if f['severity'] == 'Critical'])
    moderate_issues = len([f for f in performance_findings if f['severity'] == 'Moderate'])

    quality_score_ok = quality_analysis and quality_analysis['score'] >= 80
    if lint_passed and critical_issues == 0 and quality_score_ok:
        overall_status = "✅ **Overall Status: Excellent**"
    elif lint_passed and critical_issues == 0:
        overall_status = "🟡 **Overall Status: Good**"
    else:
        overall_status = "🔴 **Overall Status: Needs Attention**"

    quality_score_text = (
        f"{quality_analysis['score']}/100 ({quality_analysis['status']})"
        if quality_analysis else "N/A"
    )
    lint_status = '✅ Passed' if lint_passed else '❌ Issues found'
    perf_issues_text = f"{critical_issues} Critical, {moderate_issues} Moderate"
    report_lines.extend([
        overall_status,
        "",
        f"- **Linting**: {lint_status}",
        f"- **Performance Issues**: {perf_issues_text}",
        f"- **Code Quality Score**: {quality_score_text}",
        "",
        "---",
        "",
    ])

    # Linting Results
    report_lines.extend([
        "## Linting Results",
        "",
    ])

    # Ruff
    ruff_status = "✅ Passed" if linting_results['ruff']['passed'] else "❌ Issues Found"
    ruff_issues_count = len(linting_results['ruff']['issues'])
    report_lines.extend([
        f"### Ruff: {ruff_status}",
        "",
        f"Issues found: {ruff_issues_count}",
        "",
    ])

    if ruff_issues_count > 0 and ruff_issues_count <= 20:
        report_lines.append("| File | Line | Code | Message |")
        report_lines.append("|------|------|------|---------|")
        for issue in linting_results['ruff']['issues'][:20]:
            file_path = issue.get('filename', 'unknown').replace(str(PROJECT_ROOT) + '/', '')
            line = issue.get('location', {}).get('row', '?')
            code = issue.get('code', '?')
            msg = issue.get('message', '')
            report_lines.append(f"| `{file_path}` | {line} | {code} | {msg} |")
        report_lines.append("")

    # Pyright
    pyright_status = "✅ Passed" if linting_results['pyright']['passed'] else "❌ Issues Found"
    pyright_issues_count = len(linting_results['pyright']['issues'])
    report_lines.extend([
        f"### Pyright: {pyright_status}",
        "",
        f"Issues found: {pyright_issues_count}",
        "",
    ])

    if pyright_issues_count > 0 and pyright_issues_count <= 20:
        report_lines.append("| File | Line | Message |")
        report_lines.append("|------|------|---------|")
        for issue in linting_results['pyright']['issues'][:20]:
            file_path = issue.get('file', 'unknown').replace(str(PROJECT_ROOT) + '/', '')
            line = issue.get('range', {}).get('start', {}).get('line', '?')
            msg = issue.get('message', '')
            report_lines.append(f"| `{file_path}` | {line} | {msg} |")
        report_lines.append("")

    report_lines.append("---")
    report_lines.append("")

    # Performance Issues
    if performance_findings:
        report_lines.extend([
            "## Performance Anti-Patterns",
            "",
            "> Performance issues impact Azure Consumption plan costs.",
            "",
            "| File | Line | Issue | Severity | Recommended Fix |",
            "|------|------|-------|----------|----------------|",
        ])

        for finding in sorted(
            performance_findings,
            key=lambda x: (x['severity'] == 'Critical', x['severity'] == 'Moderate', x['file'])
        ):
            severity_emoji = (
                "🔴" if finding['severity'] == 'Critical'
                else "🟡" if finding['severity'] == 'Moderate'
                else "🟢"
            )
            report_lines.append(
                f"| `{finding['file']}` | {finding['line']} | "
                f"{finding['description']} | {severity_emoji} {finding['severity']} | "
                f"{finding['fix']} |"
            )

        report_lines.append("")
        report_lines.append("---")
        report_lines.append("")

    # Code Quality Analysis
    if quality_analysis:
        report_lines.extend([
            "## Code Quality Analysis",
            "",
            f"**Quality Score:** {quality_analysis['score']}/100 "
            f"({quality_analysis['status'].replace('_', ' ').title()})",
            "",
            f"- Violations: {quality_analysis['violations_count']}",
            f"- Errors: {quality_analysis['errors_count']}",
            "",
        ])

        if quality_analysis['violations_count'] > 0:
            report_lines.extend([
                "### Top Violations",
                "",
            ])
            for violation in quality_analysis['violations'][:10]:
                report_lines.append(f"- {violation}")
            report_lines.append("")

        report_lines.append("---")
        report_lines.append("")

    # Recommendations
    report_lines.extend([
        "## Recommendations",
        "",
    ])

    recommendations = []
    if not lint_passed:
        recommendations.append(
            "1. **Fix linting errors**: Run `make lint-fix` to automatically fix "
            "most issues, then review remaining errors manually."
        )
    if critical_issues > 0:
        recommendations.append(
            f"2. **Address {critical_issues} critical performance issue(s)**: "
            "These have the highest impact on Azure costs."
        )
    if moderate_issues > 0:
        recommendations.append(
            f"3. **Review {moderate_issues} moderate performance issue(s)**: "
            "These can be addressed to further optimize costs."
        )
    if quality_analysis and quality_analysis['score'] < 80:
        recommendations.append(
            "4. **Improve code quality score**: Focus on reducing violations "
            "and errors identified by CodeHealthAnalyzer."
        )

    if not recommendations:
        recommendations.append(
            "✅ **No critical issues found**. Code quality is excellent!"
        )

    report_lines.extend([rec + "\n" for rec in recommendations])
    report_lines.append("---")
    report_lines.append("")

    report_content = "\n".join(report_lines)

    # Write report
    with open(REPORT_FILE, 'w', encoding='utf-8') as f:
        f.write(report_content)

    print(f"✅ Report written to: {REPORT_FILE}")
    return report_content


def main():
    """Main execution."""
    try:
        print("📝 Generating code review report...")
        print()

        # Run linting checks
        try:
            linting_results = check_linting()
        except Exception as e:
            # pylint: disable=broad-exception-caught
            print(f"⚠️  Error during linting checks: {e}")
            linting_results = {
                'ruff': {'passed': False, 'issues': []},
                'pyright': {'passed': False, 'issues': []}
            }
        print()

        # Detect performance anti-patterns
        try:
            performance_findings = detect_performance_anti_patterns()
            print(f"  Found {len(performance_findings)} performance issues")
        except Exception as e:
            # pylint: disable=broad-exception-caught
            print(f"⚠️  Error detecting performance patterns: {e}")
            performance_findings = []
        print()

        # Get code quality analysis
        try:
            quality_analysis = get_code_quality_analysis()
            if quality_analysis:
                print(f"  Quality score: {quality_analysis['score']}/100")
        except Exception as e:
            # pylint: disable=broad-exception-caught
            print(f"⚠️  Error analyzing code quality: {e}")
            quality_analysis = None
        print()

        # Generate report
        try:
            generate_report(linting_results, performance_findings, quality_analysis)
        except Exception as e:
            # pylint: disable=broad-exception-caught
            print(f"⚠️  Error generating report: {e}")
            print("   Report may be incomplete")

    except Exception as e:
        # pylint: disable=broad-exception-caught
        print(f"❌ Fatal error in code review: {e}")
        print("   Attempting to generate partial report...")

    # Always return 0 - report generation should not fail the build
    return 0


if __name__ == "__main__":
    sys.exit(main())
