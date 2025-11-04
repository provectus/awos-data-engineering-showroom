"""DLT pipeline for US holiday data ingestion using Nager.Date API.

This module handles the extraction and loading of US federal and New York state holidays
from the Nager.Date API into a DuckDB data warehouse.
"""

import logging
import time
from collections.abc import Iterator
from datetime import datetime
from typing import Any

import dlt
import requests


logger = logging.getLogger(__name__)


@dlt.resource(
    name="us_holidays",
    write_disposition="merge",
    primary_key="date",
    table_name="us_holidays",
)
def us_holidays(years: list[int]) -> Iterator[dict[str, Any]]:
    """Extract US holiday data from Nager.Date API.

    Fetches nationwide US federal holidays and New York state-specific holidays
    for the specified years.

    Args:
        years: List of years to fetch holiday data for (e.g., [2024, 2025])

    Yields:
        Dictionary records of holiday information with the following fields:
        - date: Holiday date (YYYY-MM-DD)
        - holiday_name: Official holiday name
        - local_name: Local/alternative name
        - is_nationwide: Whether holiday applies to all states
        - is_fixed: Whether holiday date is fixed annually
        - holiday_types: Comma-separated list of holiday types
        - counties: Comma-separated state codes (null if nationwide)
        - _dlt_load_timestamp: Ingestion timestamp
    """
    base_url = "https://date.nager.at/api/v3/PublicHolidays"
    timeout = 30
    max_retries = 3

    for year in years:
        url = f"{base_url}/{year}/US"
        logger.info("Fetching holiday data for year %d from %s", year, url)

        # Retry logic with exponential backoff
        for attempt in range(max_retries):
            try:
                response = requests.get(url, timeout=timeout)
                response.raise_for_status()
                holidays_data = response.json()

                if not isinstance(holidays_data, list):
                    logger.warning("Unexpected API response format for year %d", year)
                    break

                # Filter holidays: include nationwide OR NY-specific
                filtered_count = 0
                for holiday in holidays_data:
                    # Check if holiday is nationwide
                    is_nationwide = holiday.get("global", False)

                    # Check if holiday is NY-specific
                    counties = holiday.get("counties", None)
                    is_ny_specific = False
                    if counties and isinstance(counties, list):
                        is_ny_specific = any(c.startswith("US-NY") for c in counties)

                    # Include if nationwide OR NY-specific
                    if is_nationwide or is_ny_specific:
                        # Convert counties list to comma-separated string
                        counties_str = None
                        if counties and isinstance(counties, list):
                            counties_str = ", ".join(counties)

                        # Convert types list to comma-separated string
                        types = holiday.get("types", [])
                        types_str = ", ".join(types) if types else None

                        record = {
                            "date": holiday.get("date"),
                            "holiday_name": holiday.get("name"),
                            "local_name": holiday.get("localName"),
                            "is_nationwide": is_nationwide,
                            "is_fixed": holiday.get("fixed", False),
                            "holiday_types": types_str,
                            "counties": counties_str,
                            "_dlt_load_timestamp": datetime.now(),
                        }
                        filtered_count += 1
                        yield record

                logger.info(
                    "Extracted %d holidays for year %d (filtered from %d total)",
                    filtered_count,
                    year,
                    len(holidays_data),
                )
                break  # Success, exit retry loop

            except requests.exceptions.Timeout:
                logger.warning(
                    "Timeout fetching holidays for year %d (attempt %d/%d)",
                    year,
                    attempt + 1,
                    max_retries,
                )
                if attempt < max_retries - 1:
                    # Exponential backoff: 2^attempt seconds
                    sleep_time = 2**attempt
                    logger.info("Retrying in %d seconds...", sleep_time)
                    time.sleep(sleep_time)
                else:
                    logger.error("Max retries reached for year %d, skipping", year)

            except requests.exceptions.RequestException as e:
                logger.error(
                    "Error fetching holidays for year %d (attempt %d/%d): %s",
                    year,
                    attempt + 1,
                    max_retries,
                    e,
                )
                if attempt < max_retries - 1:
                    sleep_time = 2**attempt
                    logger.info("Retrying in %d seconds...", sleep_time)
                    time.sleep(sleep_time)
                else:
                    logger.error("Max retries reached for year %d, skipping", year)

            except (KeyError, ValueError, TypeError) as e:
                logger.error("Error parsing holiday data for year %d: %s", year, e)
                break  # Don't retry parsing errors


def run_holiday_pipeline(
    years: list[int],
    dataset_name: str = "raw_holidays",
) -> dict[str, Any]:
    """Run the holiday data ingestion pipeline.

    Args:
        years: List of years to fetch holiday data for
        dataset_name: Target dataset/schema name (default: "raw_holidays")

    Returns:
        Pipeline execution result information
    """
    # Configure DuckDB destination with explicit database path
    # Note: We use a dedicated database file for holiday data to separate concerns
    pipeline = dlt.pipeline(
        pipeline_name="holiday_ingestion",
        destination=dlt.destinations.duckdb(credentials="duckdb/holiday_ingestion.duckdb"),
        dataset_name=dataset_name,
    )

    logger.info("Starting holiday data ingestion pipeline for years: %s", years)

    # Run the pipeline
    load_info = pipeline.run(us_holidays(years))

    # Log summary
    logger.info("Pipeline completed: %s", load_info)
    logger.info("Loaded %s loads", load_info.loads_ids)

    return load_info


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Fetch holidays for 2024 and 2025
    years_to_fetch = [2024, 2025]
    logger.info("Fetching US holidays for years: %s", years_to_fetch)

    result = run_holiday_pipeline(years=years_to_fetch)

    logger.info("Holiday ingestion complete. Result: %s", result)
