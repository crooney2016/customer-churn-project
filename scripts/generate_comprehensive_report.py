#!/usr/bin/env python3
"""
Generate comprehensive project report by combining:
- Test suite report (test execution, coverage, quality scores)
- Code review report (linting, performance, code quality analysis)

Deduplicates and logically orders content for a unified view.
"""

import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List

PROJECT_ROOT = Path(__file__).parent.parent
OUTPUT_DIR = PROJECT_ROOT / "docs"
OUTPUT_DIR.mkdir(exist_ok=True)

TEST_REPORT = OUTPUT_DIR / "test-suite-report.md"
CODE_REVIEW_REPORT = OUTPUT_DIR / "code-review.md"
COMPREHENSIVE_REPORT = OUTPUT_DIR / "comprehensive-report.md"


def read_report_sections(file_path: Path) -> Dict[str, List[str]]:
    """Read a markdown report and extract sections."""
    if not file_path.exists():
        return {}

    content = file_path.read_text(encoding='utf-8')
    lines = content.split('\n')

    sections = {}
    current_section = None
    current_content = []

    for line in lines:
        # Check for section headers (## or ###)
        if line.startswith('##'):
            if current_section:
                sections[current_section] = current_content
            current_section = line.strip()
            current_content = [line]
        elif current_section:
            current_content.append(line)
        elif not current_section and line.strip():
            # Content before first section
            if 'header' not in sections:
                sections['header'] = []
            sections['header'].append(line)

    # Add last section
    if current_section:
        sections[current_section] = current_content

    return sections


def merge_sections(
    test_sections: Dict[str, List[str]],
    review_sections: Dict[str, List[str]]
) -> List[str]:
    """Merge sections from both reports, deduplicating and ordering logically."""
    merged = []

    # Header with timestamp
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    merged.extend([
        "# Comprehensive Project Report",
        "",
        f"**Generated:** {timestamp}",
        "",
        "> This comprehensive report combines:",
        "> - Test suite report (execution results, coverage, quality scores)",
        "> - Code review report (linting, performance analysis, recommendations)",
        "",
        "---",
        "",
    ])

    # Executive Summary (from code review if available)
    if '## Executive Summary' in review_sections:
        merged.extend(review_sections['## Executive Summary'])
        merged.append("")
    elif '## Summary' in test_sections:
        # Fallback to test summary
        merged.extend(test_sections['## Summary'])
        merged.append("")

    # Test Execution Status (from test report)
    if '### Test Execution:' in str(test_sections):
        for section_key in test_sections:
            if 'Test Execution' in section_key or 'Test Execution Output' in section_key:
                if section_key.startswith('###'):
                    merged.extend([
                        "## Test Execution",
                        "",
                    ])
                    # Extract content without the header
                    content = '\n'.join(test_sections[section_key])
                    for line in content.split('\n')[1:]:  # Skip header line
                        merged.append(line)
                    merged.append("")

    # Code Coverage (from test report)
    if '### Code Coverage' in str(test_sections):
        for section_key in test_sections:
            if 'Coverage' in section_key:
                merged.extend(test_sections[section_key])
                merged.append("")
                merged.append("---")
                merged.append("")
                break

    # Code Quality Analysis (combine both)
    merged.extend([
        "## Code Quality Analysis",
        "",
    ])

    # Quality scores from test report
    if '## Code Quality Analysis' in test_sections:
        test_quality = test_sections['## Code Quality Analysis']
        # Skip the header line
        for line in test_quality[1:]:
            if line.strip() and not line.startswith('#'):
                merged.append(line)
        merged.append("")

    # Quality analysis details from code review
    if '## Code Quality Analysis' in review_sections:
        review_quality = review_sections['## Code Quality Analysis']
        for line in review_quality:
            if line.strip() and not line.startswith('#'):
                merged.append(line)
        merged.append("")

    merged.extend([
        "---",
        "",
    ])

    # Linting Results (from code review)
    if '## Linting Results' in review_sections:
        merged.extend(review_sections['## Linting Results'])
        merged.append("")
        merged.append("---")
        merged.append("")

    # Performance Issues (from code review)
    if '## Performance Anti-Patterns' in review_sections:
        merged.extend(review_sections['## Performance Anti-Patterns'])
        merged.append("")
        merged.append("---")
        merged.append("")

    # Recommendations (from code review)
    if '## Recommendations' in review_sections:
        merged.extend(review_sections['## Recommendations'])
        merged.append("")
        merged.append("---")
        merged.append("")

    # Append test output details at the end (if not already included)
    if '## Test Execution Output' in test_sections:
        merged.extend([
            "## Detailed Test Output",
            "",
        ])
        merged.extend(test_sections['## Test Execution Output'])
        merged.append("")

    # Footer with source information
    merged.extend([
        "---",
        "",
        "## Report Sources",
        "",
        f"- **Test Suite Report**: `{TEST_REPORT.name}`",
        f"- **Code Review Report**: `{CODE_REVIEW_REPORT.name}`",
        "",
        "> Regenerate reports individually:",
        "> - `make test-report` - Test suite report",
        "> - `make code-review` - Code review report",
        "> - `make comprehensive-report` - Combined report",
        "",
        "> All reports are saved in the `docs/` directory.",
        "",
    ])

    return merged


