#!/usr/bin/env python3
# pylint: disable=too-many-lines,invalid-name,reimported,redefined-outer-name,import-outside-toplevel
"""
Automated markdown linting fixer.

Fixes common markdownlint errors automatically. Can operate in two modes:
1. Comprehensive mode (default): Scans and fixes all common errors in files/directories
2. Specific mode: Fixes only errors specified in JSON diagnostics file

Adding New Rules:
    To add support for a new markdownlint error:
    1. Create comprehensive fixer function: fix_mdXXX_error_name(content: str) -> str
    2. Create specific fixer function: fix_mdXXX_specific(_file_path, line_num, content) -> str
    3. Add to fix_all() pipeline (in correct order - see comments for dependencies)
    4. Add to SPECIFIC_FIX_FUNCTIONS dictionary: 'MDXXX': fix_mdXXX_specific
    5. Update docstring at top of file with new error code
    6. Test with known error cases
    7. Document in .cursor/rules/markdown.md and .cursor/rules/linting.md

Fixes:
- MD001: Heading increment (must increment by exactly 1 level)
- MD009: Trailing spaces
- MD012: Multiple blank lines
- MD024: Duplicate headings
- MD026: Trailing punctuation in headings
- MD029: Ordered list numbering
- MD031: Blank lines around code fences
- MD032: Blank lines around lists
- MD034: Bare URLs
- MD036: Emphasis as heading
- MD038: Spaces inside code spans (removes spaces from backticks)
- MD040: Fenced code language
- MD047: Trailing newline
- MD056: Table column count (fixes mismatched table columns)
- MD060: Table spacing

Usage:
    # Comprehensive mode (default) - fix all errors in files/directories
    python scripts/fix-markdown-lint.py [file_or_directory]
    python scripts/fix-markdown-lint.py docs/
    python scripts/fix-markdown-lint.py .cursor/rules/
    python scripts/fix-markdown-lint.py file.md

    # Specific mode - fix only errors from JSON diagnostics
    python scripts/fix-markdown-lint.py --json errors.json
    python scripts/fix-markdown-lint.py --json -  # Read from stdin

    # Dry run (preview changes)
    python scripts/fix-markdown-lint.py --dry-run docs/
    python scripts/fix-markdown-lint.py --json --dry-run errors.json
"""

import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple


def fix_md032_blanks_around_lists(content: str) -> str:
    """Fix MD032: Add blank lines before and after lists."""
    lines = content.split('\n')
    result = []
    i = 0

    while i < len(lines):
        line = lines[i]

        # Check if this is a list item (starts with -, *, +, or number)
        is_list_item = bool(re.match(r'^(\s*)([-*+]|\d+\.)\s+', line))
        is_checkbox = bool(re.match(r'^\s*-?\s*\[', line))  # Checkbox lists

        if is_list_item or is_checkbox:
            # Add blank line before if previous line is not blank and not a list
            prev_is_list = bool(re.match(r'^(\s*)([-*+]|\d+\.)\s+', result[-1]))
            prev_is_checkbox = bool(re.match(r'^\s*-?\s*\[', result[-1]))
            if result and result[-1].strip() and not prev_is_list and not prev_is_checkbox:
                result.append('')

            result.append(line)
            i += 1

            # Add blank line after if next line is not blank and not a list
            if i < len(lines):
                next_line = lines[i]
                is_next_list = bool(re.match(r'^(\s*)([-*+]|\d+\.)\s+', next_line))
                is_next_checkbox = bool(re.match(r'^\s*-?\s*\[', next_line))
                is_next_list = is_next_list or is_next_checkbox
                is_next_blank = not next_line.strip()
                is_next_code_fence = next_line.strip().startswith('```')

                if not is_next_blank and not is_next_list and not is_next_code_fence:
                    # Check if we're at end of list
                    if i < len(lines) and not re.match(r'^(\s*)([-*+]|\d+\.)\s+', next_line):
                        result.append('')
        else:
            result.append(line)
            i += 1

    return '\n'.join(result)


