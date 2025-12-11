"""Airflow DAG for daily data quality checks.

This DAG runs independently of the ingestion DAG and:
1. Runs Great Expectations validations on all raw sources
2. Runs dbt tests
3. Stores results in data_quality schema
"""

import logging
import os
import subprocess
import sys
from datetime import timedelta
from pathlib import Path

import pendulum
from airflow import DAG
from airflow.decorators import task

# Disable progress bars and GX telemetry to avoid slowdowns in Airflow
os.environ["TQDM_DISABLE"] = "1"
os.environ["GE_USAGE_STATISTICS"] = "FALSE"

logger = logging.getLogger(__name__)

# Add parent directory to path to import our modules
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Absolute paths for subprocess execution
DBT_DIR = str(project_root / "dbt")

# Default arguments for all tasks
default_args = {
    "owner": "data-team",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "execution_timeout": timedelta(minutes=30),
}

# DAG definition
with DAG(
    dag_id="data_quality_dag",
    default_args=default_args,
    description="Daily data quality validation",
    schedule_interval="0 6 * * *",  # Daily at 6 AM UTC
    start_date=pendulum.datetime(2024, 1, 1, tz="UTC"),
    catchup=False,
    tags=["data-quality"],
) as dag:

    @task(
        doc_md="""
        ## Run Great Expectations Validations

        Validates all raw data sources using Great Expectations:
        - bike_trips: ride_id uniqueness, not_null checks, value ranges
        - weather: date uniqueness, temperature ranges
        - holidays: date uniqueness, not_null checks
        - games: game_id uniqueness, not_null checks

        Note: Runs as subprocess to isolate memory from Airflow scheduler.
        """
    )
    def run_gx_validations() -> dict:
        """Run Great Expectations validations as subprocess."""
        logger.info("Starting GX validations via subprocess...")

        # Run validation script as subprocess to isolate memory
        result = subprocess.run(
            ["python", str(project_root / "data_quality" / "validate_all.py")],
            cwd=str(project_root),
            capture_output=True,
            text=True,
            env={**os.environ, "TQDM_DISABLE": "1", "GE_USAGE_STATISTICS": "FALSE"},
        )

        logger.info(f"GX subprocess stdout: {result.stdout}")
        if result.stderr:
            logger.warning(f"GX subprocess stderr: {result.stderr}")

        # Parse results from stdout - check for pass/fail per source
        sources = ["bike_trips", "weather", "holidays", "games"]
        serializable_results = {}

        for source in sources:
            # Check if validation passed for this source
            passed = f"Validating {source}..." in result.stdout and "PASSED" in result.stdout.split(f"Validating {source}...")[-1].split("Validating")[0] if f"Validating {source}..." in result.stdout else False

            serializable_results[source] = {
                "success": passed,
                "statistics": {
                    "evaluated_expectations": 0,
                    "successful_expectations": 0,
                    "unsuccessful_expectations": 0,
                    "success_percent": 100.0 if passed else 0.0,
                },
            }

        # Overall success based on exit code
        all_passed = result.returncode == 0
        logger.info(f"GX validations completed. Exit code: {result.returncode}, All passed: {all_passed}")

        return serializable_results

    @task(
        doc_md="""
        ## Run dbt Tests

        Runs all dbt data quality tests including:
        - Uniqueness tests on primary keys
        - Not null tests on required columns
        - Accepted values tests
        - Custom SQL tests
        """
    )
    def run_dbt_tests() -> dict:
        """Run dbt tests and capture results."""
        result = subprocess.run(
            ["dbt", "test", "--profiles-dir", "."],
            cwd=DBT_DIR,
            capture_output=True,
            text=True,
        )

        # Parse the output to count tests
        output = result.stdout
        tests_passed = 0
        tests_failed = 0

        for line in output.split("\n"):
            if "PASS" in line:
                tests_passed += 1
            elif "FAIL" in line or "ERROR" in line:
                tests_failed += 1

        return {
            "returncode": result.returncode,
            "tests_passed": tests_passed,
            "tests_failed": tests_failed,
            "success": result.returncode == 0,
        }

    @task(
        doc_md="""
        ## Store Results

        Stores validation results in data_quality.test_results table:
        - Creates schema if not exists
        - Inserts results from both GX and dbt
        - Records run_id and timestamp for tracking

        Note: Runs as subprocess to isolate memory from Airflow scheduler.
        """
    )
    def store_results(gx_results: dict, dbt_results: dict) -> str:
        """Store validation results via subprocess."""
        import json

        logger.info("Storing results via subprocess...")

        gx_json = json.dumps(gx_results)
        dbt_json = json.dumps(dbt_results)

        result = subprocess.run(
            ["python", str(project_root / "data_quality" / "store_results.py"), gx_json, dbt_json],
            cwd=str(project_root),
            capture_output=True,
            text=True,
        )

        logger.info(f"Store results stdout: {result.stdout}")
        if result.stderr:
            logger.warning(f"Store results stderr: {result.stderr}")

        if result.returncode != 0:
            raise RuntimeError(f"Failed to store results: {result.stderr}")

        return result.stdout.strip()

    # Task instances
    gx_results = run_gx_validations()
    dbt_results = run_dbt_tests()
    store_task = store_results(gx_results, dbt_results)

    # Both validation tasks run in parallel, then store results
    [gx_results, dbt_results] >> store_task
