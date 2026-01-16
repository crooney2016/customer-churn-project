#!/usr/bin/env python3
"""
Generate static HTML email previews for review.

This script renders all email templates with sample data and saves them
to HTML files in the outputs/email_previews/ directory.
"""

import sys
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

# Get project root and template directory
project_root = Path(__file__).parent.parent
template_dir = project_root / "function_app" / "templates" / "emails"

# Initialize Jinja2 environment
env = Environment(
    loader=FileSystemLoader(str(template_dir)),
    autoescape=True,
    trim_blocks=True,
    lstrip_blocks=True
)


def render_template(template_name: str, context: dict) -> str:
    """Render an HTML email template with the provided context."""
    template = env.get_template(template_name)
    return template.render(**context)


def generate_previews():
    """Generate all email preview variations."""
    output_dir = project_root / "outputs" / "email_previews"
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Generating email previews in: {output_dir}\n")

    # Success email variations
    success_variations = [
        {
            "name": "success_standard",
            "context": {
                "row_count": 1523,
                "snapshot_date": "2025-01-31",
                "duration_seconds": 45.67,
                "risk_distribution": {
                    "A - High Risk": 250,
                    "B - Medium Risk": 750,
                    "C - Low Risk": 523
                },
                "avg_risk": 0.42,
                "median_risk": 0.38,
                "top_reasons": {
                    "Low order count (current year)": 450,
                    "High days since last order": 380,
                    "Low spend (current year)": 320,
                    "Low uniforms units (current year)": 280,
                    "High days since last uniforms order": 250
                },
                "model_auc": 0.8523,
                "model_version": "XGBoost v1.0",
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
            }
        },
        {
            "name": "success_single_risk",
            "context": {
                "row_count": 100,
                "snapshot_date": "2025-01-31",
                "duration_seconds": 5.0,
                "risk_distribution": {"A - High Risk": 100},
                "avg_risk": 0.75,
                "median_risk": 0.72,
                "top_reasons": {
                    "High days since last order": 85,
                    "Low order count (current year)": 70
                },
                "model_auc": 0.8523,
                "model_version": "XGBoost v1.0",
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
            }
        },
        {
            "name": "success_no_risk",
            "context": {
                "row_count": 0,
                "snapshot_date": "2025-01-31",
                "duration_seconds": 0.0,
                "risk_distribution": {},
                "avg_risk": None,
                "median_risk": None,
                "top_reasons": {},
                "model_auc": None,
                "model_version": "XGBoost v1.0",
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
            }
        },
        {
            "name": "success_large_numbers",
            "context": {
                "row_count": 1234567,
                "snapshot_date": "2025-01-31",
                "duration_seconds": 1234.56,
                "risk_distribution": {
                    "A - High Risk": 123456,
                    "B - Medium Risk": 987654,
                    "C - Low Risk": 123457
                },
                "avg_risk": 0.45,
                "median_risk": 0.40,
                "top_reasons": {
                    "Low order count (current year)": 450000,
                    "High days since last order": 380000,
                    "Low spend (current year)": 320000
                },
                "model_auc": 0.8523,
                "model_version": "XGBoost v1.0",
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
            }
        },
        {
            "name": "success_sorted_risk",
            "context": {
                "row_count": 100,
                "snapshot_date": "2025-01-31",
                "duration_seconds": 10.0,
                "risk_distribution": {
                    "A - High Risk": 10,
                    "B - Medium Risk": 20,
                    "C - Low Risk": 30
                },
                "avg_risk": 0.35,
                "median_risk": 0.32,
                "top_reasons": {
                    "Low order count (current year)": 45,
                    "High days since last order": 38
                },
                "model_auc": 0.8523,
                "model_version": "XGBoost v1.0",
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
            }
        }
    ]

    # Failure email variations
    failure_variations = [
        {
            "name": "failure_standard",
            "context": {
                "error_type": "ValueError",
                "error_message": "CSV file contains no data rows",
                "step": "parse_csv",
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
            }
        },
        {
            "name": "failure_connection_error",
            "context": {
                "error_type": "ConnectionError",
                "error_message": "Failed to connect to SQL Server: timeout after 30 seconds",
                "step": "sql_write",
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
            }
        },
        {
            "name": "failure_long_traceback",
            "context": {
                "error_type": "RuntimeError",
                "error_message": (
                    "Traceback (most recent call last):\n"
                    "  File 'function_app.py', line 123, in _run_pipeline\n"
                    "    df = parse_csv_from_bytes(blob_data)\n"
                    "  File 'csv_validator.py', line 45, in parse_csv_from_bytes\n"
                    "    raise ValueError('Invalid CSV format')\n"
                    "ValueError: Invalid CSV format\n"
                    "\n"
                    "Additional context: The file appears to be corrupted."
                ),
                "step": "parse_csv",
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
            }
        },
        {
            "name": "failure_special_chars",
            "context": {
                "error_type": "ValueError",
                "error_message": "Error with special chars: <>&\"'",
                "step": "parse_csv",
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
            }
        }
    ]

    # Generate success emails
    print("Generating success emails...")
    for variation in success_variations:
        try:
            html = render_template("success.html", variation["context"])
            output_file = output_dir / f"{variation['name']}.html"
            output_file.write_text(html, encoding="utf-8")
            print(f"  ✓ {variation['name']}.html")
        except (RuntimeError, OSError, IOError) as render_err:
            print(f"  ✗ {variation['name']}.html - Error: {render_err}")

    # Generate failure emails
    print("\nGenerating failure emails...")
    for variation in failure_variations:
        try:
            html = render_template("failure.html", variation["context"])
            output_file = output_dir / f"{variation['name']}.html"
            output_file.write_text(html, encoding="utf-8")
            print(f"  ✓ {variation['name']}.html")
        except (RuntimeError, OSError, IOError) as render_err:
            print(f"  ✗ {variation['name']}.html - Error: {render_err}")

    print(f"\n✓ All email previews generated in: {output_dir}")
    print(f"  Total files: {len(success_variations) + len(failure_variations)}")


if __name__ == "__main__":
    try:
        generate_previews()
    except (RuntimeError, OSError, IOError, ImportError) as err:
        print(f"Error generating previews: {err}", file=sys.stderr)
        sys.exit(1)