def fix_md031_blanks_around_fences(content: str) -> str:
    """Fix MD031: Add blank lines before and after code fences."""
    lines = content.split('\n')
    result = []
    i = 0

    while i < len(lines):
        line = lines[i]

        # Check if this is a code fence
        if line.strip().startswith('```'):
            # Add blank line before if previous line is not blank
            if result and result[-1].strip():
                result.append('')

            result.append(line)
            i += 1

            # Read until closing fence
            while i < len(lines) and not lines[i].strip().startswith('```'):
                result.append(lines[i])
                i += 1

            # Add closing fence
            if i < len(lines):
                result.append(lines[i])
                i += 1

            # Add blank line after if next line is not blank
            if i < len(lines) and lines[i].strip():
                result.append('')
        else:
            result.append(line)
            i += 1

    return '\n'.join(result)


def fix_md029_ordered_list_prefix(content: str) -> str:
    """Fix MD029: Ensure ordered lists use consistent numbering (1/1/1 style)."""
    lines = content.split('\n')
    result = []
    i = 0

    while i < len(lines):
        line = lines[i]

        # Check if this is an ordered list item
        match = re.match(r'^(\s*)(\d+)\.\s+(.*)$', line)
        if match:
            indent = match.group(1)
            # rest = match.group(3)  # Not currently used, kept for potential future use

            # Find all consecutive list items at same indent level
            list_items = []
            j = i

            while j < len(lines):
                item_match = re.match(r'^(\s*)(\d+)\.\s+(.*)$', lines[j])
                if item_match and item_match.group(1) == indent:
                    list_items.append((j, int(item_match.group(2)), item_match.group(3)))
                    j += 1
                else:
                    break

            # Check if we need to fix numbering
            # If first item is not 1, or items are not sequential starting from where they should
            if list_items and list_items[0][1] != 1:
                # Fix: start from 1
                for _, _, content in list_items:
                    result.append(f"{indent}1. {content}")

                i = j
            else:
                # Keep as is if numbering is correct
                for _, _, content in list_items:
                    result.append(f"{indent}1. {content}")
                i = j
        else:
            result.append(line)
            i += 1

    return '\n'.join(result)


def fix_md047_trailing_newline(content: str) -> str:
    """Fix MD047: Ensure file ends with exactly one newline."""
    # Remove trailing newlines
    content = content.rstrip('\n')
    # Add exactly one newline
    return content + '\n'


def fix_md060_table_spacing(content: str) -> str:
    """Fix MD060: Ensure proper spacing in tables (space after |)."""
    lines = content.split('\n')
    result = []

    for line in lines:
        # Check if this is a table row
        # Skip if it's a code block or if pipes are inside code spans (backticks)
        if '|' in line and not line.strip().startswith('```'):
            # Check if pipes are inside code spans (backticks) - if so, skip this line
            # Simple heuristic: if line has backticks and pipes, likely code span, skip
            if '`' in line:
                # More careful check: look for patterns like `|something|` which are code spans
                # Check if there are backticks with pipes inside them
                code_span_pattern = r'`[^`]*\|[^`]*`'
                if re.search(code_span_pattern, line):
                    # Has pipes inside code spans, skip this line
                    result.append(line)
                    continue

            # Split by | and add proper spacing
            parts = line.split('|')
            fixed_parts = []

            for i, part in enumerate(parts):
                if i == 0 or i == len(parts) - 1:
                    # First and last parts (outside table) keep as is
                    fixed_parts.append(part)
                else:
                    # Inner parts need space after |
                    fixed_parts.append(' ' + part.strip() + ' ')

            result.append('|'.join(fixed_parts))
        else:
            result.append(line)

    return '\n'.join(result)


def fix_md034_bare_urls(content: str) -> str:
    """Fix MD034: Convert bare URLs to proper markdown links."""
    # Pattern for URLs (http/https)
    url_pattern = r'(?<!\]\()(https?://[^\s<>"{}|\\^`\[\]]+)'

    def replace_url(match):
        url = match.group(1)
        # Don't replace if already in a link
        if f'[{url}]' in content or f'({url})' in content:
            return url
        return f'[{url}]({url})'

    return re.sub(url_pattern, replace_url, content)


