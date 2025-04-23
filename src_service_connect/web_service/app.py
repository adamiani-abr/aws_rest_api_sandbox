from flask import Flask, request, redirect, url_for, make_response
import os
import requests
from functools import wraps

app = Flask(__name__)

# Configurations
AUTH_SERVICE_URL = os.environ["AUTH_SERVICE_URL"]  # URL of the authentication service
app.config["SECRET_KEY"] = os.environ["SECRET_KEY"]


# Decorator for session validation
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        session_id = request.cookies.get("session_id")

        if not session_id:
            return redirect(url_for("login"))

        # Verify session with auth service
        response = requests.post(f"{AUTH_SERVICE_URL}/verify", json={"session_id": session_id})
        print(f"decorator - response.status_code: {response.status_code}")

        if response.status_code != 200:
            return redirect(url_for("login"))

        return f(*args, **kwargs)

    return decorated_function


@app.before_request
def set_script_root():
    request.script_root = request.headers.get("X-Forwarded-Prefix", "")


@app.route("/")
def index():
    session_id = request.cookies.get("session_id")

    if session_id:
        response = requests.post(f"{AUTH_SERVICE_URL}/verify", json={"session_id": session_id})

        if response.status_code == 200:
            user = response.json().get("user")
            return f"Hello, {user}! You are logged in. <a href='/dashboard'>Go to Dashboard</a> | <a href='/logout'>Logout</a>"

    return "Hello, Guest! <a href='/login'>Login here</a>"


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        response = requests.post(f"{AUTH_SERVICE_URL}/login", json={"username": username, "password": password})
        print(f"response.status_code: {response.status_code}")
        print(f"json_response: {response.json()}")

        if response.status_code == 200:
            session_id = response.json().get("session_id")

            # resp = make_response(redirect(url_for("dashboard")))
            resp = make_response(redirect(f"{request.script_root}{url_for('dashboard')}"))

            resp.set_cookie(
                "session_id",
                session_id,
                httponly=True,
                # secure=True,  # if using HTTPS then must set `secure=True`
                secure=False,  # if using HTTP then browser will not allow to set secure cookie, must set `secure=False`
                domain=os.environ["AWS_ALB_DNS_NAME"],  # store session cookie at ALB level so persists updates of ECS service
                path="/",
            )

            return resp

        return "Invalid credentials, try again."

    return """
        <form method="post">
            Username: <input type="text" name="username"><br>
            Password: <input type="password" name="password"><br>
            <input type="submit" value="Login">
        </form>
    """


@app.route("/dashboard")
@login_required
def dashboard():
    return "Welcome to your Dashboard! <a href='/profile'>Go to Profile</a> | <a href='/settings'>Settings</a> | <a href='/logout'>Logout</a>"


@app.route("/profile")
@login_required
def profile():
    return "This is your profile page. <a href='/dashboard'>Back to Dashboard</a>"


@app.route("/settings")
@login_required
def settings():
    return "Settings page. Customize your preferences here. <a href='/dashboard'>Back to Dashboard</a>"


@app.route("/logout")
def logout():
    session_id = request.cookies.get("session_id")

    if session_id:
        requests.post(f"{AUTH_SERVICE_URL}/logout", json={"session_id": session_id})

    # Clear the session cookie
    resp = make_response(redirect(url_for("index")))
    resp.delete_cookie("session_id")
    return resp


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT_FLASK", 5001)))
