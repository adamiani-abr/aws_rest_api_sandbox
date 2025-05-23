import os
from functools import wraps
from typing import Any, Callable

import requests
from flask import Flask, Response, make_response, redirect, request, url_for

# * initialize flask app
app = Flask(__name__)

# * configuration variables
AUTH_SERVICE_URL = os.environ["AUTH_SERVICE_URL"]
app.config["SECRET_KEY"] = os.environ["SECRET_KEY"]


def login_required(f: Callable) -> Callable:
    """Decorator to enforce authentication via session ID checked against auth service."""

    @wraps(f)
    def decorated_function(*args: Any, **kwargs: Any) -> Any:
        """decorated function to check session ID."""
        session_id = request.cookies.get("session_id")
        if not session_id:
            return redirect(url_for("login"))

        response = requests.post(f"{AUTH_SERVICE_URL}/verify", json={"session_id": session_id}, timeout=3)
        print(f"decorator - response.status_code: {response.status_code}")

        if response.status_code != 200:
            return redirect(url_for("login"))

        return f(*args, **kwargs)

    return decorated_function


@app.route("/")
def index() -> str:
    """Root page: shows login status based on session validation."""
    session_id = request.cookies.get("session_id")

    if session_id:
        response = requests.post(f"{AUTH_SERVICE_URL}/verify", json={"session_id": session_id}, timeout=3)
        if response.status_code == 200:
            user = response.json().get("user")
            return f"Hello, {user}! You are logged in. <a href='/dashboard'>Go to Dashboard</a> | <a href='/logout'>Logout</a>"

    return "Hello, Guest! <a href='/login'>Login here</a>"


@app.route("/login", methods=["GET", "POST"])
def login() -> Response:
    """Login form handler. Validates credentials and sets session cookie."""
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        response = requests.post(
            f"{AUTH_SERVICE_URL}/login",
            json={"username": username, "password": password},
            timeout=3,
        )
        print(f"response.status_code: {response.status_code}")
        print(f"json_response: {response.json()}")

        if response.status_code == 200:
            session_id = response.json().get("session_id")
            resp = make_response(redirect(f"{request.script_root}{url_for('dashboard')}"))
            resp.set_cookie(
                "session_id",
                session_id,
                httponly=True,
                secure=False,
                domain=os.environ["AWS_ALB_DNS_NAME"],
                path="/",
            )
            return resp

        return Response(
            "Invalid credentials, try again.",
            mimetype="text/html",
        )

    return Response(
        """
        <form method="post">
            Username: <input type="text" name="username"><br>
            Password: <input type="password" name="password"><br>
            <input type="submit" value="Login">
        </form>
        """,
        mimetype="text/html",
    )


@app.route("/dashboard")
@login_required
def dashboard() -> str:
    """Protected dashboard page."""
    return (
        "Welcome to your Dashboard! <a href='/profile'>Go to Profile</a> | <a href='/settings'>Settings</a>"
        + "| <a href='/logout'>Logout</a>"
    )


@app.route("/profile")
@login_required
def profile() -> str:
    """Protected user profile page."""
    return "This is your profile page. <a href='/dashboard'>Back to Dashboard</a>"


@app.route("/settings")
@login_required
def settings() -> str:
    """Protected settings page."""
    return "Settings page. Customize your preferences here. <a href='/dashboard'>Back to Dashboard</a>"


@app.route("/logout")
def logout() -> Response:
    """Logout endpoint that clears the session and redirects to home."""
    session_id = request.cookies.get("session_id")
    if session_id:
        requests.post(f"{AUTH_SERVICE_URL}/logout", json={"session_id": session_id}, timeout=3)

    resp = make_response(redirect(url_for("index")))
    resp.delete_cookie("session_id")
    return resp


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT_FLASK", "5001")))
