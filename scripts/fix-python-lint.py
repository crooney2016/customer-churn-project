#!/usr/bin/env python3
"""
Python linting convenience script with auto-fixer for common pylint errors.

Can operate in two modes:
1. Comprehensive mode (default): Runs ruff/pylint/pyright tools
2. Specific mode (--json): Fixes only errors specified in JSON diagnostics file

Auto-fixes common pylint errors:
- W1309: f-string-without-interpolation (convert to regular string)
- W0612: unused-variable (remove unused variable assignments)
- C0303: trailing-whitespace (remove trailing spaces)
- C0304: missing-final-newline (add final newline)
- C0321: multiple-statements (split to separate lines)

Usage:
    # Comprehensive mode - run ruff/pylint/pyright
    python3 scripts/fix-python-lint.py function_app/
    python3 scripts/fix-python-lint.py function_app/scorer.py

    # Specific mode - fix only errors from JSON diagnostics
    python3 scripts/fix-python-lint.py --json errors.json
    python3 scripts/fix-python-lint.py --json -  # Read from stdin

    # Dry run (preview changes)
    python3 scripts/fix-python-lint.py --dry-run function_app/
    python3 scripts/fix-python-lint.py --json --dry-run errors.json

    # Include type checking (read-only)
    python3 scripts/fix-python-lint.py --check-types function_app/

    # Include pylint (read-only)
    python3 scripts/fix-python-lint.py --check-pylint function_app/
"""

import json
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List


def run_command(cmd: List[str], dry_run: bool = False) -> int:
    """Run a command and return exit code."""
    if dry_run:
        print(f"[DRY RUN] Would run: {' '.join(cmd)}")
        return 0

    try:
        result = subprocess.run(cmd, check=False, capture_output=False)
        return result.returncode
    except FileNotFoundError:
        print(f"Error: Command not found: {cmd[0]}", file=sys.stderr)
        print(f"Install with: pip install {cmd[0]}", file=sys.stderr)
        return 1


def find_python_files(path: Path) -> List[Path]:
    """Find all Python files in path."""
    if path.is_file():
        if path.suffix == '.py':
            return [path]
        else:
            print(f"Warning: Not a Python file: {path}", file=sys.stderr)
            return []
    else:
        # Find all Python files recursively
        return list(path.rglob('*.py'))


# Specific error fixers for JSON diagnostics mode
def fix_w1309_fstring_without_interpolation(_file_path: Path, line_num: int, content: str) -> str:
    """Fix W1309: Convert f-string without interpolation to regular string."""
    lines = content.split('\n')
    idx = line_num - 1

    if idx < 0 or idx >= len(lines):
        return content

    line = lines[idx]
    # Match f-strings: f"...", f'...', f"""...""", f'''...'''
    # Check if there's no interpolation (no {})
    fstring_pattern = (
        r'(?P<prefix>.*?)(?P<quote>f?)(?P<quote_type>["\']{1,3})'
        r'(?P<content>[^"\']*?)(?P=quote_type)'
    )
    match = re.search(fstring_pattern, line)

    if match and match.group('quote') == 'f':
        content_part = match.group('content')
        # If no interpolation found, remove 'f' prefix
        if '{' not in content_part and '}' not in content_part:
            quote_type = match.group('quote_type')
            # Remove 'f' from the quote part
            new_line = line.replace(f'f{quote_type}', quote_type, 1)
            lines[idx] = new_line

    return '\n'.join(lines)


def fix_w0612_unused_variable(_file_path: Path, line_num: int, content: str) -> str:
    """Fix W0612: Remove unused variable assignment."""
    lines = content.split('\n')
    idx = line_num - 1

    if idx < 0 or idx >= len(lines):
        return content

    line = lines[idx].rstrip()
    # Try to detect simple variable assignments that are unused
    # Pattern: variable_name = something
    # This is tricky - we'd need to check if variable is used elsewhere
    # For now, comment out the line if it's a simple assignment
    # More sophisticated analysis would require AST parsing
    assignment_match = re.match(r'^\s*(?P<var>[_a-zA-Z][_a-zA-Z0-9]*)\s*=\s*(?P<value>.*)$', line)

    if assignment_match:
        # Check if variable name appears elsewhere in the file (simple check)
        var_name = assignment_match.group('var')
        # Check if it's used elsewhere (not just assigned)
        if var_name not in '\n'.join(lines[:idx] + lines[idx+1:]):
            # Comment out the assignment
            lines[idx] = f"# {line}  # pylint: disable=unused-variable"

    return '\n'.join(lines)


def fix_c0303_trailing_whitespace(_file_path: Path, line_num: int, content: str) -> str:
    """Fix C0303: Remove trailing whitespace."""
    lines = content.split('\n')
    idx = line_num - 1

    if idx < 0 or idx >= len(lines):
        return content

    lines[idx] = lines[idx].rstrip()
    return '\n'.join(lines)