def fix_md040_fenced_code_language(content: str) -> str:
    """Fix MD040: Add language identifier to fenced code blocks (default: text)."""
    lines = content.split('\n')
    result = []
    i = 0

    while i < len(lines):
        line = lines[i]

        # Check if this is an opening code fence without language
        if line.strip().startswith('```'):
            fence = line.strip()
            # Check if it's just ``` without language
            if fence == '```' or fence == '``` ':
                # Default to 'text' if no language specified
                result.append('```text')
            else:
                result.append(line)
            i += 1

            # Read until closing fence
            while i < len(lines) and not lines[i].strip().startswith('```'):
                result.append(lines[i])
                i += 1

            # Add closing fence
            if i < len(lines):
                result.append(lines[i])
                i += 1
        else:
            result.append(line)
            i += 1

    return '\n'.join(result)


def fix_md036_emphasis_as_heading(content: str) -> str:
    """Fix MD036: Convert bold/italic emphasis used as headings to proper headings."""
    lines = content.split('\n')
    result = []

    for line in lines:
        # Check if line starts with ** and ends with ** (likely a heading)
        stripped = line.strip()
        if stripped.startswith('**') and stripped.endswith('**') and not stripped.startswith('***'):
            # Convert to heading (assume h4 for bold standalone lines)
            text = stripped[2:-2].strip()
            result.append(f"#### {text}")
        elif stripped.startswith('*') and stripped.endswith('*') and not stripped.startswith('**'):
            # Italic emphasis as heading
            text = stripped[1:-1].strip()
            result.append(f"#### {text}")
        else:
            result.append(line)

    return '\n'.join(result)


def fix_md009_trailing_spaces(content: str) -> str:
    """Fix MD009: Remove trailing spaces (except in code blocks where 2 spaces are needed)."""
    lines = content.split('\n')
    result = []
    in_code_block = False

    for line in lines:
        # Track code blocks
        if line.strip().startswith('```'):
            in_code_block = not in_code_block
            result.append(line)
        elif in_code_block:
            # Preserve code block content as-is
            result.append(line)
        else:
            # Remove trailing spaces from regular lines
            # MD009 allows 2 trailing spaces for line breaks, but we'll remove all for simplicity
            result.append(line.rstrip(' '))

    return '\n'.join(result)


def fix_md012_multiple_blanks(content: str) -> str:
    """Fix MD012: Replace multiple consecutive blank lines with single blank line."""
    # Replace 2+ newlines with exactly 2 newlines (one blank line)
    return re.sub(r'\n{3,}', '\n\n', content)


def fix_md001_heading_increment(content: str) -> str:
    """Fix MD001: Ensure headings increment by exactly one level."""
    lines = content.split('\n')
    result = []
    previous_heading_level = 0  # Track the last heading level seen

    for line in lines:
        # Check if this is a heading (starts with #)
        match = re.match(r'^(#{1,6})\s+(.+)$', line)
        if match:
            current_level = len(match.group(1))
            text = match.group(2)

            # If current level jumps by more than 1, adjust to previous + 1
            if current_level > previous_heading_level + 1:
                # Fix: set to previous level + 1
                new_level = previous_heading_level + 1
                # Ensure we don't go beyond h6
                new_level = min(new_level, 6)
                result.append('#' * new_level + ' ' + text)
                previous_heading_level = new_level
            else:
                # Valid increment, keep as is
                result.append(line)
                previous_heading_level = current_level
        else:
            result.append(line)

    return '\n'.join(result)


