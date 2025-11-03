"""Tests for weather data ingestion pipeline."""

from unittest.mock import MagicMock, patch

import pytest

from dlt_pipeline.weather import daily_weather, run_weather_pipeline


@pytest.fixture
def sample_weather_response():
    """Create sample weather API response."""
    return {
        "daily": {
            "time": ["2024-05-01", "2024-05-02", "2024-05-03"],
            "temperature_2m_max": [22.5, 24.0, 21.3],
            "temperature_2m_min": [15.2, 16.8, 14.5],
            "precipitation_sum": [0.0, 2.5, 0.0],
            "wind_speed_10m_max": [12.3, 15.7, 10.2],
        }
    }


def test_daily_weather_basic_parsing(sample_weather_response):
    """Test that weather data is correctly parsed from API response."""
    with patch("requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.json.return_value = sample_weather_response
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        # Run the resource
        resource_gen = daily_weather(
            lat=40.73, lon=-73.94, start_date="2024-05-01", end_date="2024-05-03"
        )
        results = list(resource_gen)

        # Verify we got all records
        assert len(results) == 3

        # Verify first record structure
        first_record = results[0]
        assert first_record["date"] == "2024-05-01"
        assert first_record["tmax"] == 22.5
        assert first_record["tmin"] == 15.2
        assert first_record["precip"] == 0.0
        assert first_record["wind_max"] == 12.3


def test_daily_weather_metadata_fields(sample_weather_response):
    """Test that metadata fields are added to weather records."""
    with patch("requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.json.return_value = sample_weather_response
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        resource_gen = daily_weather(
            lat=40.73, lon=-73.94, start_date="2024-05-01", end_date="2024-05-03"
        )
        results = list(resource_gen)

        assert len(results) > 0
        # Check metadata fields
        assert "_dlt_load_timestamp" in results[0]
        assert "source_location" in results[0]
        assert results[0]["source_location"] == "40.73,-73.94"


def test_daily_weather_handles_missing_data():
    """Test handling of missing data fields in API response."""
    # Remove some fields to simulate missing data
    incomplete_response = {
        "daily": {
            "time": ["2024-05-01"],
            "temperature_2m_max": [22.5],
            # Other fields missing
        }
    }

    with patch("requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.json.return_value = incomplete_response
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        resource_gen = daily_weather(
            lat=40.73, lon=-73.94, start_date="2024-05-01", end_date="2024-05-01"
        )
        results = list(resource_gen)

        assert len(results) == 1
        # Should have None for missing fields
        assert results[0]["tmin"] is None
        assert results[0]["precip"] is None


def test_daily_weather_no_daily_data():
    """Test handling when API returns no daily data."""
    with patch("requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.json.return_value = {"error": "No data"}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        resource_gen = daily_weather(
            lat=40.73, lon=-73.94, start_date="2024-05-01", end_date="2024-05-03"
        )
        results = list(resource_gen)

        # Should return empty list
        assert len(results) == 0


def test_daily_weather_api_error():
    """Test that API errors are properly raised."""
    with patch("requests.get") as mock_get:
        mock_get.side_effect = Exception("API request failed")

        resource_gen = daily_weather(
            lat=40.73, lon=-73.94, start_date="2024-05-01", end_date="2024-05-03"
        )

        # Should raise the exception
        with pytest.raises(Exception, match="API request failed"):
            list(resource_gen)


def test_daily_weather_url_construction():
    """Test that API URL is correctly constructed."""
    with patch("requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.json.return_value = {"daily": {"time": []}}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        lat, lon = 40.73, -73.94
        start, end = "2024-05-01", "2024-05-31"

        resource_gen = daily_weather(lat=lat, lon=lon, start_date=start, end_date=end)
        list(resource_gen)

        # Verify the API was called with correct parameters
        assert mock_get.called
        call_url = mock_get.call_args[0][0]
        assert f"latitude={lat}" in call_url
        assert f"longitude={lon}" in call_url
        assert f"start_date={start}" in call_url
        assert f"end_date={end}" in call_url
        assert "temperature_2m_max" in call_url
        assert "precipitation_sum" in call_url


def test_run_weather_pipeline_basic():
    """Test the main weather pipeline execution function."""
    with (
        patch("dlt_pipeline.weather.daily_weather") as mock_resource,
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
        result = run_weather_pipeline(
            lat=40.73, lon=-73.94, start_date="2024-05-01", end_date="2024-05-31"
        )

        # Verify pipeline was created with correct params
        mock_pipeline_factory.assert_called_once_with(
            pipeline_name="weather_ingestion",
            destination="duckdb",
            dataset_name="raw_weather",
        )

        # Verify pipeline was run
        assert mock_pipeline.run.called
        assert result == mock_load_info
