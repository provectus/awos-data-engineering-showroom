"""Helper script to run Great Expectations validations."""

import logging
import sys

import great_expectations as gx


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def validate_bike_trips(context_root_dir: str = "./great_expectations") -> bool:
    """Validate bike trips data using Great Expectations.

    Args:
        context_root_dir: Path to Great Expectations context directory

    Returns:
        True if validation passes, False otherwise
    """
    try:
        # Get the data context
        context = gx.get_context(context_root_dir=context_root_dir)

        # Get the checkpoint
        checkpoint = context.get_checkpoint("bike_trips_checkpoint")

        # Run the checkpoint with the bike trips table
        result = checkpoint.run(
            batch_request={
                "datasource_name": "bike_data",
                "data_connector_name": "default_runtime_data_connector",
                "data_asset_name": "bike_trips_table",
                "runtime_parameters": {"query": "SELECT * FROM raw_bike.bike_trips"},
            }
        )

        logger.info("Bike trips validation result: %s", result.success)
        return result.success

    except Exception as e:
        logger.exception("Error validating bike trips: %s", e)
        return False


def validate_weather(context_root_dir: str = "./great_expectations") -> bool:
    """Validate weather data using Great Expectations.

    Args:
        context_root_dir: Path to Great Expectations context directory

    Returns:
        True if validation passes, False otherwise
    """
    try:
        # Get the data context
        context = gx.get_context(context_root_dir=context_root_dir)

        # Get the checkpoint
        checkpoint = context.get_checkpoint("weather_checkpoint")

        # Run the checkpoint with the weather table
        result = checkpoint.run(
            batch_request={
                "datasource_name": "weather_data",
                "data_connector_name": "default_runtime_data_connector",
                "data_asset_name": "daily_weather_table",
                "runtime_parameters": {"query": "SELECT * FROM raw_weather.daily_weather"},
            }
        )

        logger.info("Weather validation result: %s", result.success)
        return result.success

    except Exception as e:
        logger.exception("Error validating weather: %s", e)
        return False


if __name__ == "__main__":
    # Determine which validation to run
    if len(sys.argv) > 1:
        validation_type = sys.argv[1]
        if validation_type == "bike":
            success = validate_bike_trips()
        elif validation_type == "weather":
            success = validate_weather()
        else:
            logger.error("Unknown validation type: %s", validation_type)
            sys.exit(1)
    else:
        # Run both
        bike_success = validate_bike_trips()
        weather_success = validate_weather()
        success = bike_success and weather_success

    sys.exit(0 if success else 1)
