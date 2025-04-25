import os

from flask import Flask, Response, jsonify

# * create flask app instance
app = Flask(__name__)

# * optional secret key if needed
# app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "default-secret-key")


@app.route("/")
def index() -> Response:
    """
    root route returning a basic hello message
    """
    return jsonify({"message": "hello world!"})


@app.route("/dummy1")
def dummy_route() -> Response:
    """
    dummy test route
    """
    return jsonify({"message": "dummy route 1!"})


if __name__ == "__main__":
    # * start the app on host 0.0.0.0 with a configurable port
    app.run(host="0.0.0.0", port=int(os.getenv("PORT_FLASK", "5002")))
