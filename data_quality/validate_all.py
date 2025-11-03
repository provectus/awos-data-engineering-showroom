"""Validate all data sources using Great Expectations.

This script runs data quality validations on both bike trips
and weather data.
"""

import sys
from pathlib import Path

import great_expectations as gx


def main() -> int:
    """Run all data validations.

    Returns:
        0 if all validations succeed, 1 if any validation fails
    """
    context = gx.get_context(mode='file', context_root_dir=Path(__file__).parent / 'gx')

    results = {}

    # Validate bike trips
    bike_checkpoint = context.checkpoints.get("bike_trips_checkpoint")
    bike_result = bike_checkpoint.run()
    results['bike_trips'] = bike_result.success

    # Validate weather
    weather_checkpoint = context.checkpoints.get("weather_checkpoint")
    weather_result = weather_checkpoint.run()
    results['weather'] = weather_result.success

    return 0 if all(results.values()) else 1

if __name__ == "__main__":
    sys.exit(main())

