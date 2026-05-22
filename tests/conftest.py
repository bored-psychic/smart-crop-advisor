"""Shared pytest fixtures.

The ``auth_headers`` fixture mints a JWT for a synthetic phone via
``backend.auth.issue_token`` so router tests can authenticate against
the JWT-gated endpoints introduced in P0 Task 3 and P1 Task 9.
"""
from __future__ import annotations

import pytest

from backend.auth import issue_token


@pytest.fixture(scope="session")
def test_phone() -> str:
    """E.164 phone used by the JWT fixture. Synthetic — not a real number."""
    return "+919999999999"


@pytest.fixture(scope="session")
def auth_token(test_phone: str) -> str:
    """A valid JWT signed with the test settings' secret."""
    token, _ = issue_token(test_phone)
    return token


@pytest.fixture(scope="session")
def auth_headers(auth_token: str) -> dict[str, str]:
    """Authorization header ready to splat into a TestClient call."""
    return {"Authorization": f"Bearer {auth_token}"}
