import os
from typing import Optional

import redis
from flask import Flask, Response, make_response, redirect, request, session, url_for
from flask_login import LoginManager, UserMixin, current_user, login_required, login_user, logout_user
from flask_session import Session

# * initialize flask app
app = Flask(__name__)

# * session and secret key configuration
app.config["SECRET_KEY"] = "supersecretkey"  # nosec B105
app.config["SESSION_TYPE"] = "redis"
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_USE_SIGNER"] = True
app.config["SESSION_KEY_PREFIX"] = "flask_session:"

try:
    print(f"Connecting to Redis at {os.environ['REDIS_HOST']}:{os.getenv('REDIS_PORT', '6379')}")
    app.config["SESSION_REDIS"] = redis.Redis(
        host=os.environ["REDIS_HOST"],
        port=int(os.getenv("REDIS_PORT", "6379")),
        decode_responses=False,
        socket_timeout=5,
        ssl=True,
    )
except Exception as e:
    print(f"Error connecting to Redis: {e}")

# * enable server-side session
Session(app)

# * setup flask-login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# * simulated user database (replace with real DB later)
users = {"admin": {"password": "password123"}}


class User(UserMixin):
    """Basic User class for Flask-Login."""

    def __init__(self, username: str):
        self.id = username


@login_manager.user_loader
def load_user(user_id: str) -> Optional[User]:
    """Load user by ID from mock database."""
    if user_id in users:
        return User(user_id)
    return None


@app.route("/")
def index() -> str:
    """Root page with greeting based on login status."""
    session["test"] = "hello"
    if current_user.is_authenticated:
        return f"Hello, {current_user.id}! You are logged in."
    return "Hello, Guest! <a href='/login'>Login here</a>"


@app.route("/login", methods=["GET", "POST"])
def login() -> Response:
    """Login form handler. Authenticates user and sets session."""
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        if username in users and users[username]["password"] == password:
            user = User(username)
            login_user(user)
            session["user"] = username
            return make_response(redirect(url_for("dashboard")))

        return Response("Invalid credentials, try again.", mimetype="text/html")

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
    return f"Welcome to your dashboard, {current_user.id}!"


@app.route("/logout")
@login_required
def logout() -> Response:
    """Logout the user and clear session."""
    session.pop("user", None)
    logout_user()
    return make_response(redirect(url_for("index")))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