def fix_md024_duplicate_headings(content: str) -> str:
    """Fix MD024: Make duplicate headings unique by adding context."""
    lines = content.split('\n')
    heading_history = {}  # Track headings seen: {text_lower: [line_indices]}

    # First pass: collect all headings and identify duplicates
    # Extract base text (without existing context in parentheses)
    for i, line in enumerate(lines):
        match = re.match(r'^(#{1,6})\s+(.+)$', line)
        if match:
            text = match.group(2).rstrip()
            # Remove trailing punctuation
            text_clean = re.sub(r'[:.,;!?]+$', '', text).strip()
            # Remove ALL existing context in parentheses (handle nested parentheses)
            base_text = text_clean
            # Remove all parenthetical context: match (text) at end, including nested
            while re.search(r'\([^()]+\)\s*$', base_text):
                base_text = re.sub(r'\s*\([^()]+\)\s*$', '', base_text).strip()
            base_text_lower = base_text.lower()

            if base_text_lower not in heading_history:
                heading_history[base_text_lower] = []
            heading_history[base_text_lower].append(i)

    # Second pass: fix duplicates by adding context to all occurrences
    result = []
    for i, line in enumerate(lines):
        match = re.match(r'^(#{1,6})\s+(.+)$', line)
        if match:
            level = match.group(1)
            text = match.group(2).rstrip()
            # Remove trailing punctuation
            text_clean = re.sub(r'[:.,;!?]+$', '', text).strip()
            # Remove ALL existing context in parentheses to get base text
            base_text = text_clean
            while re.search(r'\([^()]+\)\s*$', base_text):
                base_text = re.sub(r'\s*\([^()]+\)\s*$', '', base_text).strip()
            base_text_lower = base_text.lower()

            # Check if this base heading text appears multiple times
            occurrences = heading_history.get(base_text_lower, [])
            if len(occurrences) > 1:
                # This is a duplicate - add context to make it unique
                # Check if it already has context (any parentheses at end)
                has_context = bool(re.search(r'\([^)]+\)\s*$', text_clean))

                if not has_context:
                    # Find parent heading for context
                    parent_context = None
                    for j in range(i - 1, -1, -1):
                        parent_match = re.match(r'^(#{1,6})\s+(.+)$', lines[j])
                        if parent_match and len(parent_match.group(1)) < len(level):
                            parent_text = parent_match.group(2).rstrip()
                            parent_text_clean = re.sub(r'[:.,;!?]+$', '', parent_text).strip()
                            # Remove existing context from parent too
                            parent_base = re.sub(r'\s*\([^)]+\)\s*$', '', parent_text_clean).strip()
                            parent_context = parent_base
                            break

                    # Make unique with context or counter
                    # Only add context if heading doesn't already have it
                    if parent_context:
                        # Make sure we don't duplicate the parent context
                        if f"({parent_context})" not in text_clean:
                            result.append(f"{level} {text_clean} ({parent_context})")
                        else:
                            # Already has this context, keep as is
                            result.append(line)
                    else:
                        # Fallback: use occurrence number if no parent context found
                        occurrence_num = occurrences.index(i) + 1
                        result.append(f"{level} {text_clean} {occurrence_num}")
            else:
                # Not a duplicate, keep as is
                result.append(line)
        else:
            result.append(line)

    return '\n'.join(result)


def fix_md026_trailing_punctuation(content: str) -> str:
    """Fix MD026: Remove trailing punctuation from headings."""
    lines = content.split('\n')
    result = []

    for line in lines:
        # Check if this is a heading (starts with #)
        match = re.match(r'^(#{1,6})\s+(.+)$', line)
        if match:
            level = match.group(1)
            text = match.group(2).rstrip()

            # Remove trailing punctuation: : . , ; ! ?
            text = re.sub(r'[:.,;!?]+$', '', text)

            result.append(f"{level} {text}")
        else:
            result.append(line)

    return '\n'.join(result)


def fix_md038_spaces_in_code(content: str) -> str:
    """Fix MD038: Remove spaces from inside code span elements (backticks)."""
    # Pattern to match code spans with spaces: ` text ` or ` text` or `text `
    # We want to preserve the backticks but remove leading/trailing spaces inside them
    def remove_spaces_in_code_span(match):
        code_content = match.group(1)
        # Remove leading and trailing spaces
        cleaned = code_content.strip()
        return f'`{cleaned}`'

    # Match code spans: `...` but not code blocks ```
    # Use negative lookahead to avoid matching code block fences
    pattern = r'`([^`\n]+)`'
    return re.sub(pattern, remove_spaces_in_code_span, content)


