"""Validate weather data using Great Expectations.

This script runs data quality validations on the daily_weather table
from the weather_ingestion DuckDB database.
"""

import sys
from pathlib import Path

import great_expectations as gx


def main() -> int:
    """Run weather data validation.

    Returns:
        0 if validation succeeds, 1 if validation fails
    """
    context = gx.get_context(mode='file', context_root_dir=Path(__file__).parent / 'gx')

    checkpoint = context.checkpoints.get("weather_checkpoint")
    result = checkpoint.run()

    return result.success


if __name__ == "__main__":
    sys.exit(main())