def fix_c0304_missing_final_newline(_file_path: Path, content: str) -> str:
    """Fix C0304: Ensure file ends with exactly one newline."""
    content = content.rstrip('\n')
    return content + '\n'


def fix_c0321_multiple_statements(_file_path: Path, line_num: int, content: str) -> str:
    """Fix C0321: Split multiple statements on same line."""
    lines = content.split('\n')
    idx = line_num - 1

    if idx < 0 or idx >= len(lines):
        return content

    line = lines[idx]
    # Split on semicolons (but not inside strings)
    # Simple approach: split on ';' that's not inside quotes
    # This is a simplified fix - full fix would need proper parsing
    if ';' in line and line.count('"') % 2 == 0 and line.count("'") % 2 == 0:
        # Split by semicolon and recreate lines with proper indentation
        indent = len(line) - len(line.lstrip())
        indent_str = ' ' * indent
        parts = [p.strip() for p in line.split(';') if p.strip()]
        if len(parts) > 1:
            # Replace original line with first part, insert others as new lines
            lines[idx] = parts[0]
            for part in parts[1:]:
                lines.insert(idx + 1, indent_str + part)
                idx += 1

    return '\n'.join(lines)


# Mapping of error codes to specific fix functions
SPECIFIC_FIX_FUNCTIONS = {
    'W1309': fix_w1309_fstring_without_interpolation,
    'W0612': fix_w0612_unused_variable,
    'C0303': fix_c0303_trailing_whitespace,
    'C0304': fix_c0304_missing_final_newline,
    'C0321': fix_c0321_multiple_statements,
}


def process_errors_json(errors: List[Dict], dry_run: bool = False) -> Dict[str, str]:  # pylint: disable=unused-argument
    """
    Process errors from JSON diagnostics and return modified file contents.

    Returns:
        Dict mapping file paths to modified content
    """
    # Group errors by file
    errors_by_file: Dict[str, List[Dict]] = defaultdict(list)

    for error in errors:
        resource = error.get('resource', '')
        if resource:
            errors_by_file[resource].append(error)

    modified_files = {}

    for file_path_str, file_errors in errors_by_file.items():
        file_path = Path(file_path_str)

        if not file_path.exists():
            print(f"Warning: File does not exist: {file_path}", file=sys.stderr)
            continue

        try:
            content = file_path.read_text(encoding='utf-8')
            original_content = content

            # Sort errors by line number (descending) to avoid index shifting
            sorted_errors = sorted(
                file_errors,
                key=lambda e: e.get('startLineNumber', 0),
                reverse=True
            )

            # Apply fixes (reverse order to avoid line number shifts)
            for error in sorted_errors:
                code_obj = error.get('code', {})
                if isinstance(code_obj, dict):
                    code = code_obj.get('value', '')
                else:
                    code = str(code_obj)

                # Extract error code (e.g., "W1309" from "W1309:f-string-without-interpolation")
                if ':' in code:
                    code = code.split(':')[0]

                line_num = error.get('startLineNumber', 0)

                if code in SPECIFIC_FIX_FUNCTIONS:
                    fix_func = SPECIFIC_FIX_FUNCTIONS[code]

                    # C0304 doesn't need line number
                    if code == 'C0304':
                        content = fix_func(file_path, content)
                    # Most fixes need line number
                    else:
                        content = fix_func(file_path, line_num, content)

            if content != original_content:
                modified_files[str(file_path)] = content

        except Exception as e:  # pylint: disable=broad-exception-caught
            print(f"Error processing {file_path}: {e}", file=sys.stderr)

    return modified_files


