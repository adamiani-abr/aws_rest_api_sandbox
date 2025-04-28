import json
import os
import uuid
from typing import Dict, Optional, Tuple

import redis
from flask import Flask, Response, jsonify, request

# * create the Flask app
app = Flask(__name__)

# * flask session configuration
app.config["SECRET_KEY"] = os.environ["SECRET_KEY"]
app.config["SESSION_TYPE"] = "redis"
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_USE_SIGNER"] = True
app.config["SESSION_KEY_PREFIX"] = "auth_session:"

# * connect to redis
try:
    redis_host = os.environ["REDIS_HOST"]
    redis_port = int(os.getenv("REDIS_PORT", "6379"))
    print(f"connecting to redis at {redis_host}:{redis_port}")

    session_store = redis.Redis(
        host=redis_host,
        port=redis_port,
        decode_responses=False,
        socket_timeout=5,
        ssl=(os.getenv("REDIS_SSL", "false") == "true"),
    )
except Exception as e:
    print(f"error connecting to redis: {e}")

# * simulated user database
users: Dict[str, Dict[str, str]] = {
    "programmingwithalex3@gmail.com": {"password": "password123"},
    "test_user": {"password": "passwordtest"},
}


@app.route("/login", methods=["POST"])
def login() -> Tuple[Response, int]:
    """
    login route to authenticate a user and create a session in redis
    """
    print("auth service - login()")
    data: Dict[str, str] = request.json or {}

    username = data.get("username")
    password = data.get("password")

    if username in users and users[username]["password"] == password:
        # print(f"user {username} authenticated successfully")
        session_id = str(uuid.uuid4())
        session_store.setex(
            f"session:{session_id}",
            int(os.getenv("SESSION_EXPIRE_TIME_SECONDS", "3600")),
            json.dumps({"email": username, "name": username, "source": "manual"}),
        )
        # print(f"session created for {username}: {session_id}")
        return jsonify({"message": "login successful", "session_id": session_id}), 200

    return jsonify({"message": "invalid credentials"}), 401


@app.route("/store_google_user_info", methods=["POST"])
def store_google_user_info() -> Tuple[Response, int]:
    """
    create a session using google auth user info
    """
    print("auth service - store_google_user_info()")
    try:
        data: Dict[str, str] = request.json or {}
        email = data["email"]
        name = data["name"]

        session_id = str(uuid.uuid4())
        session_data = {"email": email, "name": name, "source": "google"}

        session_store.setex(
            f"session:{session_id}",
            int(os.getenv("SESSION_EXPIRE_TIME_SECONDS", "3600")),
            json.dumps(session_data),
        )

        return jsonify({"session_id": session_id}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/verify", methods=["POST"])
def verify() -> Tuple[Response, int]:
    """
    verify session by checking redis for the given session_id
    """
    print("verifying session...")
    data: Dict[str, str] = request.json or {}
    session_id = data.get("session_id")

    # print(f"session_id: {session_id}")

    if not session_id:
        return jsonify({"message": "session ID required"}), 400

    username: Optional[bytes] = session_store.get(f"session:{session_id}")  # type: ignore
    # print(f"username: {username}")

    if username:
        decoded = username.decode("utf-8")
        # print(f"decoded username: {decoded}")
        return jsonify({"message": "valid session", "user": json.loads(decoded)}), 200

    return jsonify({"message": "invalid session"}), 401


@app.route("/logout", methods=["POST"])
def logout() -> Tuple[Response, int]:
    """
    logout route to delete the session from redis
    """
    data: Dict[str, str] = request.json or {}
    session_id = data.get("session_id")

    if session_id:
        session_store.delete(f"session:{session_id}")
        return jsonify({"message": "logged out successfully"}), 200

    return jsonify({"message": "invalid session ID"}), 400


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT_FLASK", "5000")))