def fix_md056_table_column_count(content: str) -> str:
    """Fix MD056: Fix table column count mismatches."""
    lines = content.split('\n')
    result = []
    i = 0

    while i < len(lines):
        line = lines[i]

        # Check if this is a table row (has | and not a code block)
        if '|' in line and not line.strip().startswith('```'):
            # Skip if pipes are in code spans
            if '`' in line:
                code_span_pattern = r'`[^`]*\|[^`]*`'
                if re.search(code_span_pattern, line):
                    result.append(line)
                    i += 1
                    continue

            # Check if this looks like a table header (next line is separator)
            if i + 1 < len(lines) and re.match(r'^\s*\|[\s\-:]+\|', lines[i + 1]):
                # This is a table header, find the separator to get column count
                header = line
                separator = lines[i + 1]  # Separator line
                header_cols = len([p for p in header.split('|') if p.strip()])

                # Find all rows in this table
                table_rows = [header, separator]
                j = i + 2
                while j < len(lines) and '|' in lines[j] and not lines[j].strip().startswith('```'):
                    # Skip if code spans
                    if '`' in lines[j]:
                        code_span_pattern = r'`[^`]*\|[^`]*`'
                        if re.search(code_span_pattern, lines[j]):
                            break
                    table_rows.append(lines[j])
                    j += 1

                # Fix rows to match header column count
                fixed_rows = []
                for row in table_rows:
                    parts = row.split('|')
                    # Remove empty first/last if they're just whitespace
                    if len(parts) > 0 and not parts[0].strip():
                        parts = parts[1:]
                    if len(parts) > 0 and not parts[-1].strip():
                        parts = parts[:-1]

                    # Adjust to match header
                    if len(parts) > header_cols:
                        # Too many columns, truncate
                        parts = parts[:header_cols]
                    elif len(parts) < header_cols:
                        # Too few columns, pad with empty cells
                        parts.extend([''] * (header_cols - len(parts)))

                    # Reconstruct row
                    fixed_row = '| ' + ' | '.join(p.strip() for p in parts) + ' |'
                    fixed_rows.append(fixed_row)

                result.extend(fixed_rows)
                i = j
                continue

        result.append(line)
        i += 1

    return '\n'.join(result)


def fix_all(content: str) -> str:
    """Apply all markdown fixes in correct order."""
    content = fix_md009_trailing_spaces(content)
    content = fix_md012_multiple_blanks(content)
    content = fix_md001_heading_increment(content)  # Fix heading increments before duplicates
    content = fix_md024_duplicate_headings(content)  # Fix duplicate headings after increments
    content = fix_md032_blanks_around_lists(content)
    content = fix_md031_blanks_around_fences(content)
    content = fix_md036_emphasis_as_heading(content)
    content = fix_md038_spaces_in_code(content)  # Fix code spans before table fixes
    content = fix_md040_fenced_code_language(content)
    content = fix_md034_bare_urls(content)
    content = fix_md056_table_column_count(content)  # Fix table structure before spacing
    content = fix_md060_table_spacing(content)
    content = fix_md029_ordered_list_prefix(content)
    content = fix_md026_trailing_punctuation(content)
    content = fix_md047_trailing_newline(content)
    return content


# Specific error fixers for JSON diagnostics mode
def fix_md032_specific(_file_path: Path, line_num: int, content: str) -> str:
    """Fix MD032: Add blank line before/after list."""
    lines = content.split('\n')
    # Convert to 0-based index
    idx = line_num - 1

    if idx < 0 or idx >= len(lines):
        return content

    # Add blank line before if needed
    if idx > 0 and lines[idx - 1].strip():
        lines.insert(idx, '')
        idx += 1  # Adjust for inserted line

    # Add blank line after if needed
    if idx + 1 < len(lines) and lines[idx + 1].strip():
        # Check if next line is not a list item
        next_line = lines[idx + 1]
        is_list = bool(re.match(r'^(\s*)([-*+]|\d+\.)\s+', next_line))
        is_code_fence = next_line.strip().startswith('```')

        if not is_list and not is_code_fence:
            lines.insert(idx + 1, '')

    return '\n'.join(lines)


def fix_md031_specific(_file_path: Path, line_num: int, content: str) -> str:
    """Fix MD031: Add blank line before/after code fence."""
    lines = content.split('\n')
    idx = line_num - 1

    if idx < 0 or idx >= len(lines):
        return content

    # Add blank line before if needed
    if idx > 0 and lines[idx - 1].strip():
        lines.insert(idx, '')

    return '\n'.join(lines)


def fix_md029_specific(_file_path: Path, line_num: int, content: str) -> str:
    """Fix MD029: Fix ordered list numbering."""
    lines = content.split('\n')
    idx = line_num - 1

    if idx < 0 or idx >= len(lines):
        return content

    line = lines[idx]
    match = re.match(r'^(\s*)(\d+)\.\s+(.*)$', line)
    if match:
        indent = match.group(1)
        _rest = match.group(3)  # Content after number, not currently used

        # Find all list items at same indent level
        list_start = idx
        while list_start > 0:
            prev_match = re.match(r'^(\s*)(\d+)\.\s+', lines[list_start - 1])
            if prev_match and prev_match.group(1) == indent:
                list_start -= 1
            else:
                break

        # Count how many list items before current one
        item_number = 1
        for i in range(list_start, idx):
            if re.match(r'^' + re.escape(indent) + r'\d+\.\s+', lines[i]):
                item_number += 1

        # Replace with correct number
        lines[idx] = f"{indent}1. {rest}"

    return '\n'.join(lines)


