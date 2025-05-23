import os
from datetime import date
from functools import wraps
from typing import Any, Callable

import requests
from aws_app_config import aws_app_config_client_sandbox_alex
from dotenv import load_dotenv
from flask import Flask, Response, make_response, redirect, render_template, request, session, url_for
from flask_dance.contrib.google import google, make_google_blueprint
from werkzeug.wrappers import Response as WerkzeugResponse

load_dotenv()

app = Flask(__name__)

# * AWS AppConfigClient instance - for feature flags
aws_app_config_client = aws_app_config_client_sandbox_alex.AWSAppConfigClientSandboxAlex()

# * Google OAuth blueprint
google_bp = make_google_blueprint(
    client_id=os.environ["GOOGLE_OAUTH_CLIENT_ID"],
    client_secret=os.environ["GOOGLE_OAUTH_CLIENT_SECRET"],
    scope=[
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/userinfo.profile",
        "openid",
    ],
    redirect_to="google_logged_in",
)
app.register_blueprint(google_bp, url_prefix="/login")

# * Configuration variables
AUTH_SERVICE_URL = os.environ["AUTH_SERVICE_URL_REST_API"]
AWS_REST_API_URL = os.environ["ORDER_SERVICE_URL_REST_API"]
app.config["SECRET_KEY"] = os.environ["SECRET_KEY"]
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"


def login_required(f: Callable) -> Callable:
    """Decorator to enforce login by validating the session ID with the auth service."""

    @wraps(f)
    def decorated_function(*args: Any, **kwargs: Any) -> Any:
        """decorated function to check session ID."""
        session_id = request.cookies.get("session_id", "")
        if not session_id:
            return redirect(url_for("login"))
        try:
            response = requests.post(f"{AUTH_SERVICE_URL}/verify", json={"session_id": session_id}, timeout=3)
            if response.status_code != 200:
                return redirect(url_for("login"))
        except requests.exceptions.Timeout:
            return "Server timeout. Please try again.", 504
        return f(*args, **kwargs)

    return decorated_function


def check_already_logged_in(f: Callable) -> Callable:
    """Decorator: if JWT present and valid, redirect to dashboard."""

    @wraps(f)
    def wrapper(*args: Any, **kwargs: Any) -> WerkzeugResponse | tuple[str, int]:
        """Check if user is already logged in and redirect to dashboard if so."""
        session_id = request.cookies.get("session_id", "")
        if session_id:
            try:
                response = requests.post(f"{AUTH_SERVICE_URL}/verify", json={"session_id": session_id}, timeout=3)
                if response.status_code == 200:
                    return redirect(url_for("dashboard"))
            except requests.exceptions.Timeout:
                return "Server timeout. Please try again.", 504
            except requests.RequestException:
                pass
        return f(*args, **kwargs)

    return wrapper


def __set_and_get_auth_headers() -> dict[str, str]:
    """Return headers needed for order service requests based on session type."""
    session_id = request.cookies.get("session_id", "")
    if aws_app_config_client.get_config_api_gateway_authorizer_ecs_auth_service():
        return {"Content-Type": "application/json", "Cookie": f"session_id={session_id}"}

    if aws_app_config_client.get_config_api_gateway_authorizer_lambda_authorizer():
        return {"Content-Type": "application/json", "Authorization": f"Bearer {session_id}"}

    return {}


@app.route("/google-logged-in")
def google_logged_in() -> Response | WerkzeugResponse | str | tuple[str, int]:
    """Handle login callback from Google and create a session via the auth service."""
    if not google.authorized:
        return redirect(url_for("google.login"))
    resp = google.get("/oauth2/v2/userinfo")
    if not resp.ok:
        return f"Failed to fetch user info: {resp.text}", 500
    user_info = resp.json()

    try:
        auth_response = requests.post(
            f"{AUTH_SERVICE_URL}/store_google_user_info",
            json={"email": user_info.get("email"), "name": user_info.get("name")},
            timeout=3,
        )
        if auth_response.status_code != 200:
            return f"Failed to create session: {auth_response.text}", 500
        session_id = auth_response.json()["session_id"]
        response = make_response(render_template("google_logged_in.html", user=user_info, current_year=date.today().year))
        response.set_cookie("session_id", session_id, httponly=True, secure=False, domain=request.host, path="/", max_age=3600)
        return response
    except requests.exceptions.Timeout:
        return "Server timeout. Please try again.", 504


