"""Tests for bike data ingestion pipeline."""

from unittest.mock import MagicMock, patch

import polars as pl
import pytest

from dlt_pipeline.bike import bike_trips, run_bike_pipeline


@pytest.fixture
def sample_bike_data():
    """Create sample bike trip data for testing."""
    return pl.DataFrame(
        {
            "ride_id": ["ABC123", "DEF456", "GHI789"],
            "started_at": [
                "2024-05-01 10:30:00",
                "2024-05-01 11:15:00",
                "2024-05-01 14:20:00",
            ],
            "ended_at": [
                "2024-05-01 10:45:00",
                "2024-05-01 11:30:00",
                "2024-05-01 14:50:00",
            ],
            "start_station_id": ["123", "456", "789"],
            "end_station_id": ["456", "789", "123"],
            "member_casual": ["member", "casual", "member"],
        }
    )


@pytest.fixture
def sample_bike_csv(sample_bike_data):
    """Create CSV content from sample data."""
    return sample_bike_data.write_csv()


def test_bike_trips_column_normalization():
    """Test that column names are normalized to snake_case."""
    with patch("polars.read_csv") as mock_read:
        # Create data with mixed-case column names
        df = pl.DataFrame(
            {
                "Ride ID": ["ABC123"],
                "Started At": ["2024-05-01 10:30:00"],
                "Ended At": ["2024-05-01 10:45:00"],
                "Member Casual": ["member"],
            }
        )
        mock_read.return_value = df

        # Run the resource
        resource_gen = bike_trips(["2024-05"], base_url="http://test.com")
        results = list(resource_gen)

        # Verify columns are normalized
        assert len(results) > 0
        first_record = results[0]
        assert "ride_id" in first_record
        assert "started_at" in first_record
        assert "ended_at" in first_record


def test_bike_trips_datetime_parsing():
    """Test that datetime columns are properly parsed."""
    with patch("polars.read_csv") as mock_read:
        df = pl.DataFrame(
            {
                "ride_id": ["ABC123"],
                "started_at": ["2024-05-01 10:30:00"],
                "ended_at": ["2024-05-01 10:45:00"],
            }
        )
        mock_read.return_value = df

        resource_gen = bike_trips(["2024-05"], base_url="http://test.com")
        results = list(resource_gen)

        assert len(results) > 0
        # The datetime should be parsed and present in the result
        assert "started_at" in results[0]
        assert "ended_at" in results[0]


def test_bike_trips_ride_duration_calculation():
    """Test that ride duration is calculated correctly."""
    with patch("polars.read_csv") as mock_read:
        df = pl.DataFrame(
            {
                "ride_id": ["ABC123"],
                "started_at": ["2024-05-01 10:00:00.000"],
                "ended_at": ["2024-05-01 10:30:00.000"],
            }
        )
        mock_read.return_value = df

        resource_gen = bike_trips(["2024-05"], base_url="http://test.com")
        results = list(resource_gen)

        assert len(results) > 0
        # Should have ride_mins calculated
        assert "ride_mins" in results[0]


def test_bike_trips_metadata_fields():
    """Test that ingestion metadata is added."""
    with patch("polars.read_csv") as mock_read:
        df = pl.DataFrame(
            {
                "ride_id": ["ABC123"],
                "started_at": ["2024-05-01 10:30:00"],
                "ended_at": ["2024-05-01 10:45:00"],
            }
        )
        mock_read.return_value = df

        resource_gen = bike_trips(["2024-05"], base_url="http://test.com")
        results = list(resource_gen)

        assert len(results) > 0
        # Check metadata fields
        assert "_dlt_load_timestamp" in results[0]
        assert "source_month" in results[0]
        assert results[0]["source_month"] == "2024-05"


def test_bike_trips_multiple_months():
    """Test processing multiple months of data."""
    with patch("polars.read_csv") as mock_read:
        df = pl.DataFrame(
            {
                "ride_id": ["ABC123"],
                "started_at": ["2024-05-01 10:30:00"],
                "ended_at": ["2024-05-01 10:45:00"],
            }
        )
        mock_read.return_value = df

        months = ["2024-05", "2024-06"]
        resource_gen = bike_trips(months, base_url="http://test.com")
        results = list(resource_gen)

        # Should have data from both months
        # Each month should have at least one record
        assert len(results) >= 2


def test_bike_trips_error_handling():
    """Test that errors during download are handled gracefully."""
    with patch("polars.read_csv") as mock_read:
        mock_read.side_effect = Exception("Download failed")

        # Should not raise, but handle the error
        resource_gen = bike_trips(["2024-05"], base_url="http://test.com")
        results = list(resource_gen)

        # No results should be returned for failed download
        assert len(results) == 0


def test_run_bike_pipeline_basic():
    """Test the main pipeline execution function."""
    with (
        patch("dlt_pipeline.bike.bike_trips") as mock_resource,
        patch("dlt.pipeline") as mock_pipeline_factory,
    ):
        # Mock the resource to return empty data
        mock_resource.return_value = iter([])

        # Mock the pipeline
        mock_pipeline = MagicMock()
        mock_load_info = MagicMock()
        mock_load_info.loads_ids = ["load_123"]
        mock_pipeline.run.return_value = mock_load_info
        mock_pipeline_factory.return_value = mock_pipeline

        # Run the pipeline
        result = run_bike_pipeline(["2024-05"])

        # Verify pipeline was created with correct params
        mock_pipeline_factory.assert_called_once_with(
            pipeline_name="bike_ingestion",
            destination="duckdb",
            dataset_name="raw_bike",
        )

        # Verify pipeline was run
        assert mock_pipeline.run.called
        assert result == mock_load_info
