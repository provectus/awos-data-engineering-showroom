"""Unit tests for the holiday data ingestion pipeline."""

import time
from datetime import datetime
from unittest.mock import Mock, patch

import pytest
import requests

from dlt_pipeline.holidays import _merge_holidays, us_holidays


class TestHolidayPipeline:
    """Test suite for holiday data pipeline."""

    @pytest.fixture
    def sample_holiday_data(self):
        """Sample holiday data from Nager.Date API."""
        return [
            {
                "date": "2024-01-01",
                "name": "New Year's Day",
                "localName": "New Year's Day",
                "countryCode": "US",
                "fixed": False,
                "global": True,
                "types": ["Public"],
                "counties": None,
                "launchYear": None,
            },
            {
                "date": "2024-07-04",
                "name": "Independence Day",
                "localName": "Independence Day",
                "countryCode": "US",
                "fixed": False,
                "global": True,
                "types": ["Public"],
                "counties": None,
                "launchYear": None,
            },
        ]

    @pytest.fixture
    def duplicate_date_holidays(self):
        """Sample data with duplicate dates (same date, different holidays)."""
        return [
            {
                "date": "2024-10-14",
                "name": "Columbus Day",
                "localName": "Columbus Day",
                "countryCode": "US",
                "fixed": False,
                "global": False,
                "types": ["Public"],
                "counties": ["US-NY", "US-CA"],
                "launchYear": None,
            },
            {
                "date": "2024-10-14",
                "name": "Indigenous Peoples' Day",
                "localName": "Indigenous Peoples' Day",
                "countryCode": "US",
                "fixed": False,
                "global": False,
                "types": ["Public"],
                "counties": ["US-AK", "US-OR"],
                "launchYear": None,
            },
        ]

    def test_single_year_ingestion(self, sample_holiday_data):
        """Test successful ingestion for a single year."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_holiday_data

        with patch("requests.get", return_value=mock_response):
            results = list(us_holidays([2024]))

            # Should yield 2 holidays
            assert len(results) == 2

            # Verify first holiday
            assert results[0]["date"] == "2024-01-01"
            assert results[0]["holiday_name"] == "New Year's Day"
            assert results[0]["country_code"] == "US"
            assert results[0]["holiday_types"] == "Public"
            assert results[0]["source_year"] == 2024

            # Verify metadata fields
            assert "_dlt_load_timestamp" in results[0]
            assert isinstance(results[0]["_dlt_load_timestamp"], datetime)

    def test_multi_year_ingestion(self, sample_holiday_data):
        """Test ingestion for multiple years."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_holiday_data

        with patch("requests.get", return_value=mock_response):
            results = list(us_holidays([2024, 2025]))

            # Should yield 2 holidays per year = 4 total
            assert len(results) == 4

            # Verify source_year metadata
            years = [r["source_year"] for r in results]
            assert years.count(2024) == 2
            assert years.count(2025) == 2

    def test_retry_logic_success_on_second_attempt(self, sample_holiday_data):
        """Test that retry succeeds on the second attempt."""
        call_count = 0

        def mock_get(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First call fails
                raise requests.exceptions.Timeout("Connection timeout")
            else:
                # Second call succeeds
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = sample_holiday_data
                return mock_response

        with patch("requests.get", side_effect=mock_get):
            start_time = time.time()
            results = list(us_holidays([2024]))
            elapsed = time.time() - start_time

            # Should succeed after retry
            assert len(results) == 2
            assert call_count == 2

            # Should have waited ~1 second for first retry
            assert elapsed >= 1.0

    def test_retry_logic_fails_after_max_attempts(self):
        """Test that pipeline fails after all retries are exhausted."""
        call_count = 0

        def mock_get(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            raise requests.exceptions.ConnectionError(
                f"Connection failed (attempt {call_count})"
            )

        with patch("requests.get", side_effect=mock_get):
            # dlt wraps the exception in ResourceExtractionError
            with pytest.raises(Exception):  # Catch any exception type
                start_time = time.time()
                list(us_holidays([2024]))
                elapsed = time.time() - start_time

            # Verify retries happened outside the context manager
            assert call_count == 3

    def test_field_transformation_arrays_to_strings(self):
        """Test that array fields are converted to comma-separated strings."""
        holiday_with_arrays = {
            "date": "2024-10-14",
            "name": "Columbus Day",
            "localName": "Columbus Day",
            "countryCode": "US",
            "fixed": False,
            "global": False,
            "types": ["Public", "Federal"],
            "counties": ["US-NY", "US-CA", "US-TX"],
            "launchYear": None,
        }

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [holiday_with_arrays]

        with patch("requests.get", return_value=mock_response):
            results = list(us_holidays([2024]))

            assert len(results) == 1
            # Verify arrays converted to comma-separated strings
            assert results[0]["holiday_types"] == "Public,Federal"
            # Counties preserve original order for single holidays (sorted only when merged)
            assert results[0]["counties"] == "US-NY,US-CA,US-TX"

    def test_metadata_fields_added(self, sample_holiday_data):
        """Test that metadata fields are added to all records."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_holiday_data

        with patch("requests.get", return_value=mock_response):
            results = list(us_holidays([2024]))

            for result in results:
                # Verify _dlt_load_timestamp
                assert "_dlt_load_timestamp" in result
                assert isinstance(result["_dlt_load_timestamp"], datetime)

                # Verify source_year
                assert "source_year" in result
                assert result["source_year"] == 2024

    def test_merge_holidays_single_holiday(self):
        """Test _merge_holidays with a single holiday (no merge needed)."""
        holidays = [
            {
                "date": "2024-01-01",
                "name": "New Year's Day",
                "localName": "New Year's Day",
                "countryCode": "US",
                "fixed": False,
                "global": True,
                "types": ["Public"],
                "counties": None,
                "launchYear": None,
            }
        ]

        merged = _merge_holidays(holidays)

        assert merged["date"] == "2024-01-01"
        assert merged["holiday_name"] == "New Year's Day"
        assert merged["holiday_types"] == "Public"
        assert merged["counties"] is None

    def test_merge_holidays_multiple_same_date(self, duplicate_date_holidays):
        """Test _merge_holidays with multiple holidays on same date."""
        merged = _merge_holidays(duplicate_date_holidays)

        # Names should be concatenated
        assert merged["holiday_name"] == "Columbus Day and Indigenous Peoples' Day"

        # Counties should be merged and sorted
        assert merged["counties"] == "US-AK,US-CA,US-NY,US-OR"

        # Types should be deduplicated (both are Public)
        assert merged["holiday_types"] == "Public"

        # is_global should be True if ANY holiday is global (both False here)
        assert merged["is_global"] is False

    def test_merge_holidays_type_prioritization(self):
        """Test that Public types are prioritized over others."""
        holidays = [
            {
                "date": "2024-03-29",
                "name": "Good Friday",
                "localName": "Good Friday",
                "countryCode": "US",
                "fixed": False,
                "global": False,
                "types": ["Optional"],
                "counties": ["US-TX"],
                "launchYear": None,
            },
            {
                "date": "2024-03-29",
                "name": "Good Friday",
                "localName": "Good Friday",
                "countryCode": "US",
                "fixed": False,
                "global": False,
                "types": ["Public"],
                "counties": ["US-NY"],
                "launchYear": None,
            },
        ]

        merged = _merge_holidays(holidays)

        # Public should come before Optional
        assert merged["holiday_types"] == "Public,Optional"
        assert merged["counties"] == "US-NY,US-TX"

    def test_empty_api_response(self):
        """Test handling of empty API response."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = []

        with patch("requests.get", return_value=mock_response):
            results = list(us_holidays([2024]))

            # Should yield no results but not crash
            assert len(results) == 0

    def test_null_counties_handling(self):
        """Test that null/None counties are handled correctly."""
        holiday = {
            "date": "2024-01-01",
            "name": "New Year's Day",
            "localName": "New Year's Day",
            "countryCode": "US",
            "fixed": False,
            "global": True,
            "types": ["Public"],
            "counties": None,  # Nationwide holiday
            "launchYear": None,
        }

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [holiday]

        with patch("requests.get", return_value=mock_response):
            results = list(us_holidays([2024]))

            assert len(results) == 1
            # counties should be None for nationwide holidays
            assert results[0]["counties"] is None
