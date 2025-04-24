import os
from datetime import date
from functools import wraps

import requests
from aws_app_config.aws_app_config_client_sandbox_alex import (
    AWSAppConfigClientSandboxAlex,
)
from dotenv import load_dotenv
from flask import (
    Flask,
    make_response,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_dance.contrib.google import google, make_google_blueprint

load_dotenv()

app = Flask(__name__)

# * AWS AppConfigClient instance - for feature flags
aws_app_config_client = AWSAppConfigClientSandboxAlex()

# print(f"GOOGLE_OAUTH_CLIENT_ID: {os.environ['GOOGLE_OAUTH_CLIENT_ID']}")
# print(f"GOOGLE_OAUTH_CLIENT_SECRET: {os.environ['GOOGLE_OAUTH_CLIENT_SECRET']}")

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

# Configurations
AUTH_SERVICE_URL = os.environ[
    "AUTH_SERVICE_URL_REST_API"
]  # URL of the authentication service
AWS_REST_API_URL = os.environ["ORDER_SERVICE_URL_REST_API"]
app.config["SECRET_KEY"] = os.environ["SECRET_KEY"]

os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = (
    "1"  # Allow HTTP for local testing with oAuthlib
)


# Decorator for session validation
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        session_id = request.cookies.get("session_id")

        print(f"request.cookies: {request.cookies}")
        print(f"session_id: {session_id}")

        if not session_id:
            return redirect(url_for("login"))

        # * Verify session with auth service
        response = requests.post(
            f"{AUTH_SERVICE_URL}/verify", json={"session_id": session_id}
        )
        print(f"decorator - response.status_code: {response.status_code}")
        print(f"json_response: {response.json()}")

        if response.status_code != 200:
            return redirect(url_for("login"))

        return f(*args, **kwargs)

    return decorated_function


@app.route("/google-logged-in")
def google_logged_in():
    if not google.authorized:
        return redirect(url_for("google.login"))
    resp = google.get("/oauth2/v2/userinfo")
    if not resp.ok:
        return f"Failed to fetch user info: {resp.text}", 500
    user_info = resp.json()

    # Send to auth_service
    auth_response = requests.post(
        AUTH_SERVICE_URL + "/store_google_user_info",
        json={
            "email": user_info.get("email"),
            "name": user_info.get("name"),
        },
    )

    if auth_response.status_code != 200:
        return f"Failed to create session: {auth_response.text}", 500

    session_id = auth_response.json()["session_id"]

    response = make_response(
        render_template(
            "google_logged_in.html", user=user_info, current_year=date.today().year
        )
    )

    response.set_cookie(
        "session_id",
        session_id,
        httponly=True,
        secure=False,
        domain=request.host,
        path="/",
        max_age=3600,
    )

    return response


@app.route("/")
def index():
    session_id = request.cookies.get("session_id")
    if session_id:
        try:
            response = requests.post(
                f"{AUTH_SERVICE_URL}/verify", json={"session_id": session_id}, timeout=3
            )
            if response.status_code == 200:
                user = response.json().get("user")
                return render_template(
                    "index.html", user=user, current_year=date.today().year
                )
        except requests.RequestException:
            pass
    return render_template("index.html", user=None, current_year=date.today().year)


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        try:
            response = requests.post(
                f"{AUTH_SERVICE_URL}/login",
                json={"username": username, "password": password},
                timeout=3,
            )
            if response.status_code == 200:
                session_id = response.json().get("session_id")
                if session_id:
                    resp = make_response(redirect(url_for("dashboard")))
                    resp.set_cookie(
                        "session_id",
                        session_id,
                        httponly=True,
                        secure=False,
                        domain=request.host,
                        path="/",
                        max_age=3600,
                    )
                    return resp
                else:
                    error = "Session ID missing from response."
            else:
                error = "Invalid credentials."
        except requests.RequestException:
            error = "Auth service unavailable."

    return render_template("login.html", error=error, current_year=date.today().year)


def __set_and_get_auth_headers() -> dict:
    """
    Set and get the auth headers for the request to the orders API.
    This function checks the type of authorizer used (ECS auth service or Lambda authorizer) and sets the headers accordingly.
    """
    session_id = request.cookies.get("session_id")
    headers = {}

    if aws_app_config_client.get_config_api_gateway_authorizer_ecs_auth_service():
        # * auth_service used - use `Cookie` session_id for authorization
        headers = {
            "Content-Type": "application/json",
            "Cookie": f"session_id={session_id}",
        }
    elif aws_app_config_client.get_config_api_gateway_authorizer_lambda_authorizer():
        # * lambda_authorizer used - use `Bearer` token session_id for authorization
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {session_id}",
        }

    return headers


