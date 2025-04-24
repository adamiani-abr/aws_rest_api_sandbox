import os

from flask import Flask

app = Flask(__name__)

# app.config["SECRET_KEY"] = os.environ["SECRET_KEY"]


@app.route("/")
def index():
    return {"message": "Hello world!"}


@app.route("/dummy1")
def dummy_route():
    return {"message": "dummy route 1!"}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT_FLASK", 5002)))
