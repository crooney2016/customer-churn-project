# Code Review Report

**Generated:** 2026-01-16 17:56:00

> This report was generated using automated analysis based on
> `.cursor/rules/prompts/code-review.md` guidelines.

---

## Executive Summary

🔴 **Overall Status: Needs Attention**

- **Linting**: ❌ Issues found
- **Performance Issues**: 0 Critical, 1 Moderate
- **Code Quality Score**: N/A

---

## Linting Results

### Ruff: ❌ Issues Found

Issues found: 0

### Pyright: ❌ Issues Found

Issues found: 0

---

## Performance Anti-Patterns

> Performance issues impact Azure Consumption plan costs.

| File | Line | Issue | Severity | Recommended Fix |
| ------ | ------ | ------- | ---------- | ---------------- |
| `function_app/scorer.py` | 75 | Multiple sequential concat operations | 🟢 Minor | Combine in single concat operation |
| `function_app/.venv/lib/python3.13/site-packages/pip/_vendor/cachecontrol/adapter.py` | 99 | apply() on DataFrame (row-by-row execution) | 🟡 Moderate | Use vectorized NumPy/pandas operations |

---

## Recommendations

1. **Fix linting errors**: Run `make lint-fix` to automatically fix most issues, then review remaining errors manually.

1. **Review 1 moderate performance issue(s)**: These can be addressed to further optimize costs.

---