@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html", current_year=date.today().year)


@app.route("/profile")
@login_required
def profile():
    return render_template("profile.html", current_year=date.today().year)


@app.route("/settings")
@login_required
def settings():
    return render_template("settings.html", current_year=date.today().year)


@app.route("/my-orders")
@login_required
def my_orders():
    resp = requests.get(
        f"{AWS_REST_API_URL}/orders", headers=__set_and_get_auth_headers()
    )
    if resp.status_code != 200:
        print("Failed to fetch orders:", resp.status_code, resp.json())
        return f"Failed to fetch orders. Status code: {resp.status_code}"
    orders = resp.json().get("orders", [])
    return render_template(
        "my_orders.html", orders=orders, current_year=date.today().year
    )


@app.route("/my-orders/<order_id>")
@login_required
def get_order_detail(order_id):
    resp = requests.get(
        f"{AWS_REST_API_URL}/orders/{order_id}", headers=__set_and_get_auth_headers()
    )
    if resp.status_code == 404:
        return f"Order {order_id} not found."
    order = resp.json()
    return render_template(
        "order_detail.html", order=order, current_year=date.today().year
    )


@app.route("/place-order", methods=["GET", "POST"])
@login_required
def place_order():
    if request.method == "POST":
        print(f"place_order - POST - request.form: {request.form}")

        items = request.form.get("items", "")
        total = request.form.get("total", 0)

        data = {
            "items": [i.strip() for i in items.split(",") if i.strip()],
            "total": float(total),
        }

        try:
            print(f"POST orders_api_url - url: {AWS_REST_API_URL}/orders")
            print(f"POST orders_api_url - data: {data}")
            print(f"POST orders_api_url - headers: {__set_and_get_auth_headers()}")
            response = requests.post(
                f"{AWS_REST_API_URL}/orders",
                json=data,
                headers=__set_and_get_auth_headers(),
            )
            if response.status_code == 201:  # created status code
                return redirect(url_for("my_orders"))
            return f"Failed to create order. Status code: {response.status_code}"
        except Exception as e:
            return f"Error: {str(e)}"

    return render_template("place_order.html", current_year=date.today().year)


@app.route("/my-orders/<order_id>/edit", methods=["GET", "POST"])
@login_required
def edit_order(order_id):
    """Fetches an order, validates input, and updates via a PUT to order_service."""
    api_url = f"{AWS_REST_API_URL}/orders/{order_id}"
    headers = __set_and_get_auth_headers()
    errors = {}

    if request.method == "POST":
        # Read form inputs
        items_str = request.form.get("items", "").strip()
        total_str = request.form.get("total", "").strip()
        status = request.form.get("status", "").strip()

        # Validate items: at least one
        items = [i.strip() for i in items_str.split(",") if i.strip()]
        if not items:
            errors["items"] = "Enter at least one item."

        # Validate total: numeric and >= 0
        try:
            total = float(total_str)
            if total < 0:
                errors["total"] = "Total must be ≥ 0."
        except ValueError:
            errors["total"] = "Total must be a valid number."

        # Validate status
        if status not in ["created", "shipped", "canceled"]:
            errors["status"] = "Select a valid status."

        # If no validation errors, send update
        if not errors:
            payload = {"items": items, "total": total, "status": status}
            resp = requests.put(api_url, json=payload, headers=headers)
            if resp.status_code == 200:
                return redirect(url_for("get_order_detail", order_id=order_id))
            errors["form"] = f"Update failed (status {resp.status_code})."
    else:
        # GET: load existing order
        resp = requests.get(api_url, headers=headers)
        if resp.status_code != 200:
            return f"Failed to load order (status {resp.status_code})."
        order = resp.json()

    return render_template(
        "edit_order.html", order=order, errors=errors, current_year=date.today().year
    )


@app.route("/logout")
def logout():
    session_id = request.cookies.get("session_id")

    print(f"auth_api_url: {AUTH_SERVICE_URL}/logout")
    print(f"session_id: {session_id}")

    if session_id:
        response = requests.post(
            f"{AUTH_SERVICE_URL}/logout", json={"session_id": session_id}
        )

        print(f"response.status_code: {response.status_code}")
        print(f"json_response: {response.json()}")

        # 🔐 Clear the Google OAuth token
        google.token = None
        session.clear()

        logout_url = (
            "https://accounts.google.com/Logout?continue=https://appengine.google.com/_ah/logout?"
            f"continue={url_for('index', _external=True)}"
        )

        resp = make_response(redirect(logout_url))
        resp.delete_cookie("session_id", domain=request.host, path="/")

    else:
        resp = make_response(redirect(url_for("index")))

    return resp


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT_FLASK", 5001)))