def fix_md047_specific(_file_path: Path, content: str) -> str:
    """Fix MD047: Ensure file ends with exactly one newline."""
    content = content.rstrip('\n')
    return content + '\n'


def fix_md060_specific(_file_path: Path, line_num: int, _column: int, content: str) -> str:
    """Fix MD060: Fix table spacing."""
    lines = content.split('\n')
    idx = line_num - 1

    if idx < 0 or idx >= len(lines):
        return content

    line = lines[idx]

    # Fix table spacing: ensure space after |
    if '|' in line:
        parts = line.split('|')
        fixed_parts = []

        for i, part in enumerate(parts):
            if i == 0 or i == len(parts) - 1:
                fixed_parts.append(part)
            else:
                # Ensure space padding
                fixed_parts.append(' ' + part.strip() + ' ')

        lines[idx] = '|'.join(fixed_parts)

    return '\n'.join(lines)


def fix_md034_specific(_file_path: Path, line_num: int, content: str) -> str:
    """Fix MD034: Convert bare URL to link."""
    lines = content.split('\n')
    idx = line_num - 1

    if idx < 0 or idx >= len(lines):
        return content

    line = lines[idx]
    # Pattern for URLs
    url_pattern = r'(?<!\]\()(https?://[^\s<>"{}|\\^`\[\]]+)(?![\)])'

    def replace_url(match):
        url = match.group(1)
        return f'[{url}]({url})'

    lines[idx] = re.sub(url_pattern, replace_url, line)

    return '\n'.join(lines)


def fix_md040_specific(_file_path: Path, line_num: int, content: str) -> str:
    """Fix MD040: Add language to code fence."""
    lines = content.split('\n')
    idx = line_num - 1

    if idx < 0 or idx >= len(lines):
        return content

    line = lines[idx]
    if line.strip() == '```':
        lines[idx] = '```text'
    elif line.strip().startswith('```') and len(line.strip()) == 3:
        lines[idx] = '```text'

    return '\n'.join(lines)


def fix_md036_specific(_file_path: Path, line_num: int, content: str) -> str:
    """Fix MD036: Convert emphasis to heading."""
    lines = content.split('\n')
    idx = line_num - 1

    if idx < 0 or idx >= len(lines):
        return content

    line = lines[idx]
    stripped = line.strip()

    # Check if bold emphasis used as heading
    if stripped.startswith('**') and stripped.endswith('**') and not stripped.startswith('***'):
        text = stripped[2:-2].strip()
        # Determine heading level based on context (default to h4)
        lines[idx] = line.replace(stripped, f"#### {text}")

    return '\n'.join(lines)


def fix_md001_specific(_file_path: Path, line_num: int, content: str) -> str:
    """Fix MD001: Fix heading increment at specific line."""
    lines = content.split('\n')
    idx = line_num - 1

    if idx < 0 or idx >= len(lines):
        return content

    # Find previous heading level
    previous_level = 0
    for i in range(idx - 1, -1, -1):
        prev_match = re.match(r'^(#{1,6})\s+', lines[i])
        if prev_match:
            previous_level = len(prev_match.group(1))
            break

    # Fix current heading
    line = lines[idx]
    match = re.match(r'^(#{1,6})\s+(.+)$', line)
    if match:
        current_level = len(match.group(1))
        text = match.group(2)

        # If current level jumps by more than 1, adjust to previous + 1
        if current_level > previous_level + 1:
            new_level = previous_level + 1
            new_level = min(new_level, 6)  # Max h6
            lines[idx] = '#' * new_level + ' ' + text

    return '\n'.join(lines)


