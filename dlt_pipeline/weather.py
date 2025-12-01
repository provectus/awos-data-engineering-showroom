"""DLT pipeline for weather data ingestion using Open-Meteo API.

This module handles the extraction and loading of daily weather data
from the Open-Meteo API into a DuckDB data warehouse.
"""

import logging
import os
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path
from typing import Any

import dlt
import requests


logger = logging.getLogger(__name__)

# Set dlt project directory to find .dlt config folder
os.environ["DLT_PROJECT_DIR"] = str(Path(__file__).parent)


@dlt.resource(
    name="daily_weather",
    write_disposition="merge",
    primary_key="date",
    table_name="daily_weather",
)
def daily_weather(
    lat: float, lon: float, start_date: str, end_date: str
) -> Iterator[dict[str, Any]]:
    """Extract daily weather data from Open-Meteo API.

    Args:
        lat: Latitude coordinate
        lon: Longitude coordinate
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format

    Yields:
        Dictionary records of daily weather observations
    """
    url = (
        "https://archive-api.open-meteo.com/v1/archive"
        f"?latitude={lat}&longitude={lon}"
        f"&start_date={start_date}&end_date={end_date}"
        "&daily=temperature_2m_max,temperature_2m_min,"
        "precipitation_sum,wind_speed_10m_max"
        "&timezone=auto"
    )

    logger.info(
        "Fetching weather data from %s to %s for location (%s, %s)", start_date, end_date, lat, lon
    )

    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()

        if "daily" not in data:
            logger.warning("No daily weather data found in API response")
            return

        daily_data = data["daily"]
        dates = daily_data.get("time", [])
        temps_max = daily_data.get("temperature_2m_max", [])
        temps_min = daily_data.get("temperature_2m_min", [])
        precip = daily_data.get("precipitation_sum", [])
        wind_max = daily_data.get("wind_speed_10m_max", [])

        logger.info("Extracted %d days of weather data", len(dates))

        # Combine into records
        for i, date_str in enumerate(dates):
            record = {
                "date": date_str,
                "tmax": temps_max[i] if i < len(temps_max) else None,
                "tmin": temps_min[i] if i < len(temps_min) else None,
                "precip": precip[i] if i < len(precip) else None,
                "wind_max": wind_max[i] if i < len(wind_max) else None,
                "_dlt_load_timestamp": datetime.now(),
                "source_location": f"{lat},{lon}",
            }
            yield record

    except requests.exceptions.RequestException as e:
        logger.error("Error fetching weather data: %s", e)
        raise
    except (KeyError, ValueError) as e:
        logger.error("Error parsing weather data: %s", e)
        raise


def run_weather_pipeline(
    lat: float,
    lon: float,
    start_date: str,
    end_date: str,
    destination: str = "duckdb",
    dataset_name: str = "raw_weather",
) -> dict[str, Any]:
    """Run the weather data ingestion pipeline.

    Args:
        lat: Latitude coordinate
        lon: Longitude coordinate
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        destination: DLT destination name (default: "duckdb")
        dataset_name: Target dataset/schema name (default: "raw_weather")

    Returns:
        Pipeline execution result information
    """
    pipeline = dlt.pipeline(
        pipeline_name="weather_ingestion",
        destination=destination,
        dataset_name=dataset_name,
    )

    # Run the pipeline
    load_info = pipeline.run(daily_weather(lat, lon, start_date, end_date))

    # Log summary
    logger.info("Pipeline completed: %s", load_info)
    logger.info("Loaded %s loads", load_info.loads_ids)

    return load_info


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Example usage: fetch weather for NYC (May-June 2024)
    nyc_lat = 40.73
    nyc_lon = -73.94
    result = run_weather_pipeline(
        lat=nyc_lat,
        lon=nyc_lon,
        start_date="2024-05-01",
        end_date="2024-06-30",
    )
    logger.info("Weather ingestion complete. Result: %s", result)