def generate_comprehensive_report(force_regenerate: bool = False):
    """Generate comprehensive report by combining test and code review reports."""
    print("📋 Generating comprehensive project report...")
    print()

    # Check if source reports exist
    if not TEST_REPORT.exists():
        print(f"⚠️  Test report not found: {TEST_REPORT}")
        print("   Run: make test-report")
        if not force_regenerate:
            return False
        print("   Generating test report now...")
        subprocess.run(
            [sys.executable, PROJECT_ROOT / "scripts" / "generate_test_suite_report.py"],
            check=False
        )

    if not CODE_REVIEW_REPORT.exists():
        print(f"⚠️  Code review report not found: {CODE_REVIEW_REPORT}")
        print("   Run: make code-review")
        if not force_regenerate:
            return False
        print("   Generating code review report now...")
        subprocess.run(
            [sys.executable, PROJECT_ROOT / "scripts" / "generate_code_review_report.py"],
            check=False
        )

    # Read both reports
    print("📖 Reading test suite report...")
    test_sections = read_report_sections(TEST_REPORT)

    print("📖 Reading code review report...")
    review_sections = read_report_sections(CODE_REVIEW_REPORT)

    # Merge sections
    print("🔗 Merging reports...")
    merged_content = merge_sections(test_sections, review_sections)

    # Write comprehensive report
    report_content = '\n'.join(merged_content)
    with open(COMPREHENSIVE_REPORT, 'w', encoding='utf-8') as f:
        f.write(report_content)

    test_section_count = len([s for s in test_sections if s.startswith('##')])
    review_section_count = len([s for s in review_sections if s.startswith('##')])
    print(f"✅ Comprehensive report written to: {COMPREHENSIVE_REPORT}")
    print()
    print("   Report combines:")
    print(f"   - {test_section_count} sections from test report")
    print(f"   - {review_section_count} sections from code review")
    print()
    print("   Reports saved in docs/ directory:")
    print("   - docs/test-suite-report.md")
    print("   - docs/code-review.md")
    print("   - docs/comprehensive-report.md")
    print()

    return True


def main():
    """Main execution."""
    parser = argparse.ArgumentParser(
        description='Generate comprehensive project report from test and code review reports'
    )
    parser.add_argument(
        '--force-regenerate',
        action='store_true',
        help='Automatically regenerate missing source reports'
    )
    args = parser.parse_args()

    try:
        success = generate_comprehensive_report(force_regenerate=args.force_regenerate)
        if not success:
            print("⚠️  Comprehensive report may be incomplete")
    except Exception as e:
        # pylint: disable=broad-exception-caught
        print(f"⚠️  Error generating comprehensive report: {e}")
        print("   Report may be incomplete")

    # Always return 0 - report generation should not fail the build
    return 0


if __name__ == "__main__":
    sys.exit(main())
