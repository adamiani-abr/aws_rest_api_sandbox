import pytest
from flask.testing import FlaskClient
from _pytest.monkeypatch import MonkeyPatch
from requests_mock.mocker import Mocker
from src_api_gateway.web_service.app import app
from dotenv import load_dotenv
import os
from typing import Any

load_dotenv("../../src_api_gateway/web_service/.env")


@pytest.fixture
def client() -> Any:
    """
    create a test client from the web_service flask app
    """
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_my_orders_success(client: FlaskClient, requests_mock: Mocker) -> None:
    """
    test /my-orders route when user is authenticated and orders are available
    """
    # * mock auth verify
    requests_mock.post(
        f"{os.environ['AUTH_SERVICE_URL_REST_API']}/verify",
        json={"user": '{"email":"admin"}'},
        status_code=200,
    )

    # * mock order service response
    requests_mock.get(
        f"{os.environ['ORDER_SERVICE_URL_REST_API']}/orders",
        json={"orders": [{"order_id": "abc123"}]},
        status_code=200,
    )

    # * simulate logged-in user
    client.set_cookie("session_id", "dummy-session-id")

    # * hit the route
    res = client.get("/my-orders")

    # * assert order is shown
    assert res.status_code == 200
    assert b"abc123" in res.data


def test_place_order_success(client: FlaskClient, requests_mock: Mocker, monkeypatch: MonkeyPatch) -> None:
    """
    test /place-order with valid form input and auth/session in place
    """
    # * force ecs auth mode
    monkeypatch.setattr(
        "src_api_gateway.web_service.app.aws_app_config_client.get_config_api_gateway_authorizer_ecs_auth_service",
        lambda: True,
    )

    # * mock session verification
    requests_mock.post(
        f"{os.environ['AUTH_SERVICE_URL_REST_API']}/verify",
        json={"user": '{"email": "admin"}'},
        status_code=200,
    )

    # * mock order creation
    requests_mock.post(
        f"{os.environ['ORDER_SERVICE_URL_REST_API']}/orders",
        json={"order_id": "test123", "message": "Order created"},
        status_code=201,
    )

    # * simulate session cookie
    client.set_cookie("session_id", "dummy-session-id")

    # * submit order form
    res = client.post("/place-order", data={"items": "apple, banana", "total": "10.50"}, follow_redirects=False)

    # * should redirect to my-orders
    assert res.status_code == 302
    assert "/my-orders" in res.headers["Location"]


def test_edit_order_success(client: FlaskClient, requests_mock: Mocker, monkeypatch: MonkeyPatch) -> None:
    """
    test /my-orders/<order_id>/edit for a successful order update
    """
    # * force ecs auth mode
    monkeypatch.setattr(
        "src_api_gateway.web_service.app.aws_app_config_client.get_config_api_gateway_authorizer_ecs_auth_service",
        lambda: True,
    )

    # * mock session verification
    requests_mock.post(
        f"{os.environ['AUTH_SERVICE_URL_REST_API']}/verify",
        json={"user": '{"email": "admin"}'},
        status_code=200,
    )

    # * set order id
    order_id = "abc123"

    # * mock order fetch
    requests_mock.get(
        f"{os.environ['ORDER_SERVICE_URL_REST_API']}/orders/{order_id}",
        json={"order_id": order_id, "items": ["notebook"], "total": 5.0, "status": "created"},
        status_code=200,
    )

    # * mock order update
    requests_mock.put(
        f"{os.environ['ORDER_SERVICE_URL_REST_API']}/orders/{order_id}",
        json={"order_id": order_id, "items": ["notebook", "pen"], "total": 10.0, "status": "shipped"},
        status_code=200,
    )

    # * simulate session cookie
    client.set_cookie("session_id", "dummy-session-id")

    # * submit edit form
    res = client.post(
        f"/my-orders/{order_id}/edit",
        data={"items": "notebook, pen", "total": "10.00", "status": "shipped"},
        follow_redirects=False,
    )

    # * should redirect to detail page
    assert res.status_code == 302
    assert f"/my-orders/{order_id}" in res.headers["Location"]
