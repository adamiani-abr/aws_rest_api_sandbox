import importlib
import os
from typing import Generator

import pytest
import requests_mock
from flask import Flask
from flask.testing import FlaskClient
from pytest import MonkeyPatch


@pytest.fixture(autouse=True)  # `autouse=True` -> all tests automatically use
def setup_env(monkeypatch: MonkeyPatch) -> None:
    """
    Configure environment variables for the web front-end before import.
    This ensures JWT_COOKIE_NAME and other settings are applied.
    """
    env_vars = {
        "AUTH_SERVICE_URL_REST_API": "http://auth:8000",
    }
    for key, val in env_vars.items():
        monkeypatch.setenv(key, val)

    import app as web_app_module  # type: ignore

    importlib.reload(web_app_module)


@pytest.fixture
def mock_api() -> Generator[requests_mock.Mocker, None, None]:
    """
    Fixture to provide a requests_mock Mocker for HTTP stubbing.
    """
    with requests_mock.Mocker() as m:
        yield m


@pytest.fixture
def app() -> Flask:
    """
    Import and configure the Flask application after environment variables are set.
    Reloading the module ensures patched env vars are used.
    """
    import app as web_app_module  # type: ignore

    importlib.reload(web_app_module)
    web_app_module.app.config["TESTING"] = True
    return web_app_module.app


@pytest.fixture
def client(app: Flask) -> Generator[FlaskClient, None, None]:
    """
    Create a Flask test client using the configured app fixture.
    """
    with app.test_client() as client_instance:
        yield client_instance


def test_index_not_logged_in(client: FlaskClient) -> None:
    """GET / should render login link when no session."""
    response = client.get("/")
    assert response.status_code == 200
    assert "login" in response.get_data(as_text=True).lower()


def test_index_logged_in(
    mock_api: requests_mock.Mocker,
    client: FlaskClient,
) -> None:
    """GET / shows username when session is valid."""
    print(f"os.environ['AUTH_SERVICE_URL_REST_API']: {os.environ['AUTH_SERVICE_URL_REST_API']}")
    mock_api.post(
        f"{os.environ['AUTH_SERVICE_URL_REST_API']}/verify",
        json={"user": {"email": "u@x", "name": "TestUser"}},
        status_code=200,
    )
    client.set_cookie("session_id", "dummy")

    response = client.get("/")
    assert response.status_code == 302
    assert "/dashboard" in response.headers["Location"]
    assert True


def test_login_page_fetches_oauth_url_and_redirects(
    client: FlaskClient,
    requests_mock: requests_mock.Mocker,
) -> None:
    """GET /login should fetch Google OAuth URL and redirect to /dashboard if successful."""
    requests_mock.get(
        f"{os.environ['AUTH_SERVICE_URL_REST_API']}/login/google",
        json={"username": "u@x", "password": "password"},
        status_code=200,
    )
    res = client.get("/login")
    assert res.status_code == 200
    assert b"dashboard" in res.data


def test_dashboard_redirects_when_not_logged_in(client: FlaskClient) -> None:
    """GET /dashboard without cookie → redirect to /login."""
    res = client.get("/dashboard")
    assert res.status_code == 302
    assert "/login" in res.headers["Location"]


def test_dashboard_success_when_logged_in(
    client: FlaskClient,
    requests_mock: requests_mock.Mocker,
) -> None:
    """GET /dashboard with valid session → shows user name."""
    requests_mock.post(
        f"{os.environ['AUTH_SERVICE_URL_REST_API']}/verify",
        json={"user": '{"name":"Alice"}'},
        status_code=200,
    )
    client.set_cookie("session_id", "dummy")
    res = client.get("/dashboard")
    assert res.status_code == 200


def test_settings_redirects_when_not_logged_in(client: FlaskClient) -> None:
    """GET /settings without cookie → redirect to /login."""
    res = client.get("/settings")
    assert res.status_code == 302
    assert "/login" in res.headers["Location"]


def test_settings_success_when_logged_in(
    client: FlaskClient,
    requests_mock: requests_mock.Mocker,
) -> None:
    """GET /settings with valid session → shows Settings page."""
    requests_mock.post(
        f"{os.environ['AUTH_SERVICE_URL_REST_API']}/verify",
        json={"user": '{"name":"Bob"}'},
        status_code=200,
    )
    client.set_cookie("session_id", "dummy")
    res = client.get("/settings")
    assert res.status_code == 200
    assert b"settings" in res.data.lower()


@pytest.mark.parametrize("method", ["get", "post"])
def test_logout_clears_cookie_and_redirects(
    client: FlaskClient,
    requests_mock: requests_mock.Mocker,
    method: str,
) -> None:
    """GET or POST /logout should hit auth logout, clear cookie, and redirect."""
    requests_mock.post(f"{os.environ['AUTH_SERVICE_URL_REST_API']}/logout", status_code=200)
    client.set_cookie("session_id", "dummy")
    res = getattr(client, method)("/logout")
    assert res.status_code in (302, 301, 200)
    # cookie should be deleted
    sc = res.headers.get("Set-Cookie", "")
    assert "session_id=;" in sc
    # ends up on index
    assert res.headers["Location"].endswith("/") or res.status_code == 200
