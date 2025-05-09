from typing import Any

import pytest
import requests_mock


@pytest.fixture
def mock_api() -> Any:
    """mock_api fixture to mock external API calls."""
    with requests_mock.Mocker() as m:
        yield m