@app.route("/")
@check_already_logged_in
def index() -> Response | str | tuple[str, int]:
    """Landing page that checks for a valid session and shows user info if logged in."""
    session_id = request.cookies.get("session_id", "")
    if session_id:
        try:
            response = requests.post(f"{AUTH_SERVICE_URL}/verify", json={"session_id": session_id}, timeout=3)
            if response.status_code == 200:
                user = response.json().get("user")
                return render_template("index.html", user=user, current_year=date.today().year)
        except requests.exceptions.Timeout:
            return "Server timeout. Please try again.", 504
        except requests.RequestException:
            pass
    return render_template("index.html", user=None, current_year=date.today().year)


@app.route("/login", methods=["GET", "POST"])
def login() -> Response | WerkzeugResponse | str | tuple[str, int]:
    """Login form that authenticates user via the auth service and sets a session cookie."""
    error: str | None = None
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        try:
            response = requests.post(f"{AUTH_SERVICE_URL}/login", json={"username": username, "password": password}, timeout=3)
            if response.status_code == 200:
                session_id = response.json().get("session_id")
                if session_id:
                    resp = redirect(url_for("dashboard"))
                    resp.set_cookie(
                        "session_id", session_id, httponly=True, secure=False, domain=request.host, path="/", max_age=3600
                    )
                    return resp
                error = "Session ID missing from response."
            else:
                error = "Invalid credentials."
        except requests.exceptions.Timeout:
            return "Server timeout. Please try again.", 504
        except requests.RequestException:
            error = "Auth service unavailable."
    return render_template("login.html", error=error, current_year=date.today().year)  # type: ignore


@app.route("/dashboard")
@login_required
def dashboard() -> str:
    """User dashboard view."""
    return render_template("dashboard.html", current_year=date.today().year)


@app.route("/profile")
@login_required
def profile() -> str:
    """User profile page."""
    return render_template("profile.html", current_year=date.today().year)


@app.route("/settings")
@login_required
def settings() -> str:
    """User settings page."""
    return render_template("settings.html", current_year=date.today().year)


@app.route("/my-orders")
@login_required
def my_orders() -> Response | str | tuple[str, int]:
    """Retrieve and display the user's orders."""
    try:
        headers = __set_and_get_auth_headers()
        print(f"headers: {headers}")
        resp = requests.get(
            f"{AWS_REST_API_URL}/orders",
            cookies={"session_id": request.cookies.get("session_id", "")},
            headers=__set_and_get_auth_headers(),
            timeout=3,
        )
    except requests.exceptions.Timeout:
        return "Server timeout. Please try again.", 504

    if resp.status_code != 200:
        return f"Failed to fetch orders. Status code: {resp.status_code}", resp.status_code

    print(f"resp.status_code: {resp.status_code}")
    print(f"resp.json(): {resp.json()}")

    orders = resp.json() or []
    return render_template("my_orders.html", orders=orders, current_year=date.today().year)


@app.route("/my-orders/<order_id>")
@login_required
def get_order_detail(order_id: str) -> Response | str | tuple[str, int]:
    """Get details of a specific order."""
    try:
        resp = requests.get(
            f"{AWS_REST_API_URL}/orders/{order_id}",
            cookies={"session_id": request.cookies.get("session_id", "")},
            headers=__set_and_get_auth_headers(),
            timeout=3,
        )
    except requests.exceptions.Timeout:
        return "Server timeout. Please try again.", 504

    if resp.status_code == 404:
        return f"Order {order_id} not found.", 404
    order = resp.json()
    print(f"resp.json(): {resp.json()}")
    return render_template("order_detail.html", order=order, current_year=date.today().year)


