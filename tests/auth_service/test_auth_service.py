import pytest
from unittest.mock import patch
from src_api_gateway.auth_service.app import app


@pytest.fixture
def client():
    with app.test_client() as client:
        yield client


def test_login(client):
    response = client.post("/login", json={"username": "test", "password": "test"})
    assert response.status_code == 200
    assert "token" in response.json


def test_protected_route(client, mocker):
    mocker.patch("src_api_gateway.auth_service.app.verify_token", return_value=True)
    response = client.get("/protected", headers={"Authorization": "Bearer testtoken"})
    assert response.status_code == 200
    assert response.json == {"message": "Access granted"}


def test_token_storage(client):
    with patch("src_api_gateway.auth_service.app.store_token") as mock_store_token:
        mock_store_token.return_value = True
        response = client.post("/store_token", json={"token": "testtoken"})
        assert response.status_code == 200
        assert response.json == {"message": "Token stored successfully"}
