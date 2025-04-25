# Setup

Assuming using a `flask` app to initiate connections.

## AWS Elasticache Connection

* uses TLS so must have the `ssl=True` parameter set for the `redis` connection in the `flask` app, otherwise will hang indefinitely
* must set `decode_responses=False`, otherwise `flask` app won't be able to decode values from `redis` storage

```python
app = Flask(__name__)

# Session and secret key configuration
app.config["SECRET_KEY"] = "supersecretkey"
app.config["SESSION_TYPE"] = "redis"
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_USE_SIGNER"] = True
app.config["SESSION_KEY_PREFIX"] = "flask_session:"

try:
    print(f"Connecting to Redis at {os.environ['REDIS_HOST']}:{os.getenv('REDIS_PORT', "6379")}")
    app.config["SESSION_REDIS"] = redis.Redis(
        host=os.environ["REDIS_HOST"],
        port=int(os.getenv("REDIS_PORT", "6379")),
        # decode_responses=True,  # all responses from Redis are returned as Python strings instead of raw bytes
        decode_responses=False,  # all responses from Redis are returned as raw bytes
        socket_timeout=5,  # timeout for Redis connection
        ssl=True,  # enable SSL
    )
except Exception as e:
    print(f"Error connecting to Redis: {e}")
```

## Storing Cache Client Side

* if not using HTTPS connection, then have to set `secure=False` when setting cookie client side
* cookie must be set at domain level (`ALB`/`Route53`/etc. DNS name)
  * if not then it will not persist updates to the AWS ECS web service

```python
from flask import make_response

...
@app.route("/login", methods=["GET", "POST"])
def login():
    ...

    resp = make_response(redirect(url_for("dashboard")))

    resp.set_cookie(
        "session_id",
        session_id,
        httponly=True,
        # secure=True,  # if using HTTPS then must set `secure=True`
        secure=False,  # if using HTTP then browser will not allow to set secure cookie, must set `secure=False`
        domain=os.environ["AWS_ALB_DNS_NAME"],  # store session cookie at ALB level so persists updates of ECS service
        path="/",
    )
```
