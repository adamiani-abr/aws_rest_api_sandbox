import pytest
from unittest.mock import patch
from src_api_gateway.dummy_service.app import app


@pytest.fixture
def client():
    with app.test_client() as client:
        yield client


def test_index(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json == {"message": "Hello world!"}


def test_dummy_route(client):
    response = client.get("/dummy1")
    assert response.status_code == 200
    assert response.json == {"message": "dummy route 1!"}


def test_new_dummy_route(client):
    with patch("src_api_gateway.dummy_service.app.new_dummy_function") as mock_new_dummy:
        mock_new_dummy.return_value = {"status": "success", "data": "new dummy data"}
        response = client.get("/new_dummy")
        assert response.status_code == 200
        assert response.json == {"status": "success", "data": "new dummy data"}
