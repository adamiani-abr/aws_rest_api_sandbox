import os

import redis
from flask import Flask, redirect, request, session, url_for
from flask_login import (
    LoginManager,
    UserMixin,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from flask_session import Session

app = Flask(__name__)

# Session and secret key configuration
app.config["SECRET_KEY"] = "supersecretkey"
app.config["SESSION_TYPE"] = "redis"
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_USE_SIGNER"] = True
app.config["SESSION_KEY_PREFIX"] = "flask_session:"

try:
    print(
        f"Connecting to Redis at {os.environ['REDIS_HOST']}:{os.getenv('REDIS_PORT', 6379)}"
    )
    app.config["SESSION_REDIS"] = redis.Redis(
        host=os.environ["REDIS_HOST"],
        port=int(os.getenv("REDIS_PORT", 6379)),
        # decode_responses=True,  # all responses from Redis are returned as Python strings instead of raw bytes
        decode_responses=False,  # all responses from Redis are returned as raw bytes
        socket_timeout=5,  # timeout for Redis connection
        ssl=True,  # enable SSL
    )
except Exception as e:
    print(f"Error connecting to Redis: {e}")

Session(app)

# Setup Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# Simulated user database (Replace with real DB later)
users = {"admin": {"password": "password123"}}


class User(UserMixin):
    def __init__(self, username):
        self.id = username


@login_manager.user_loader
def load_user(user_id):
    if user_id in users:
        return User(user_id)
    return None


@app.route("/")
def index():
    session["test"] = "hello"

    if current_user.is_authenticated:
        return f"Hello, {current_user.id}! You are logged in."
    return "Hello, Guest! <a href='/login'>Login here</a>"


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        if username in users and users[username]["password"] == password:
            user = User(username)
            login_user(user)
            session["user"] = username  # Store user in Redis session
            return redirect(url_for("dashboard"))

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
    return f"Welcome to your dashboard, {current_user.id}!"


@app.route("/logout")
@login_required
def logout():
    session.pop("user", None)  # Remove user from Redis session
    logout_user()
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
