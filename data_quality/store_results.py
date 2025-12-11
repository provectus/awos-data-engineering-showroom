"""Store data quality results in DuckDB.

Usage:
    python store_results.py '<gx_results_json>' '<dbt_results_json>'
"""

import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import duckdb


DUCKDB_PATH = str(Path(__file__).parent.parent / "duckdb" / "warehouse.duckdb")


def store_results(gx_results: dict, dbt_results: dict) -> str:
    """Store validation results in DuckDB."""
    conn = duckdb.connect(DUCKDB_PATH)

    # Create schema and table if not exists
    conn.execute("CREATE SCHEMA IF NOT EXISTS data_quality")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS data_quality.test_results (
            run_id VARCHAR,
            run_timestamp TIMESTAMP,
            test_type VARCHAR,
            test_name VARCHAR,
            status VARCHAR,
            failure_message VARCHAR,
            source_name VARCHAR
        )
    """)

    run_id = str(uuid.uuid4())
    run_timestamp = datetime.now(tz=timezone.utc)

    # Store GX results
    for source_name, result in gx_results.items():
        status = "pass" if result["success"] else "fail"
        unsuccessful = result.get("statistics", {}).get("unsuccessful_expectations", 0)
        failure_msg = None if result["success"] else f"Failed {unsuccessful} expectations"

        conn.execute("""
            INSERT INTO data_quality.test_results VALUES (?, ?, ?, ?, ?, ?, ?)
        """, [
            run_id,
            run_timestamp,
            "gx",
            f"gx_{source_name}_validation",
            status,
            failure_msg,
            source_name,
        ])

    # Store dbt results
    dbt_status = "pass" if dbt_results.get("success", False) else "fail"
    dbt_failure_msg = None if dbt_results.get("success", False) else f"Failed {dbt_results.get('tests_failed', 0)} tests"

    conn.execute("""
        INSERT INTO data_quality.test_results VALUES (?, ?, ?, ?, ?, ?, ?)
    """, [
        run_id,
        run_timestamp,
        "dbt",
        "dbt_test_suite",
        dbt_status,
        dbt_failure_msg,
        "all",
    ])

    conn.close()

    return run_id


def main():
    if len(sys.argv) != 3:
        print("Usage: python store_results.py '<gx_results_json>' '<dbt_results_json>'")
        sys.exit(1)

    gx_results = json.loads(sys.argv[1])
    dbt_results = json.loads(sys.argv[2])

    run_id = store_results(gx_results, dbt_results)
    print(f"Stored results for run {run_id}")


if __name__ == "__main__":
    main()