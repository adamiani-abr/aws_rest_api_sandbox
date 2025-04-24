import pytest
from unittest.mock import patch
from src_api_gateway.web_service.app import app


@pytest.fixture
def client():
    with app.test_client() as client:
        yield client


def test_home_page(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Welcome" in response.data.decode()


def test_login_page(client):
    response = client.get("/login")
    assert response.status_code == 200
    assert "Login" in response.data.decode()


def test_auth_service_interaction(client):
    with patch("src_api_gateway.web_service.app.auth_service_call") as mock_auth_service:
        mock_auth_service.return_value = {"status": "success", "user_id": 123}
        response = client.get("/auth")
        assert response.status_code == 200
        assert "user_id" in response.json
        assert response.json["user_id"] == 123


def test_order_service_interaction(client):
    with patch("src_api_gateway.web_service.app.order_service_call") as mock_order_service:
        mock_order_service.return_value = {"status": "success", "order_id": 456}
        response = client.get("/order")
        assert response.status_code == 200
        assert "order_id" in response.json
        assert response.json["order_id"] == 456


def test_dummy_service_interaction(client):
    with patch("src_api_gateway.web_service.app.dummy_service_call") as mock_dummy_service:
        mock_dummy_service.return_value = {"status": "success", "data": "dummy data"}
        response = client.get("/dummy")
        assert response.status_code == 200
        assert "data" in response.json
        assert response.json["data"] == "dummy data"
