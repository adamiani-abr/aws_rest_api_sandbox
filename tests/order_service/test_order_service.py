import requests
import uuid
import redis
import os
from dotenv import load_dotenv

# Adjust the path to your .env file relative to your working directory.
load_dotenv(dotenv_path="src_api_gateway/web_service/.env")

# Base URL of your API Gateway (public endpoint)
ORDER_SERVICE_URL_REST_API = os.environ["ORDER_SERVICE_URL_REST_API"]


def setup_test_session(token, user_data):
    """
    Inserts a session in Redis that the Lambda authorizer will find.
    Make sure your environment variables for REDIS_HOST and REDIS_PORT are set.
    """
    print("REDIS_HOST:", os.environ.get("REDIS_HOST"))
    print("REDIS_PORT:", os.environ.get("REDIS_PORT"))

    session_store = redis.Redis(
        host=os.environ["REDIS_HOST"],
        port=int(os.getenv("REDIS_PORT", 6379)),
        # decode_responses=True,  # Redis responses returned as Python strings instead of raw bytes - for debugging
        decode_responses=False,  # Redis responses returned as raw bytes - must be False if trying to read session data
        socket_timeout=5,
        # ssl=True,  # must be enabled if connecting to Redis in AWS ElastiCache
    )
    session_key = f"session:{token}"
    # Store the user data (as bytes) with an expiration (e.g., 1 hour)
    session_store.set(session_key, user_data.encode("utf-8"), ex=3600)


def test_get_order_authorized():
    """
    Tests the /orders/<order_id> endpoint with a valid token.
    The token is pre-registered in Redis so the Lambda authorizer returns Allow.
    """
    # Generate a unique token for this test.
    test_token = str(uuid.uuid4())
    # Set up a valid session in Redis for the test token.
    setup_test_session(test_token, "test_user")

    headers = {"Authorization": f"Bearer {test_token}"}
    response = requests.get(f"{ORDER_SERVICE_URL_REST_API}/orders/123", headers=headers)
    assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}"
    # Additional assertions can verify response content if needed.


def test_get_order_without_token():
    """
    Tests that accessing the endpoint without an Authorization header is rejected.
    """
    response = requests.get(f"{ORDER_SERVICE_URL_REST_API}/orders/123")
    assert response.status_code in (401, 403), f"Expected 401/403, got {response.status_code}"


def test_get_order_with_invalid_token():
    """
    Tests that an invalid token (i.e., one not present in Redis) is correctly rejected.
    """
    invalid_token = "invalid-token"
    headers = {"Authorization": f"Bearer {invalid_token}"}
    response = requests.get(f"{ORDER_SERVICE_URL_REST_API}/orders/123", headers=headers)
    assert response.status_code in (401, 403), f"Expected 401/403 for invalid token, got {response.status_code}"


# Optionally, you may run tests manually:
if __name__ == "__main__":
    test_get_order_authorized()
    test_get_order_without_token()
    test_get_order_with_invalid_token()
    print("All tests passed!")
