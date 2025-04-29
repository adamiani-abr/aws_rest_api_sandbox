import os
from typing import Any

import pytest
from _pytest.monkeypatch import MonkeyPatch
from dotenv import load_dotenv
from flask.testing import FlaskClient
from requests_mock.mocker import Mocker

from src_api_gateway.web_service.app import app

load_dotenv("../../src_api_gateway/web_service/.env")


@pytest.fixture
def client() -> Any:
    """
    create a test client from the web_service flask app
    """
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def force_ecs_auth(monkeypatch: MonkeyPatch) -> None:
    """
    monkeypatch the config client to return True for ECS auth mode
    """
    monkeypatch.setattr(
        "src_api_gateway.web_service.app.aws_app_config_client.get_config_api_gateway_authorizer_ecs_auth_service",
        lambda: True,
    )


@pytest.fixture
def simulate_session_cookie(client: FlaskClient) -> None:
    """
    set a dummy session_id cookie on the test client
    """
    client.set_cookie("session_id", "dummy-session-id")


@pytest.fixture
def mock_valid_session(requests_mock: Mocker) -> None:
    """
    mock the POST /verify endpoint to return a valid session response
    """
    requests_mock.post(
        f"{os.environ['AUTH_SERVICE_URL_REST_API']}/verify",
        json={"user": '{"email": "admin"}'},
        status_code=200,
    )


def test_my_orders_success(
    client: FlaskClient,
    requests_mock: Mocker,
    force_ecs_auth: None,  # pylint: disable=unused-argument
    simulate_session_cookie: None,  # pylint: disable=unused-argument
    mock_valid_session: None,  # pylint: disable=unused-argument
) -> None:
    """
    test /my-orders route when user is authenticated and orders are available
    """
    requests_mock.get(
        f"{os.environ['ORDER_SERVICE_URL_REST_API']}/orders",
        json={"orders": [{"order_id": "abc123"}]},
        status_code=200,
    )

    res = client.get("/my-orders")
    assert res.status_code == 200
    assert b"abc123" in res.data


def test_place_order_success(
    client: FlaskClient,
    requests_mock: Mocker,
    force_ecs_auth: None,  # pylint: disable=unused-argument
    simulate_session_cookie: None,  # pylint: disable=unused-argument
    mock_valid_session: None,  # pylint: disable=unused-argument
) -> None:
    """
    test /place-order with valid form input and auth/session in place
    """
    requests_mock.post(
        f"{os.environ['ORDER_SERVICE_URL_REST_API']}/orders",
        json={"order_id": "test123", "message": "Order created"},
        status_code=201,
    )

    res = client.post(
        "/place-order",
        data={"items": "apple, banana", "total": "10.50"},
        follow_redirects=False,
    )

    assert res.status_code == 201
    assert "/my-orders" in res.headers["Location"]


def test_edit_order_success(
    client: FlaskClient,
    requests_mock: Mocker,
    force_ecs_auth: None,  # pylint: disable=unused-argument
    simulate_session_cookie: None,  # pylint: disable=unused-argument
    mock_valid_session: None,  # pylint: disable=unused-argument
) -> None:
    """
    test /my-orders/<order_id>/edit for a successful order update
    """
    order_id = "abc123"

    requests_mock.get(
        f"{os.environ['ORDER_SERVICE_URL_REST_API']}/orders/{order_id}",
        json={"order_id": order_id, "items": ["notebook"], "total": 5.0, "status": "created"},
        status_code=200,
    )

    requests_mock.put(
        f"{os.environ['ORDER_SERVICE_URL_REST_API']}/orders/{order_id}",
        json={"order_id": order_id, "items": ["notebook", "pen"], "total": 10.0, "status": "shipped"},
        status_code=200,
    )

    res = client.post(
        f"/my-orders/{order_id}/edit",
        data={"items": "notebook, pen", "total": "10.00", "status": "shipped"},
        follow_redirects=False,
    )

    assert res.status_code == 302
    assert f"/my-orders/{order_id}" in res.headers["Location"]
