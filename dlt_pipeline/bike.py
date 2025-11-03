"""DLT pipeline for NYC Citi Bike trip data ingestion.

This module handles the extraction and loading of bike-share trip data
from publicly available CSV files into a DuckDB data warehouse.
"""

import logging
from collections.abc import Iterator
from datetime import datetime
from typing import Any

import dlt
import polars as pl
import requests


logger = logging.getLogger(__name__)


@dlt.resource(
    name="bike_trips",
    write_disposition="merge",
    primary_key="ride_id",
    table_name="bike_trips",
)
def bike_trips(months: list[str], base_url: str | None = None) -> Iterator[dict[str, Any]]:
    """Extract bike trip data from monthly CSV files.

    Args:
        months: List of month strings in YYYY-MM format (e.g., ["2024-05", "2024-06"])
        base_url: Base URL for Citi Bike data (defaults to S3 bucket)

    Yields:
        Dictionary records of bike trips with normalized timestamps
    """
    if base_url is None:
        base_url = "https://s3.amazonaws.com/tripdata"

    for month_str in months:
        url = f"{base_url}/{month_str}-citibike-tripdata.csv.zip"
        logger.info("Processing bike data for %s from %s", month_str, url)

        try:
            # Download and parse CSV with Polars for efficiency
            # Note: Polars can read directly from URLs and handle zip files
            df = pl.read_csv(
                url,
                try_parse_dates=True,
                ignore_errors=True,
                rechunk=True,
            )

            # Normalize column names to snake_case
            df = df.rename({col: col.lower().replace(" ", "_") for col in df.columns})

            # Ensure datetime columns are properly parsed
            datetime_cols = ["started_at", "ended_at"]
            for col in datetime_cols:
                if col in df.columns:
                    df = df.with_columns(
                        pl.col(col).str.strptime(
                            pl.Datetime("us"),
                            format="%Y-%m-%d %H:%M:%S%.f",
                            strict=False,
                        )
                    )

            # Calculate ride duration in minutes if not present
            if "ride_mins" not in df.columns and all(
                col in df.columns for col in ["started_at", "ended_at"]
            ):
                df = df.with_columns(
                    ((pl.col("ended_at") - pl.col("started_at")).dt.total_seconds() / 60.0).alias(
                        "ride_mins"
                    )
                )

            # Add ingestion metadata
            df = df.with_columns(
                pl.lit(datetime.now()).alias("_dlt_load_timestamp"),
                pl.lit(month_str).alias("source_month"),
            )

            # Convert to dictionaries for dlt
            records = df.to_dicts()
            logger.info("Extracted %d records for %s", len(records), month_str)

            # Yield records in batches for memory efficiency
            batch_size = 10000
            for i in range(0, len(records), batch_size):
                batch = records[i : i + batch_size]
                yield from batch

        except requests.exceptions.RequestException as e:
            logger.error("Error downloading data for %s: %s", month_str, e)
            continue
        except Exception as e:
            logger.exception("Error processing data for %s: %s", month_str, e)
            continue


def run_bike_pipeline(
    months: list[str],
    destination: str = "duckdb",
    dataset_name: str = "raw_bike",
) -> dict[str, Any]:
    """Run the bike data ingestion pipeline.

    Args:
        months: List of month strings to ingest
        destination: DLT destination name (default: "duckdb")
        dataset_name: Target dataset/schema name (default: "raw_bike")

    Returns:
        Pipeline execution result information
    """
    pipeline = dlt.pipeline(
        pipeline_name="bike_ingestion",
        destination=destination,
        dataset_name=dataset_name,
    )

    # Run the pipeline
    load_info = pipeline.run(bike_trips(months))

    # Log summary
    logger.info("Pipeline completed: %s", load_info)
    logger.info("Loaded %s loads", load_info.loads_ids)

    return load_info


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Example usage: ingest May and June 2024 data
    months_to_load = ["2024-05", "2024-06"]
    result = run_bike_pipeline(months_to_load)
    logger.info("Ingestion complete. Result: %s", result)
