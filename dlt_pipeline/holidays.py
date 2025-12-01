"""DLT pipeline for US holiday data ingestion using Nager.Date API.

This module handles the extraction and loading of US public holiday data
from the Nager.Date API into a DuckDB data warehouse.
"""

import logging
import os
import time
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
    name="us_holidays",
    write_disposition="merge",
    primary_key="date",
    table_name="us_holidays",
)
def us_holidays(years: list[int]) -> Iterator[dict[str, Any]]:
    """Extract US public holiday data from Nager.Date API.

    Args:
        years: List of years to fetch holidays for (e.g., [2024, 2025])

    Yields:
        Dictionary records of US public holidays with all API fields.
        Holidays on the same date are intelligently merged:
        - Names concatenated with ' and '
        - Counties merged (comma-separated, deduplicated)
        - Types prioritized: 'Public' > 'Federal' > others
    """
    # Slice 4: Process all years in the list with retry logic
    for year in years:
        logger.info("Fetching US holidays for year %d", year)

        url = f"https://date.nager.at/api/v3/PublicHolidays/{year}/US"

        # Retry logic with exponential backoff
        max_retries = 3
        backoff_delays = [1, 2, 4]  # seconds

        data = None
        last_error = None

        for attempt in range(max_retries):
            try:
                response = requests.get(url, timeout=30)
                response.raise_for_status()
                data = response.json()

                # Success - break out of retry loop
                break

            except requests.exceptions.RequestException as e:
                last_error = e
                if attempt < max_retries - 1:
                    delay = backoff_delays[attempt]
                    logger.warning(
                        "Attempt %d/%d failed for year %d: %s. Retrying in %d seconds...",
                        attempt + 1, max_retries, year, e, delay
                    )
                    time.sleep(delay)
                else:
                    # Final attempt failed - raise exception to fail pipeline
                    logger.error(
                        "All %d attempts failed for year %d: %s. Pipeline will fail.",
                        max_retries, year, e
                    )
                    raise

        if not data:
            logger.warning("No holiday data found in API response for year %d", year)
            continue

        logger.info("Fetched %d holidays for year %d", len(data), year)

        # Group holidays by date for intelligent merging
        from collections import defaultdict
        holidays_by_date = defaultdict(list)
        for holiday in data:
            holidays_by_date[holiday.get("date")].append(holiday)

        # Merge holidays on the same date
        try:
            for date, holidays in holidays_by_date.items():
                if len(holidays) > 1:
                    logger.info("Merging %d holidays for date %s", len(holidays), date)

                # Merge multiple holidays on same date
                merged = _merge_holidays(holidays)

                record = {
                    "date": merged["date"],
                    "holiday_name": merged["holiday_name"],
                    "local_name": merged["local_name"],
                    "country_code": merged["country_code"],
                    "is_fixed": merged["is_fixed"],
                    "is_global": merged["is_global"],
                    "counties": merged["counties"],
                    "launch_year": merged["launch_year"],
                    "holiday_types": merged["holiday_types"],
                    "_dlt_load_timestamp": datetime.now(),
                    "source_year": year,
                }
                logger.debug("Yielding holiday: %s on %s", record.get("holiday_name"), record.get("date"))
                yield record

        except (KeyError, ValueError) as e:
            logger.error("Error parsing holiday data: %s", e)
            raise


def _merge_holidays(holidays: list[dict[str, Any]]) -> dict[str, Any]:
    """Merge multiple holidays on the same date.

    Args:
        holidays: List of holiday records for the same date

    Returns:
        Merged holiday record with:
        - Names concatenated with ' and '
        - Counties merged (comma-separated, deduplicated)
        - Types prioritized: 'Public' > 'Federal' > others
        - is_global: True if any is global
        - is_fixed: True if any is fixed
    """
    if len(holidays) == 1:
        holiday = holidays[0]
        types = holiday.get("types", [])
        counties = holiday.get("counties")
        return {
            "date": holiday.get("date"),
            "holiday_name": holiday.get("name"),
            "local_name": holiday.get("localName"),
            "country_code": holiday.get("countryCode"),
            "is_fixed": holiday.get("fixed"),
            "is_global": holiday.get("global"),
            "counties": ",".join(counties) if counties else None,
            "launch_year": holiday.get("launchYear"),
            "holiday_types": ",".join(types) if types else None,
        }

    # Multiple holidays - merge them
    names = []
    local_names = []
    all_types = []
    all_counties = set()
    is_global = False
    is_fixed = False
    launch_years = []

    for holiday in holidays:
        name = holiday.get("name")
        if name and name not in names:
            names.append(name)

        local_name = holiday.get("localName")
        if local_name and local_name not in local_names:
            local_names.append(local_name)

        types = holiday.get("types", [])
        all_types.extend(types)

        counties = holiday.get("counties")
        if counties:
            all_counties.update(counties)

        if holiday.get("global"):
            is_global = True
        if holiday.get("fixed"):
            is_fixed = True

        launch_year = holiday.get("launchYear")
        if launch_year:
            launch_years.append(launch_year)

    # Prioritize Public > Federal > others
    type_priority = {"Public": 1, "Federal": 2}
    unique_types = sorted(set(all_types), key=lambda t: (type_priority.get(t, 999), t))

    return {
        "date": holidays[0].get("date"),
        "holiday_name": " and ".join(names),
        "local_name": " and ".join(local_names) if local_names else holidays[0].get("localName"),
        "country_code": holidays[0].get("countryCode"),
        "is_fixed": is_fixed,
        "is_global": is_global,
        "counties": ",".join(sorted(all_counties)) if all_counties else None,
        "launch_year": min(launch_years) if launch_years else None,
        "holiday_types": ",".join(unique_types) if unique_types else None,
    }


def run_holiday_pipeline(
    years: list[int],
    destination: str = "duckdb",
    dataset_name: str = "raw_holidays",
) -> dict[str, Any]:
    """Run the holiday data ingestion pipeline.

    Args:
        years: List of years to ingest holidays for
        destination: DLT destination name (default: "duckdb")
        dataset_name: Target dataset/schema name (default: "raw_holidays")

    Returns:
        Pipeline execution result information
    """
    pipeline = dlt.pipeline(
        pipeline_name="holiday_ingestion",
        destination=destination,
        dataset_name=dataset_name,
    )

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

    # Example usage: ingest 2024 US holidays
    result = run_holiday_pipeline([2024])
    logger.info("Holiday ingestion complete. Result: %s", result)