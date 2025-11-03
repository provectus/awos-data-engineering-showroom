"""DLT pipeline for NYC Citi Bike trip data ingestion.

This module handles the extraction and loading of bike-share trip data
from publicly available CSV files into a DuckDB data warehouse.
"""

import logging
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path
from typing import Any
from zipfile import ZipFile

import dlt
import polars as pl
import requests


logger = logging.getLogger(__name__)

# Local directory for downloaded files
DOWNLOAD_DIR = Path(".cache/bike_data")
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)


def download_bike_data(month_str: str, base_url: str) -> Path:
    """Download bike trip data file to local storage.

    Args:
        month_str: Month string in YYYYMM format (e.g., "202405")
        base_url: Base URL for Citi Bike data

    Returns:
        Path to the downloaded file

    Raises:
        requests.exceptions.RequestException: If download fails
    """
    url = f"{base_url}/{month_str}-citibike-tripdata.zip"
    local_file = DOWNLOAD_DIR / f"{month_str}-citibike-tripdata.zip"

    # Skip download if file already exists
    if local_file.exists():
        logger.info("Using cached file for %s: %s", month_str, local_file)
        return local_file

    logger.info("Downloading bike data for %s from %s", month_str, url)

    # Download with streaming to handle large files
    response = requests.get(url, stream=True, timeout=300)
    response.raise_for_status()

    # Write to local file
    with open(local_file, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)

    logger.info("Downloaded %s to %s", month_str, local_file)
    return local_file


def unzip_bike_data(zip_file: Path) -> list[Path]:
    """Unzip downloaded bike trip data file.

    Args:
        zip_file: Path to the zip file

    Returns:
        List of paths to extracted CSV files
    """
    # Create extraction directory (same name as zip file without extension)
    extract_dir = zip_file.parent / zip_file.stem

    # Skip extraction if directory already exists and has CSV files
    if extract_dir.exists():
        csv_files = list(extract_dir.glob("*.csv"))
        if csv_files:
            logger.info("Using cached extracted files in %s", extract_dir)
            return csv_files

    extract_dir.mkdir(exist_ok=True)
    logger.info("Extracting %s to %s", zip_file, extract_dir)

    # Extract all files
    with ZipFile(zip_file, "r") as zip_ref:
        zip_ref.extractall(extract_dir)

    # Return list of CSV files
    csv_files = list(extract_dir.glob("*.csv"))
    logger.info("Extracted %d CSV file(s)", len(csv_files))
    return csv_files


def parse_bike_data(csv_files: list[Path], month_str: str) -> Iterator[dict[str, Any]]:
    """Parse extracted bike trip CSV data with Polars.

    Args:
        csv_files: List of paths to CSV files
        month_str: Month string for metadata

    Yields:
        Dictionary records of bike trips with normalized timestamps
    """
    for csv_file in csv_files:
        logger.info("Parsing bike data from %s", csv_file)

        # Read CSV with Polars
        df = pl.read_csv(
            csv_file,
            try_parse_dates=True,
            ignore_errors=True,
            rechunk=True,
        )

        # Normalize column names to snake_case
        df = df.rename({col: col.lower().replace(" ", "_") for col in df.columns})

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
        logger.info("Extracted %d records from %s", len(records), csv_file.name)

        # Yield records in batches for memory efficiency
        batch_size = 1000000
        for i in range(0, len(records), batch_size):
            batch = records[i : i + batch_size]
            yield from batch


@dlt.resource(
    name="bike_trips",
    write_disposition="merge",
    primary_key="ride_id",
    table_name="bike_trips",
)
def bike_trips(months: list[str], base_url: str | None = None) -> Iterator[dict[str, Any]]:
    """Extract bike trip data from monthly CSV files.

    This function orchestrates a three-step process:
    1. Download zip files to local storage
    2. Extract CSV files from zip archives
    3. Parse CSV files with Polars

    Args:
        months: List of month strings in YYYYMM format (e.g., ["202405", "202406"])
        base_url: Base URL for Citi Bike data (defaults to S3 bucket)

    Yields:
        Dictionary records of bike trips with normalized timestamps
    """
    if base_url is None:
        base_url = "https://s3.amazonaws.com/tripdata"

    for month_str in months:
        logger.info("Processing bike data for %s", month_str)

        try:
            # Step 1: Download to local storage
            zip_file = download_bike_data(month_str, base_url)

            # Step 2: Extract CSV files from zip
            csv_files = unzip_bike_data(zip_file)

            # Step 3: Parse with Polars and yield records
            yield from parse_bike_data(csv_files, month_str)

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
    months_to_load = ["202405", "202406"]
    result = run_bike_pipeline(months_to_load)
    logger.info("Ingestion complete. Result: %s", result)
