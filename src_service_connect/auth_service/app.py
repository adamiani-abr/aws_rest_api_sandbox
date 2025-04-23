from flask import Flask, request, jsonify
import redis
import os
import uuid

app = Flask(__name__)

# Flask Session Configuration
app.config["SECRET_KEY"] = os.environ["SECRET_KEY"]
app.config["SESSION_TYPE"] = "redis"
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_USE_SIGNER"] = True
app.config["SESSION_KEY_PREFIX"] = "auth_session:"

# Connect to Redis
# try:
print(f"Connecting to Redis at {os.environ['REDIS_HOST']}:{os.getenv('REDIS_PORT', 6379)}")
session_store = redis.Redis(
    host=os.environ["REDIS_HOST"],
    port=int(os.getenv("REDIS_PORT", 6379)),
    # decode_responses=True,  # Redis responses returned as Python strings instead of raw bytes - for debugging
    decode_responses=False,  # Redis responses returned as raw bytes - must be False if trying to read session data
    socket_timeout=5,
    ssl=True,  # must be enabled if connecting to Redis in AWS ElastiCache
)
# except Exception as e:
#     print(f"Error connecting to Redis: {e}")

# Simulated user database (Replace with real DB later)
users = {"admin": {"password": "password123"}}


@app.route("/login", methods=["POST"])
def login():
    data = request.json
    username = data.get("username")
    password = data.get("password")

    if username in users and users[username]["password"] == password:
        # Create a session ID and store it in Redis
        session_id = str(uuid.uuid4())
        session_store.setex(
            f"session:{session_id}",
            int(os.getenv("SESSION_EXPIRE_TIME_SECONDS", 3600)),  # session expires in 1 hour
            username,
        )

        return jsonify({"message": "Login successful", "session_id": session_id})

    return jsonify({"message": "Invalid credentials"}), 401


@app.route("/verify", methods=["POST"])
def verify():
    data = request.json
    session_id = data.get("session_id")

    if not session_id:
        return jsonify({"message": "Session ID required"}), 400

    username = session_store.get(f"session:{session_id}")

    if username:
        username = username.decode("utf-8")  # username retrieved from Redis is in a format that jsonify() does not support
        return jsonify({"message": "Valid session", "user": username})

    return jsonify({"message": "Invalid session"}), 401


@app.route("/logout", methods=["POST"])
def logout():
    data = request.json
    session_id = data.get("session_id")

    if session_id:
        session_store.delete(f"session:{session_id}")
        return jsonify({"message": "Logged out successfully"})

    return jsonify({"message": "Invalid session ID"}), 400


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT_FLASK", 5000)))