def fix_md024_specific(_file_path: Path, line_num: int, content: str) -> str:
    """Fix MD024: Make duplicate headings unique."""
    lines = content.split('\n')
    idx = line_num - 1

    if idx < 0 or idx >= len(lines):
        return content

    line = lines[idx]
    # Find heading level and text (strip trailing punctuation for comparison)
    match = re.match(r'^(#{1,6})\s+(.+)$', line)
    if match:
        level = match.group(1)
        text = match.group(2).rstrip()
        # Remove trailing punctuation for comparison
        text_clean = re.sub(r'[:.,;!?]+$', '', text).strip()

        # Count how many times this heading appears before current line
        heading_text_clean = text_clean.lower()
        occurrences = []
        for i in range(idx):
            prev_match = re.match(r'^(#{1,6})\s+(.+)$', lines[i])
            if prev_match:
                prev_text = prev_match.group(2).rstrip()
                prev_text_clean = re.sub(r'[:.,;!?]+$', '', prev_text).strip().lower()
                if prev_text_clean == heading_text_clean:
                    occurrences.append(i)

        # If this is a duplicate, make it unique
        if occurrences:
            # Find parent heading for context
            parent_context = None
            for i in range(idx - 1, -1, -1):
                parent_match = re.match(r'^(#{1,6})\s+(.+)$', lines[i])
                if parent_match and len(parent_match.group(1)) < len(level):
                    parent_context = re.sub(r'[:.,;!?]+$', '', parent_match.group(2).rstrip()).strip()
                    break

            # Make unique with counter or context
            if parent_context:
                lines[idx] = f"{level} {text_clean} ({parent_context})"
            else:
                # Use counter: "Configuration 2", "Expected Behavior 2", etc.
                counter = len(occurrences) + 1
                lines[idx] = f"{level} {text_clean} {counter}"

    return '\n'.join(lines)


def fix_md026_specific(_file_path: Path, line_num: int, content: str) -> str:
    """Fix MD026: Remove trailing punctuation from heading."""
    lines = content.split('\n')
    idx = line_num - 1

    if idx < 0 or idx >= len(lines):
        return content

    line = lines[idx]
    # Check if this is a heading
    match = re.match(r'^(#{1,6})\s+(.+)$', line)
    if match:
        level = match.group(1)
        text = match.group(2).rstrip()

        # Remove trailing punctuation: : . , ; ! ?
        text = re.sub(r'[:.,;!?]+$', '', text)

        lines[idx] = f"{level} {text}"

    return '\n'.join(lines)


def fix_md009_specific(_file_path: Path, line_num: int, content: str) -> str:
    """Fix MD009: Remove trailing spaces."""
    lines = content.split('\n')
    idx = line_num - 1

    if idx < 0 or idx >= len(lines):
        return content

    lines[idx] = lines[idx].rstrip(' ')
    return '\n'.join(lines)


def fix_md012_specific(_file_path: Path, _line_num: int, content: str) -> str:
    """Fix MD012: Remove multiple blank lines."""
    # Replace multiple consecutive newlines
    return re.sub(r'\n{3,}', '\n\n', content)


def fix_md038_specific(_file_path: Path, line_num: int, content: str) -> str:
    """Fix MD038: Remove spaces from inside code span elements."""
    lines = content.split('\n')
    idx = line_num - 1

    if idx < 0 or idx >= len(lines):
        return content

    line = lines[idx]

    def remove_spaces_in_code_span(match):
        code_content = match.group(1)
        cleaned = code_content.strip()
        return f'`{cleaned}`'

    # Fix code spans on this line
    pattern = r'`([^`\n]+)`'
    lines[idx] = re.sub(pattern, remove_spaces_in_code_span, line)

    return '\n'.join(lines)


def fix_md056_specific(_file_path: Path, _line_num: int, content: str) -> str:
    """Fix MD056: Fix table column count mismatch."""
    # For specific mode, we'll use the comprehensive fixer on the whole content
    # since table structure needs to be analyzed as a whole
    return fix_md056_table_column_count(content)


# Mapping of error codes to specific fix functions
SPECIFIC_FIX_FUNCTIONS = {
    'MD001': fix_md001_specific,
    'MD009': fix_md009_specific,
    'MD012': fix_md012_specific,
    'MD024': fix_md024_specific,
    'MD026': fix_md026_specific,
    'MD029': fix_md029_specific,
    'MD031': fix_md031_specific,
    'MD032': fix_md032_specific,
    'MD034': fix_md034_specific,
    'MD036': fix_md036_specific,
    'MD038': fix_md038_specific,
    'MD040': fix_md040_specific,
    'MD047': fix_md047_specific,
    'MD056': fix_md056_specific,
    'MD060': fix_md060_specific,
}


