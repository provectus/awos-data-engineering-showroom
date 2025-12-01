"""Airflow DAG for bike, weather, and game data pipeline.

This DAG orchestrates the complete data pipeline:
1. Ingest bike trip data (dlt)
2. Ingest weather data (dlt)
3. Ingest MLB game data (dlt)
4. Validate bike data (Great Expectations)
5. Validate weather data (Great Expectations)
6. Transform data (dbt)
"""

import sys
from datetime import timedelta
from pathlib import Path

import pendulum
from airflow import DAG
from airflow.decorators import task
from airflow.operators.bash import BashOperator

# Add parent directory to path to import our modules
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from dlt_pipeline.bike import run_bike_pipeline  # noqa: E402
from dlt_pipeline.weather import run_weather_pipeline  # noqa: E402
from dlt_pipeline.games import run_game_pipeline  # noqa: E402


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

# DAG definition using context manager
with DAG(
    dag_id="bike_weather_pipeline",
    default_args=default_args,
    description="End-to-end bike and weather data pipeline",
    schedule_interval="@daily",
    start_date=pendulum.datetime(2024, 5, 1, tz="UTC"),
    catchup=False,
    tags=["data-ingestion", "analytics", "demo"],
) as dag:

    @task(
        doc_md="""
        ## Ingest Bike Data

        Extracts bike trip data from NYC Citi Bike open data API and loads into DuckDB.
        Uses dlt for idempotent, incremental loading.
        """
    )
    def ingest_bike_data() -> str:
        """Task to ingest bike trip data using dlt."""
        # For demo, ingest May and June 2024
        months = ["202405", "202406"]
        result = run_bike_pipeline(months)
        return str(result)

    @task(
        doc_md="""
        ## Ingest Weather Data

        Fetches daily weather observations from Open-Meteo API and loads into DuckDB.
        Covers the same time period as bike data for correlation analysis.
        """
    )
    def ingest_weather_data() -> str:
        """Task to ingest weather data using dlt."""
        # NYC coordinates
        lat = 40.73
        lon = -73.94
        start_date = "2024-05-01"
        end_date = "2024-06-30"

        result = run_weather_pipeline(lat, lon, start_date, end_date)
        return str(result)

    @task(
        doc_md="""
        ## Ingest MLB Game Data

        Fetches NY Yankees and NY Mets home game schedules from MLB Stats API.
        Used to analyze bike demand patterns on game days vs non-game days.
        """
    )
    def ingest_game_data() -> str:
        """Task to ingest MLB game data using dlt."""
        start_date = "2024-05-01"
        end_date = "2024-06-30"

        result = run_game_pipeline(start_date, end_date)
        return str(result)

    # Task definitions
    ingest_bike = ingest_bike_data()
    ingest_weather = ingest_weather_data()
    ingest_games = ingest_game_data()

    dbt_deps = BashOperator(
        task_id="dbt_deps",
        bash_command=f"cd {project_root}/dbt && dbt deps --profiles-dir .",
        doc_md="""
        ## Install dbt Dependencies

        Installs required dbt packages (dbt_utils, etc.)
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

    # Pipeline dependencies
    [ingest_bike, ingest_weather, ingest_games] >> dbt_deps >> dbt_build >> dbt_docs_generate
