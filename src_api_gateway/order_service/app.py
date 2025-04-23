from flask import Flask, request, jsonify
import uuid
import time
import requests
from typing import Optional, Dict, Any
import os
from dotenv import load_dotenv
from aws_app_config.aws_app_config_client_sandbox_alex import (
    AWSAppConfigClientSandboxAlex,
)
import json

# * Load environment variables from a .env file
load_dotenv(dotenv_path="src_api_gateway/.env")

app = Flask(__name__)

# * AWS AppConfigClient instance - for feature flags
aws_app_config_client = AWSAppConfigClientSandboxAlex()

AUTH_SERVICE_URL = os.environ["AUTH_SERVICE_URL_REST_API"]  # URL of the authentication service

# In-memory store: user_id -> {order_id -> order_data}
ORDERS: Dict[str, Dict[str, Dict[str, Any]]] = {
    "admin": {
        "order-001": {
            "order_id": "order-001",
            "items": ["apple", "banana"],
            "status": "created",
            "total": 12.5,
            "timestamp": int(time.time()) - 3600,
        },
        "order-002": {
            "order_id": "order-002",
            "items": ["notebook", "pen"],
            "status": "shipped",
            "total": 23.0,
            "timestamp": int(time.time()) - 1800,
        },
    }
}


def verify_session(session_id: Optional[str]) -> Optional[str]:
    """Verify the session with the auth service and return user_id."""
    if not session_id:
        return None
    try:
        headers = {
            "Authorization": f"Bearer {session_id}",
            "Content-Type": "application/json",
        }
        response = requests.post(
            f"{AUTH_SERVICE_URL}/verify",
            json={"session_id": session_id},
            timeout=3,
            headers=headers,
        )

        print(f"response.status_code: {response.status_code}")
        print(f"response.json(): {response.json()}")

        if response.status_code == 200:
            return json.loads(response.json().get("user", "{}")).get("email")
    except requests.RequestException:
        pass
    return None


def __get_user_id_from_authorizer() -> Optional[str]:
    """Get user_id from either the auth service or the Lambda authorizer."""
    user_id = ""

    if aws_app_config_client.get_config_api_gateway_authorizer_ecs_auth_service():
        user_id = verify_session(request.cookies.get("session_id"))
        print(f"request.cookies: {request.cookies}")
        print(f"reqeuest.cookies.get(session_id): {request.cookies.get('session_id')}")
    elif aws_app_config_client.get_config_api_gateway_authorizer_lambda_authorizer():
        user_id = request.headers.get("X-User")  # <-- Injected by API Gateway from Lambda authorizer
    else:
        user_id = verify_session(request.cookies.get("session_id"))

    return user_id


@app.route("/orders", methods=["GET"])
def list_orders() -> Any:
    """Return all orders for the authenticated user."""
    user_id = __get_user_id_from_authorizer()

    print(f"/orders - GET - user_id: {user_id}")
    print(f"request.headers: {request.headers}")

    if not user_id:
        return jsonify({"message": "Unauthorized"}), 401

    user_orders = list(ORDERS.get(user_id, {}).values())
    return jsonify({"orders": user_orders}), 200


@app.route("/orders/<order_id>", methods=["GET"])
def get_order(order_id: str) -> Any:
    """Return a specific order by order_id for the authenticated user."""
    user_id = __get_user_id_from_authorizer()

    print(f"/orders - GET - user_id: {user_id}")

    if not user_id:
        return jsonify({"message": "Unauthorized"}), 401  # 401: Client is not authenticated

    order = ORDERS.get(user_id, {}).get(order_id)

    if not order:
        return jsonify({"message": "Order not found"}), 404

    return jsonify(order)


@app.route("/orders", methods=["POST"])
def create_order() -> Any:
    """Create a new order for the authenticated user."""
    user_id = __get_user_id_from_authorizer()

    print(f"/orders - POST - user_id: {user_id}")

    if not user_id:
        return jsonify({"message": "Unauthorized"}), 401  # 401: Client is not authenticated

    data: Dict[str, Any] = request.json or {}
    order_id = str(uuid.uuid4())
    order = {
        "order_id": order_id,
        "items": data.get("items", []),
        "status": "created",
        "total": data.get("total", 0),
        "timestamp": int(time.time()),
    }

    print(f"order_id: {order_id}")
    print(f"order: {order}")
    print(jsonify({"order_id": order_id, "message": "Order created"}))

    if user_id not in ORDERS:
        ORDERS[user_id] = {}

    ORDERS[user_id][order_id] = order
    return jsonify({"order_id": order_id, "message": "Order created"}), 201  # 201: Resource created


@app.route("/orders/<order_id>", methods=["PUT"])
def update_order(order_id: str) -> Any:
    """Update an existing order for the authenticated user."""
    user_id = __get_user_id_from_authorizer()
    if not user_id:
        return jsonify({"message": "Unauthorized"}), 401

    data: Dict[str, Any] = request.json or {}
    user_orders = ORDERS.get(user_id, {})
    order = user_orders.get(order_id)

    if not order:
        return jsonify({"message": "Order not found"}), 404

    # Only allow these fields to be updated
    updatable_fields = {"items", "status", "total"}
    for field in updatable_fields.intersection(data.keys()):
        order[field] = data[field]

    # (Optional) bump the timestamp to now to reflect the update
    import time

    order["timestamp"] = int(time.time())

    return jsonify(order), 200


@app.route("/orders/<order_id>", methods=["DELETE"])
def delete_order(order_id: str) -> Any:
    """Delete an existing order for the authenticated user."""
    user_id = __get_user_id_from_authorizer()

    if not user_id:
        return jsonify({"message": "Unauthorized"}), 401  # 401: Client is not authenticated

    user_orders = ORDERS.get(user_id, {})
    if order_id not in user_orders:
        return jsonify({"message": "Order not found"}), 404

    del user_orders[order_id]
    return jsonify({"message": "Order deleted"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT_FLASK", 5003)))
