"""Airflow DAG for bike and weather data pipeline.

This DAG orchestrates the complete data pipeline:
1. Ingest bike trip data (dlt)
2. Ingest weather data (dlt)
3. Validate bike data (Great Expectations)
4. Validate weather data (Great Expectations)
5. Transform data (dbt)
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path

from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator

from airflow import DAG

# Add parent directory to path to import our modules
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from dlt_pipeline.bike import run_bike_pipeline  # noqa: E402
from dlt_pipeline.weather import run_weather_pipeline  # noqa: E402
from great_expectations.validate_data import (  # noqa: E402
    validate_bike_trips,
)
from great_expectations.validate_data import (
    validate_weather as validate_weather_fn,
)

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

# DAG definition
dag = DAG(
    "bike_weather_pipeline",
    default_args=default_args,
    description="End-to-end bike and weather data pipeline",
    schedule="@daily",
    start_date=datetime(2024, 5, 1),
    catchup=False,
    tags=["data-ingestion", "analytics", "demo"],
)


def ingest_bike_data_task(**context):
    """Task to ingest bike trip data using dlt."""
    # For demo, ingest May and June 2024
    months = ["2024-05", "2024-06"]
    result = run_bike_pipeline(months)
    context["ti"].xcom_push(key="bike_load_info", value=str(result))
    return "Bike data ingested successfully"


def ingest_weather_data_task(**context):
    """Task to ingest weather data using dlt."""
    # NYC coordinates
    lat = 40.73
    lon = -73.94
    start_date = "2024-05-01"
    end_date = "2024-06-30"

    result = run_weather_pipeline(lat, lon, start_date, end_date)
    context["ti"].xcom_push(key="weather_load_info", value=str(result))
    return "Weather data ingested successfully"


def validate_bike_data_task():
    """Task to validate bike data using Great Expectations."""
    success = validate_bike_trips(context_root_dir=str(project_root / "great_expectations"))
    if not success:
        msg = "Bike data validation failed"
        raise ValueError(msg)
    return "Bike data validation passed"


def validate_weather_data_task():
    """Task to validate weather data using Great Expectations."""
    success = validate_weather_fn(context_root_dir=str(project_root / "great_expectations"))
    if not success:
        msg = "Weather data validation failed"
        raise ValueError(msg)
    return "Weather data validation passed"


# Task definitions
ingest_bike = PythonOperator(
    task_id="ingest_bike_data",
    python_callable=ingest_bike_data_task,
    dag=dag,
    doc_md="""
    ## Ingest Bike Data

    Extracts bike trip data from NYC Citi Bike open data API and loads into DuckDB.
    Uses dlt for idempotent, incremental loading.
    """,
)

ingest_weather = PythonOperator(
    task_id="ingest_weather_data",
    python_callable=ingest_weather_data_task,
    dag=dag,
    doc_md="""
    ## Ingest Weather Data

    Fetches daily weather observations from Open-Meteo API and loads into DuckDB.
    Covers the same time period as bike data for correlation analysis.
    """,
)

validate_bike = PythonOperator(
    task_id="validate_bike_data",
    python_callable=validate_bike_data_task,
    dag=dag,
    doc_md="""
    ## Validate Bike Data

    Runs Great Expectations validation suite on ingested bike data:
    - Schema validation
    - Data quality checks
    - Business rule validation
    """,
)

validate_weather = PythonOperator(
    task_id="validate_weather_data",
    python_callable=validate_weather_data_task,
    dag=dag,
    doc_md="""
    ## Validate Weather Data

    Runs Great Expectations validation suite on weather data:
    - Temperature range checks
    - Precipitation non-negative
    - Date uniqueness
    """,
)

dbt_deps = BashOperator(
    task_id="dbt_deps",
    bash_command=f"cd {project_root}/dbt && dbt deps --profiles-dir .",
    dag=dag,
    doc_md="""
    ## Install dbt Dependencies

    Installs required dbt packages (dbt_utils, etc.)
    """,
)

dbt_build = BashOperator(
    task_id="dbt_build",
    bash_command=f"cd {project_root}/dbt && dbt build --profiles-dir .",
    dag=dag,
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
    dag=dag,
    doc_md="""
    ## Generate dbt Documentation

    Creates up-to-date documentation and lineage diagrams for all dbt models.
    """,
)

# Pipeline dependencies
# Validation after ingestion
ingest_bike >> validate_bike
ingest_weather >> validate_weather

# dbt transformation after both validations pass
[validate_bike, validate_weather] >> dbt_deps >> dbt_build >> dbt_docs_generate
