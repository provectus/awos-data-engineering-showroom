"""Airflow DAG for bike, weather, game, and holiday data pipeline.

This DAG orchestrates the complete data pipeline:
1. Ingest bike trip data (dlt)
2. Ingest weather data (dlt)
3. Ingest MLB game data (dlt)
4. Ingest US holiday data (dlt)
5. Transform data (dbt)
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path

import pendulum
from airflow import DAG
from airflow.decorators import task
from airflow.operators.bash import BashOperator


def get_previous_month_range() -> tuple[str, str]:
    """Calculate first and last day of previous month.

    Returns:
        Tuple of (start_date, end_date) in YYYY-MM-DD format
    """
    today = datetime.now()
    first_of_current = today.replace(day=1)
    last_of_previous = first_of_current - timedelta(days=1)
    first_of_previous = last_of_previous.replace(day=1)
    return first_of_previous.strftime("%Y-%m-%d"), last_of_previous.strftime("%Y-%m-%d")


def get_months_from_date_range(start_date: str, end_date: str) -> list[str]:
    """Convert date range to list of months in YYYYMM format.

    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format

    Returns:
        List of month strings, e.g., ["202411", "202412"]
    """
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")

    months = []
    current = start
    while current <= end:
        months.append(current.strftime("%Y%m"))
        if current.month == 12:
            current = current.replace(year=current.year + 1, month=1)
        else:
            current = current.replace(month=current.month + 1)

    return list(dict.fromkeys(months))  # Remove duplicates, preserve order

# Add parent directory to path to import our modules
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Absolute path to DuckDB for Airflow execution
DUCKDB_PATH = str(project_root / "duckdb" / "warehouse.duckdb")

from dlt_pipeline.bike import run_bike_pipeline  # noqa: E402
from dlt_pipeline.weather import run_weather_pipeline  # noqa: E402
from dlt_pipeline.games import run_game_pipeline  # noqa: E402
from dlt_pipeline.holidays import run_holiday_pipeline  # noqa: E402


# Default arguments for all tasks
default_args = {
    "owner": "data-team",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "execution_timeout": timedelta(hours=1),
}

# Calculate default date range (previous month)
default_start, default_end = get_previous_month_range()

# DAG definition using context manager
with DAG(
    dag_id="bike_weather_pipeline",
    default_args=default_args,
    description="End-to-end bike and weather data pipeline",
    schedule_interval="@weekly",
    start_date=pendulum.datetime(2024, 5, 1, tz="UTC"),
    catchup=False,
    tags=["data-ingestion", "analytics", "demo"],
    params={
        "period_start_date": default_start,
        "period_end_date": default_end,
    },
) as dag:

    @task(
        doc_md="""
        ## Ingest Bike Data

        Extracts bike trip data from NYC Citi Bike open data API and loads into DuckDB.
        Uses dlt for idempotent, incremental loading.
        """
    )
    def ingest_bike_data(**context) -> str:
        """Task to ingest bike trip data using dlt."""
        period_start = context["params"]["period_start_date"]
        period_end = context["params"]["period_end_date"]
        months = get_months_from_date_range(period_start, period_end)

        result = run_bike_pipeline(months, credentials_path=DUCKDB_PATH)
        return str(result)

    @task(
        doc_md="""
        ## Ingest Weather Data

        Fetches daily weather observations from Open-Meteo API and loads into DuckDB.
        Covers the same time period as bike data for correlation analysis.
        """
    )
    def ingest_weather_data(**context) -> str:
        """Task to ingest weather data using dlt."""
        period_start = context["params"]["period_start_date"]
        period_end = context["params"]["period_end_date"]
        # NYC coordinates
        lat = 40.73
        lon = -73.94

        result = run_weather_pipeline(lat, lon, period_start, period_end, credentials_path=DUCKDB_PATH)
        return str(result)

    @task(
        doc_md="""
        ## Ingest MLB Game Data

        Fetches NY Yankees and NY Mets home game schedules from MLB Stats API.
        Used to analyze bike demand patterns on game days vs non-game days.
        """
    )
    def ingest_game_data(**context) -> str:
        """Task to ingest MLB game data using dlt."""
        period_start = context["params"]["period_start_date"]
        period_end = context["params"]["period_end_date"]

        result = run_game_pipeline(period_start, period_end, credentials_path=DUCKDB_PATH)
        return str(result)

    @task(
        doc_md="""
        ## Ingest US Holiday Data

        Fetches US public holidays from Nager.Date API and loads into DuckDB.
        Used to analyze bike demand patterns on holidays vs regular days.
        """
    )
    def ingest_holiday_data(**context) -> str:
        """Task to ingest US holiday data using dlt."""
        period_start = context["params"]["period_start_date"]
        period_end = context["params"]["period_end_date"]

        # Extract unique years from date range
        start_year = int(period_start[:4])
        end_year = int(period_end[:4])
        years = list(range(start_year, end_year + 1))

        result = run_holiday_pipeline(years, credentials_path=DUCKDB_PATH)
        return str(result)

    # Task definitions
    ingest_bike = ingest_bike_data()
    ingest_weather = ingest_weather_data()
    ingest_games = ingest_game_data()
    ingest_holidays = ingest_holiday_data()

    dbt_deps = BashOperator(
        task_id="dbt_deps",
        bash_command=f"cd {project_root}/dbt && dbt deps --profiles-dir .",
        trigger_rule="all_done",  # Run even if upstream tasks fail
        doc_md="""
        ## Install dbt Dependencies

        Installs required dbt packages (dbt_utils, etc.)
        Runs regardless of ingestion task success/failure.
        """,
    )

    dbt_build = BashOperator(
        task_id="dbt_build",
        bash_command=f"cd {project_root}/dbt && dbt build --profiles-dir .",
        doc_md="""
        ## dbt Build

        Runs all dbt models and tests:
        - Staging: Clean and normalize raw data
        - Core: Build dimensions and facts
        - Marts: Create business-ready analytics tables
        """,
    )

    dbt_docs_generate = BashOperator(
        task_id="dbt_docs_generate",
        bash_command=f"cd {project_root}/dbt && dbt docs generate --profiles-dir .",
        doc_md="""
        ## Generate dbt Documentation

        Creates up-to-date documentation and lineage diagrams for all dbt models.
        """,
    )

    # Pipeline dependencies - all 4 ingestion tasks run in parallel
    ingestion_tasks = [ingest_bike, ingest_weather, ingest_games, ingest_holidays]
    ingestion_tasks >> dbt_deps >> dbt_build >> dbt_docs_generate
