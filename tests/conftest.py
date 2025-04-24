import pytest
import requests_mock


@pytest.fixture
def mock_api():
    with requests_mock.Mocker() as m:
        yield m
