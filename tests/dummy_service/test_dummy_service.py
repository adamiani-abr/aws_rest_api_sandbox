import pytest
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