@app.route("/place-order", methods=["GET", "POST"])
@login_required
def place_order() -> Response | WerkzeugResponse | str | tuple[str, int] | tuple[Response, int]:
    """Form to place a new order."""
    if request.method == "POST":
        items = request.form.get("items", "")
        total = request.form.get("total", 0)
        data = {"items": [i.strip() for i in items.split(",") if i.strip()], "total": float(total)}
        try:
            response = requests.post(
                f"{AWS_REST_API_URL}/orders",
                json=data,
                cookies={"session_id": request.cookies.get("session_id", "")},
                headers=__set_and_get_auth_headers(),
                timeout=3,
            )
            if response.status_code == 201:
                return redirect(url_for("my_orders"), code=303)  # 303 to prevent resubmission on refresh
            return f"Failed to create order. Status code: {response.status_code}", response.status_code
        except requests.exceptions.Timeout:
            return "Server timeout. Please try again.", 504
        except Exception as e:
            return f"Error: {str(e)}"
    return render_template("place_order.html", current_year=date.today().year)


@app.route("/my-orders/<order_id>/edit", methods=["GET", "POST"])
@login_required
def edit_order(order_id: str) -> Response | WerkzeugResponse | str | tuple[str, int] | tuple[Response, int]:
    """Edit an existing order."""
    api_url = f"{AWS_REST_API_URL}/orders/{order_id}"
    headers = __set_and_get_auth_headers()
    errors: dict[str, str] = {}
    order = {}

    if request.method == "POST":
        items_str = request.form.get("items", "").strip()
        total_str = request.form.get("total", "").strip()
        status = request.form.get("status", "").strip()

        items = [i.strip() for i in items_str.split(",") if i.strip()]
        if not items:
            errors["items"] = "Enter at least one item."

        try:
            total = float(total_str)
            if total < 0:
                errors["total"] = "Total must be ≥ 0."
        except ValueError:
            errors["total"] = "Total must be a valid number."

        if status not in ["created", "shipped", "canceled"]:
            errors["status"] = "Select a valid status."

        if not errors:
            payload = {"items": items, "total": total, "status": status}
            try:
                resp = requests.put(
                    api_url,
                    json=payload,
                    cookies={"session_id": request.cookies.get("session_id", "")},
                    headers=headers,
                    timeout=3,
                )
                if resp.status_code == 200:
                    return redirect(url_for("get_order_detail", order_id=order_id))
                errors["form"] = f"Update failed (status {resp.status_code})."
            except requests.exceptions.Timeout:
                return "Server timeout. Please try again.", 504
    else:
        try:
            resp = requests.get(
                api_url, cookies={"session_id": request.cookies.get("session_id", "")}, headers=headers, timeout=3
            )
        except requests.exceptions.Timeout:
            return "Server timeout. Please try again.", 504

        if resp.status_code != 200:
            return f"Failed to load order (status {resp.status_code}).", resp.status_code
        order = resp.json()

    print(f"order: {order}")

    return render_template("edit_order.html", order=order, errors=errors, current_year=date.today().year)


@app.route("/orders/<order_id>/delete", methods=["POST"])
@login_required
def delete_order(order_id: str) -> Response | str | tuple[str, int] | WerkzeugResponse:
    """Delete an order by ID."""
    api_url = f"{AWS_REST_API_URL}/orders/{order_id}"

    try:
        response = requests.delete(
            api_url,
            cookies={"session_id": request.cookies.get("session_id", "")},
            headers=__set_and_get_auth_headers(),
            timeout=3,
        )
        if response.status_code == 204:
            return redirect(url_for("my_orders"), code=303)  # 303 to prevent resubmission on refresh
        return f"Failed to delete order. Status code: {response.status_code}", response.status_code
    except requests.exceptions.Timeout:
        return "Server timeout. Please try again.", 504
    except Exception as e:
        return f"Error: {str(e)}"


@app.route("/logout", methods=["GET", "POST"])
def logout() -> Response | WerkzeugResponse | str | tuple[str, int]:
    """Logout the user by clearing session and redirecting through Google logout."""
    if session_id := request.cookies.get("session_id", ""):
        try:
            requests.post(f"{AUTH_SERVICE_URL}/logout", json={"session_id": session_id}, timeout=3)
            google.token = None
            session.clear()
            logout_url = (
                "https://accounts.google.com/Logout?continue=https://appengine.google.com/_ah/logout?"
                f"continue={url_for('index', _external=True)}"
            )
            resp = redirect(logout_url)
            resp.delete_cookie("session_id", domain=request.host, path="/")
            return resp
        except requests.exceptions.Timeout:
            return "Server timeout. Please try again.", 504
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT_FLASK", "5001")))