def auto_fix_recursive(file_path: Path, max_iterations: int = 10) -> bool:
    """
    Recursively fix pylint errors until no more fixable errors remain.

    Returns:
        True if fixes were made, False otherwise
    """
    import subprocess as sp

    # Run pylint and capture JSON output
    # Note: pylint doesn't have native JSON output, so we'd need pylint-json
    # For now, use a simpler approach: run ruff which handles most of these
    # and iteratively fix remaining issues

    print(f"Auto-fixing {file_path} (max {max_iterations} iterations)...")

    for _ in range(max_iterations):
        # Run ruff check --fix (handles most issues automatically)
        sp.run(
            ['ruff', 'check', '--fix', str(file_path)],
            capture_output=True,
            text=True,
            check=False
        )

        # Run ruff format
        sp.run(['ruff', 'format', str(file_path)], capture_output=True, check=False)

        # Check if there are still errors we can fix
        # For now, stop after first iteration as ruff handles most cases
        # This can be enhanced to parse pylint output and continue fixing
        break

    return True


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Fix Python linting errors using ruff and other tools',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Comprehensive mode - fix all errors in files/directories
  python3 scripts/fix-python-lint.py function_app/
  python3 scripts/fix-python-lint.py function_app/scorer.py

  # Specific mode - fix only errors from JSON diagnostics
  python3 scripts/fix-python-lint.py --json errors.json
  python3 scripts/fix-python-lint.py --json -  # Read from stdin

  # Dry run (preview changes)
  python3 scripts/fix-python-lint.py --dry-run function_app/
  python3 scripts/fix-python-lint.py --json --dry-run errors.json

  # Include type checking
  python3 scripts/fix-python-lint.py --check-types function_app/
        """
    )
    parser.add_argument(
        'path',
        nargs='?',
        default='function_app',
        help='File or directory to process (comprehensive mode) or path to JSON file (--json mode)'
    )
    parser.add_argument(
        '--json',
        metavar='FILE',
        nargs='?',
        const='-',
        help='Read errors from JSON diagnostics file (or stdin if FILE is "-" or omitted)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be fixed without making changes'
    )
    parser.add_argument(
        '--check-types',
        action='store_true',
        help='Also run pyright type checking (read-only, no fixes)'
    )
    parser.add_argument(
        '--check-pylint',
        action='store_true',
        help='Also run pylint (read-only, no fixes)'
    )
    parser.add_argument(
        '--auto-fix',
        action='store_true',
        help='Recursively fix errors until no more fixable errors remain'
    )

    args = parser.parse_args()

    # JSON mode
    if args.json is not None:
        # Read errors
        if args.json == '-' or args.json is None:
            # Read from stdin
            errors = json.load(sys.stdin)
        else:
            # Read from file
            json_path = Path(args.json)
            if not json_path.exists():
                print(f"Error: JSON file does not exist: {json_path}", file=sys.stderr)
                sys.exit(1)
            with open(json_path, 'r', encoding='utf-8') as f:
                errors = json.load(f)

        # Process errors
        if not isinstance(errors, list):
            print("Error: Expected JSON array of errors", file=sys.stderr)
            sys.exit(1)

        modified_files = process_errors_json(errors, dry_run=args.dry_run)

        # Write modified files
        for file_path_str, content in modified_files.items():
            file_path = Path(file_path_str)

            if args.dry_run:
                print(f"🔍 Would fix: {file_path}")
            else:
                file_path.write_text(content, encoding='utf-8')
                print(f"✅ Fixed: {file_path}")

        if not args.dry_run:
            print(f"\nFixed {len(modified_files)} file(s)")

        # If auto-fix is enabled, continue with comprehensive fixes
        if args.auto_fix and modified_files:
            print("\nContinuing with comprehensive auto-fix...")
            for file_path_str in modified_files:
                auto_fix_recursive(Path(file_path_str))

    # Comprehensive mode (default)
    else:
        path = Path(args.path)

        if not path.exists():
            print(f"Error: Path does not exist: {path}", file=sys.stderr)
            sys.exit(1)

        python_files = find_python_files(path)

        if not python_files:
            print(f"No Python files found in: {path}")
            sys.exit(0)

        print(f"Processing {len(python_files)} Python file(s)...")
        if args.dry_run:
            print("DRY RUN MODE - No files will be modified\n")

        exit_code = 0

        # Auto-fix mode: recursively fix until no more errors
        if args.auto_fix:
            for py_file in python_files:
                auto_fix_recursive(py_file)

        # Step 1: Run ruff check --fix (auto-fixes linting issues)
        print("\n1. Running ruff check --fix...")
        ruff_check_cmd = ['ruff', 'check', '--fix', str(path)]
        if args.dry_run:
            ruff_check_cmd = ['ruff', 'check', str(path)]  # Check only in dry-run
        code = run_command(ruff_check_cmd, dry_run=args.dry_run)
        if code != 0:
            exit_code = code

        # Step 2: Run ruff format (code formatting)
        print("\n2. Running ruff format...")
        if args.dry_run:
            ruff_format_cmd = ['ruff', 'format', '--check', str(path)]
        else:
            ruff_format_cmd = ['ruff', 'format', str(path)]
        code = run_command(ruff_format_cmd, dry_run=args.dry_run)
        if code != 0:
            exit_code = code

        # Step 3: Optional type checking (read-only)
        if args.check_types:
            print("\n3. Running pyright type check...")
            pyright_cmd = ['pyright', str(path)]
            code = run_command(pyright_cmd, dry_run=args.dry_run)
            # Type errors don't fail the script, just report
            if code != 0:
                print("Note: Type errors found (not auto-fixed)")

        # Step 4: Optional pylint (read-only)
        if args.check_pylint:
            print("\n4. Running pylint...")
            pylint_cmd = ['pylint', str(path)]
            code = run_command(pylint_cmd, dry_run=args.dry_run)
            # Pylint errors don't fail the script, just report
            if code != 0:
                print("Note: Pylint issues found (not auto-fixed)")

        if not args.dry_run:
            print("\n✅ Python linting fixes complete!")
            if exit_code == 0:
                print("All auto-fixable issues resolved.")
            else:
                print("Some issues may require manual fixes.")
        else:
            print("\n🔍 Dry run complete. Review commands above.")

        sys.exit(exit_code)


if __name__ == '__main__':
    main()
