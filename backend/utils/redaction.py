"""PII redaction utilities for secure logging."""

from urllib.parse import urlparse


def mask_phone(p: str) -> str:
    """
    Mask phone number for logging.

    Examples:
        +919876543210 → "+91***3210"
        9876543210 → "987***210"
    """
    if len(p) <= 5:
        return "***"
    return p[:3] + "***" + p[-4:]


def mask_endpoint(url: str) -> str:
    """
    Mask endpoint URL for logging.

    Examples:
        https://push.example.com/abc123/xyz → https://push.example.com/***
        http://api.service.com/secret/path → http://api.service.com/***
    """
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}/***"


def mask_coord(c: float) -> str:
    """
    Mask coordinate for logging by rounding to 1 decimal place.

    Examples:
        28.613939 → "28.6"
        -73.935242 → "-73.9"
    """
    return f"{round(c, 1)}"
