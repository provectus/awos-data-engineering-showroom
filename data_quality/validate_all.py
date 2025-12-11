"""Validate all data sources using Great Expectations with pandas DataFrames.

This script runs data quality validations on all raw data tables
by loading them into pandas DataFrames and validating with GX.

Note: Uses pandas DataFrames instead of SQL connections due to
DuckDB/SQLAlchemy compatibility issues with GX.
"""

import sys
from pathlib import Path
from typing import Any

import duckdb
import great_expectations as gx
from great_expectations.core import ExpectationSuite


# Database and validation configuration
WAREHOUSE_PATH = Path(__file__).parent.parent / "duckdb" / "warehouse.duckdb"
GX_ROOT_DIR = Path(__file__).parent / "gx"

# Data sources to validate with their queries and expectation suites
DATA_SOURCES = {
    "bike_trips": {
        "query": "SELECT * FROM raw_bike.bike_trips",
        "suite_name": "bike_trips_suite",
    },
    "weather": {
        "query": "SELECT * FROM raw_weather.daily_weather",
        "suite_name": "weather_suite",
    },
    "holidays": {
        "query": "SELECT * FROM raw_holidays.us_holidays",
        "suite_name": "holidays_suite",
    },
    "games": {
        "query": "SELECT * FROM raw_games.mlb_games",
        "suite_name": "games_suite",
    },
}


def load_dataframe(query: str) -> "pd.DataFrame":
    """Load data from DuckDB into a pandas DataFrame.

    Args:
        query: SQL query to execute

    Returns:
        pandas DataFrame with query results
    """
    conn = duckdb.connect(str(WAREHOUSE_PATH), read_only=True)
    try:
        df = conn.execute(query).df()
        return df
    finally:
        conn.close()


def validate_dataframe(
    context: "gx.DataContext",
    df: "pd.DataFrame",
    source_name: str,
    suite_name: str,
) -> dict[str, Any]:
    """Validate a DataFrame against an expectation suite.

    Args:
        context: Great Expectations data context
        df: DataFrame to validate
        source_name: Name of the data source (for reporting)
        suite_name: Name of the expectation suite to use

    Returns:
        Dictionary with validation results
    """
    # Create or get pandas datasource
    ds_name = f"{source_name}_pandas"
    try:
        ds = context.data_sources.get(ds_name)
    except (KeyError, gx.exceptions.DataContextError):
        ds = context.data_sources.add_pandas(ds_name)

    # Create or get data asset
    asset_name = f"{source_name}_asset"
    try:
        asset = ds.get_asset(asset_name)
    except (KeyError, LookupError):
        asset = ds.add_dataframe_asset(name=asset_name)

    # Create batch definition
    batch_def_name = f"{source_name}_batch"
    try:
        batch_def = asset.get_batch_definition(batch_def_name)
    except (KeyError, LookupError):
        batch_def = asset.add_batch_definition_whole_dataframe(batch_def_name)

    # Get batch with data
    batch = batch_def.get_batch(batch_parameters={"dataframe": df})

    # Load expectation suite
    suite = context.suites.get(suite_name)

    # Run validation
    validation_result = batch.validate(suite)

    return {
        "success": validation_result.success,
        "statistics": validation_result.statistics,
        "results": [
            {
                "expectation_type": r.expectation_config.type,
                "success": r.success,
                "column": r.expectation_config.kwargs.get("column"),
                "result": r.result,
            }
            for r in validation_result.results
        ],
    }


def main() -> int | dict[str, Any]:
    """Run all data validations.

    When called directly, returns exit code (0=success, 1=failure).
    When imported and called, returns dict with detailed results.

    Returns:
        Exit code (int) when run as script, or results dict when imported
    """
    context = gx.get_context(mode="file", context_root_dir=GX_ROOT_DIR)

    results = {}
    all_success = True

    for source_name, config in DATA_SOURCES.items():
        print(f"Validating {source_name}...")

        # Load data
        df = load_dataframe(config["query"])
        print(f"  Loaded {len(df):,} rows")

        # Validate
        result = validate_dataframe(
            context=context,
            df=df,
            source_name=source_name,
            suite_name=config["suite_name"],
        )

        results[source_name] = result

        if result["success"]:
            print(f"  ✓ Validation PASSED")
        else:
            print(f"  ✗ Validation FAILED")
            all_success = False
            # Print failed expectations
            for r in result["results"]:
                if not r["success"]:
                    col = r["column"] or "table"
                    print(f"    - {r['expectation_type']} on {col}")

    # Return appropriate value based on how we're called
    if __name__ == "__main__":
        return 0 if all_success else 1
    else:
        return results


if __name__ == "__main__":
    sys.exit(main())