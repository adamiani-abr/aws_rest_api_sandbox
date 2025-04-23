import pytest
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
