#!/usr/bin/env python3
"""
Python linting convenience script.

Wraps existing Python linting tools (ruff, pylint, pyright) for convenience.
Unlike the markdown script, this is a wrapper around tools that already have
excellent auto-fix capabilities, not a custom auto-fixer.

Usage:
    # Fix all Python files
    python3 scripts/fix-python-lint.py function_app/

    # Fix specific file
    python3 scripts/fix-python-lint.py function_app/scorer.py

    # Dry run (check only, no fixes)
    python3 scripts/fix-python-lint.py --dry-run function_app/

    # Include type checking (read-only)
    python3 scripts/fix-python-lint.py --check-types function_app/

    # Include pylint (read-only)
    python3 scripts/fix-python-lint.py --check-pylint function_app/
"""

import subprocess
import sys
from pathlib import Path
from typing import List


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


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Fix Python linting errors using ruff and other tools',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Fix all Python files
  python3 scripts/fix-python-lint.py function_app/

  # Fix specific file
  python3 scripts/fix-python-lint.py function_app/scorer.py

  # Dry run (check only)
  python3 scripts/fix-python-lint.py --dry-run function_app/

  # Include type checking
  python3 scripts/fix-python-lint.py --check-types function_app/

Note: This script wraps existing tools (ruff, pylint, pyright).
      It does not create custom auto-fix logic like the markdown script.
        """
    )
    parser.add_argument(
        'path',
        nargs='?',
        default='function_app',
        help='File or directory to process (default: function_app/)'
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

    args = parser.parse_args()
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
