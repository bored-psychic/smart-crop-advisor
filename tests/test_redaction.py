"""Tests for PII redaction utilities."""

import pytest
from backend.utils.redaction import mask_phone, mask_endpoint, mask_coord


class TestMaskPhone:
    """Test phone number masking."""

    def test_mask_phone_with_country_code(self):
        """Test masking phone number with country code."""
        assert mask_phone("+919876543210") == "+91***3210"

    def test_mask_phone_without_country_code(self):
        """Test masking phone number without country code."""
        assert mask_phone("9876543210") == "987***3210"

    def test_mask_phone_short(self):
        """Test masking very short phone number."""
        assert mask_phone("123") == "***"

    def test_mask_phone_empty(self):
        """Test masking empty string."""
        assert mask_phone("") == "***"

    def test_mask_phone_exact_length(self):
        """Test masking phone number with exactly 5 characters."""
        assert mask_phone("12345") == "***"

    def test_mask_phone_six_chars(self):
        """Test masking phone number with 6 characters."""
        assert mask_phone("123456") == "123***3456"


class TestMaskEndpoint:
    """Test endpoint URL masking."""

    def test_mask_endpoint_https(self):
        """Test masking HTTPS endpoint."""
        assert mask_endpoint("https://push.example.com/abc123/xyz") == "https://push.example.com/***"

    def test_mask_endpoint_http(self):
        """Test masking HTTP endpoint."""
        assert mask_endpoint("http://api.service.com/secret/path") == "http://api.service.com/***"

    def test_mask_endpoint_with_port(self):
        """Test masking endpoint with port number."""
        assert mask_endpoint("https://push.example.com:8443/abc") == "https://push.example.com:8443/***"

    def test_mask_endpoint_with_query(self):
        """Test masking endpoint with query parameters."""
        assert mask_endpoint("https://api.example.com/v1/push?key=value") == "https://api.example.com/***"

    def test_mask_endpoint_simple(self):
        """Test masking simple endpoint."""
        assert mask_endpoint("https://example.com") == "https://example.com/***"


class TestMaskCoord:
    """Test coordinate masking."""

    def test_mask_coord_positive(self):
        """Test masking positive coordinate."""
        assert mask_coord(28.613939) == "28.6"

    def test_mask_coord_negative(self):
        """Test masking negative coordinate."""
        assert mask_coord(-73.935242) == "-73.9"

    def test_mask_coord_zero(self):
        """Test masking zero coordinate."""
        assert mask_coord(0.0) == "0.0"

    def test_mask_coord_rounds_down(self):
        """Test that coordinate rounds down correctly."""
        assert mask_coord(28.64) == "28.6"

    def test_mask_coord_rounds_up(self):
        """Test that coordinate rounds using banker's rounding."""
        # Python uses banker's rounding (round half to even)
        assert mask_coord(28.65) == "28.6"
        assert mask_coord(28.75) == "28.8"

    def test_mask_coord_large_number(self):
        """Test masking large coordinate."""
        assert mask_coord(179.9999) == "180.0"