def process_file_comprehensive(file_path: Path, dry_run: bool = False) -> Tuple[int, int]:
    """
    Process a single markdown file in comprehensive mode.

    Returns:
        Tuple of (errors_fixed, files_modified)
    """
    try:
        original_content = file_path.read_text(encoding='utf-8')
        fixed_content = fix_all(original_content)

        if original_content != fixed_content:
            if not dry_run:
                file_path.write_text(fixed_content, encoding='utf-8')
                print(f"✅ Fixed: {file_path}")
            else:
                print(f"🔍 Would fix: {file_path}")
            return (1, 1)
        else:
            if not dry_run:
                print(f"✓ OK: {file_path}")
            return (0, 0)
    except Exception as e:  # pylint: disable=broad-exception-caught
        print(f"❌ Error processing {file_path}: {e}", file=sys.stderr)
        return (0, 0)


def process_errors_json(errors: List[Dict], dry_run: bool = False) -> Dict[str, str]:
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

            # Sort errors by line number (descending) to avoid index shifting issues
            sorted_errors = sorted(file_errors, key=lambda e: e.get('startLineNumber', 0), reverse=True)

            # Apply fixes (reverse order to avoid line number shifts)
            for error in sorted_errors:
                code = error.get('code', {}).get('value', '')
                line_num = error.get('startLineNumber', 0)
                column = error.get('startColumn', 0)

                if code in SPECIFIC_FIX_FUNCTIONS:
                    fix_func = SPECIFIC_FIX_FUNCTIONS[code]

                    # MD047 doesn't need line number
                    if code == 'MD047':
                        content = fix_func(file_path, content)
                    # MD060 needs column
                    elif code == 'MD060':
                        content = fix_func(file_path, line_num, column, content)
                    # Most fixes need line number
                    else:
                        content = fix_func(file_path, line_num, content)

            if content != original_content:
                modified_files[str(file_path)] = content

        except Exception as e:  # pylint: disable=broad-exception-caught
            print(f"Error processing {file_path}: {e}", file=sys.stderr)

    return modified_files


def main():
    """Main entry point."""
    import argparse  # pylint: disable=import-outside-toplevel

    parser = argparse.ArgumentParser(
        description='Automatically fix common markdown linting errors',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Comprehensive mode - fix all errors in files/directories
  python3 scripts/fix-markdown-lint.py docs/
  python3 scripts/fix-markdown-lint.py file.md

  # Specific mode - fix only errors from JSON diagnostics
  python3 scripts/fix-markdown-lint.py --json errors.json
  python3 scripts/fix-markdown-lint.py --json -  # Read from stdin

  # Dry run (preview changes)
  python3 scripts/fix-markdown-lint.py --dry-run docs/
  python3 scripts/fix-markdown-lint.py --json --dry-run errors.json
        """
    )
    parser.add_argument(
        'path',
        nargs='?',
        default='.',
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

    # Comprehensive mode (default)
    else:
        path = Path(args.path)

        if not path.exists():
            print(f"Error: Path does not exist: {path}", file=sys.stderr)
            sys.exit(1)

        markdown_files = []

        if path.is_file():
            if path.suffix != '.md':
                print(f"Warning: Not a markdown file: {path}", file=sys.stderr)
                sys.exit(1)
            markdown_files = [path]
        else:
            # Find all markdown files recursively
            markdown_files = list(path.rglob('*.md'))

        if not markdown_files:
            print(f"No markdown files found in: {path}")
            sys.exit(0)

        print(f"Processing {len(markdown_files)} markdown file(s)...")
        if args.dry_run:
            print("DRY RUN MODE - No files will be modified\n")

        total_fixed = 0
        total_modified = 0

        for md_file in markdown_files:
            fixed, modified = process_file_comprehensive(md_file, dry_run=args.dry_run)
            total_fixed += fixed
            total_modified += modified

        action = 'Would fix' if args.dry_run else 'Fixed'
        print(f"\n{action} {total_fixed} issue(s) in {total_modified} file(s)")


if __name__ == '__main__':
    main()
