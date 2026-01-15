"""
Azure Functions entry point.
Defines Azure Functions that delegate to function_app module.
"""

import azure.functions as func  # type: ignore[reportMissingImports]
from .config import config

# Lazy import function_app to avoid loading sql_client/pyodbc unless needed
def _get_run_monthly_pipeline():
    """Lazy import to avoid loading sql_client when not needed."""
    from .function_app import run_monthly_pipeline
    return run_monthly_pipeline


def monthly_timer_trigger(_timer: func.TimerRequest) -> None:
    """Timer trigger for monthly churn scoring."""
    run_monthly_pipeline = _get_run_monthly_pipeline()
    run_monthly_pipeline()


def score_http_trigger(_req: func.HttpRequest) -> func.HttpResponse:
    """HTTP endpoint for manual scoring trigger."""
    try:
        run_monthly_pipeline = _get_run_monthly_pipeline()
        result = run_monthly_pipeline()
        return func.HttpResponse(
            f"Pipeline completed successfully. Rows scored: {result['rows_scored']}",
            status_code=200
        )
    except (ValueError, ConnectionError, TimeoutError, OSError) as e:
        return func.HttpResponse(
            f"Pipeline failed: {str(e)}",
            status_code=500
        )


def health_check(_req: func.HttpRequest) -> func.HttpResponse:
    """Health check endpoint."""
    try:
        config.validate()
        return func.HttpResponse("OK", status_code=200)
    except ValueError as e:
        return func.HttpResponse(f"Configuration error: {str(e)}", status_code=500)
