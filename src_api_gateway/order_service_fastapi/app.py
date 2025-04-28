import json
import logging
import os
import time
import uuid
from typing import Any, Dict, List, Optional

import boto3
import requests
import uvicorn
from aws_app_config.aws_app_config_client_sandbox_alex import AWSAppConfigClientSandboxAlex
from dotenv import load_dotenv
from fastapi import BackgroundTasks, Cookie, Depends, FastAPI, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# * Load environment variables
load_dotenv(dotenv_path="src_api_gateway/.env")

app = FastAPI()
aws_app_config_client = AWSAppConfigClientSandboxAlex()
AUTH_SERVICE_URL = os.environ["AUTH_SERVICE_URL_REST_API"]

# In-memory store: user_id -> {order_id -> order_data}
ORDERS: Dict[str, Dict[str, Dict[str, Any]]] = {
    "programmingwithalex3@gmail.com": {
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


# * Pydantic models
class OrderCreate(BaseModel):
    items: List[str]
    total: float


class OrderUpdate(BaseModel):
    items: Optional[List[str]] = None
    total: Optional[float] = None
    status: Optional[str] = None


class OrderResponse(BaseModel):
    order_id: str
    items: List[str]
    status: str
    total: float
    timestamp: int


class OrdersListResponse(BaseModel):
    orders: List[OrderResponse]


# * Session verification dependency
def get_user_id(
    request: Request,
    session_id: Optional[str] = Cookie(default=None),
    x_user: Optional[str] = Header(default=None),
) -> str:
    """
    Dependency to retrieve and verify the authenticated user's ID.

    Depending on the AppConfig flags:
    - If using ECS auth service, it validates session_id from cookies.
    - If using Lambda authorizer, it reads X-User from headers.
    - Falls back to cookie session verification if no config matches.

    Raises:
        HTTPException: If user authentication fails.

    Returns:
        str: Authenticated user's ID (typically email).
    """
    user_id = None

    if aws_app_config_client.get_config_api_gateway_authorizer_ecs_auth_service():
        session_id = request.cookies.get("session_id")
        user_id = verify_session(session_id)
    elif aws_app_config_client.get_config_api_gateway_authorizer_lambda_authorizer():
        user_id = x_user
    else:
        session_id = request.cookies.get("session_id")
        user_id = verify_session(session_id)

    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    return user_id


def verify_session(session_id: Optional[str]) -> Optional[str]:
    """
    Verify the session ID with the authentication service.

    Args:
        session_id (Optional[str]): Session ID retrieved from cookies.

    Returns:
        Optional[str]: User ID (email) if session is valid, None otherwise.
    """
    if not session_id:
        return None
    try:
        headers = {"Authorization": f"Bearer {session_id}", "Content-Type": "application/json"}
        response = requests.post(f"{AUTH_SERVICE_URL}/verify", json={"session_id": session_id}, headers=headers, timeout=3)

        if response.status_code == 200:
            return response.json().get("user", {}).get("email")
    except requests.RequestException:
        pass
    return None


# * Endpoints
@app.get("/orders", response_model=OrdersListResponse)
def list_orders(user_id: str = Depends(get_user_id)) -> OrdersListResponse:
    """
    Retrieve all orders for the authenticated user.

    Args:
        user_id (str): User ID obtained from authentication dependency.

    Returns:
        OrdersListResponse: List of orders.
    """
    return OrdersListResponse(orders=[OrderResponse(**order) for order in ORDERS.get(user_id, {}).values()])


@app.get("/orders/{order_id}", response_model=OrderResponse)
def get_order(order_id: str, user_id: str = Depends(get_user_id)) -> OrderResponse:
    """
    Retrieve a specific order by order ID for the authenticated user.

    Args:
        order_id (str): ID of the order to retrieve.
        user_id (str): User ID obtained from authentication dependency.

    Raises:
        HTTPException: If order not found.

    Returns:
        OrderResponse: Order details.
    """
    order = ORDERS.get(user_id, {}).get(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return OrderResponse(**order)


@app.post("/orders", status_code=201)
def create_order(
    order: OrderCreate,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_user_id),
) -> dict:
    """
    Create a new order for the authenticated user.

    Args:
        order (OrderCreate): Order creation payload.
        background_tasks (BackgroundTasks): FastAPI background task handler.
        user_id (str): User ID obtained from authentication dependency.

    Returns:
        dict: Order creation confirmation with order ID.
    """
    order_id = str(uuid.uuid4())
    new_order = {
        "order_id": order_id,
        "items": order.items,
        "status": "created",
        "total": order.total,
        "timestamp": int(time.time()),
    }
    ORDERS.setdefault(user_id, {})[order_id] = new_order

    # * schedule publishing to sns in the background
    background_tasks.add_task(publish_order_created_event_to_aws_sns, user_id, new_order)

    return {"order_id": order_id, "message": "Order created"}


@app.put("/orders/{order_id}", response_model=OrderResponse)
def update_order(order_id: str, update: OrderUpdate, user_id: str = Depends(get_user_id)) -> OrderResponse:
    """
    Update an existing order for the authenticated user.

    Args:
        order_id (str): ID of the order to update.
        update (OrderUpdate): Fields to update.
        user_id (str): User ID obtained from authentication dependency.

    Raises:
        HTTPException: If order not found.

    Returns:
        OrderResponse: Updated order details.
    """
    user_orders = ORDERS.get(user_id, {})
    order = user_orders.get(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    for field in {"items", "status", "total"}:
        val = getattr(update, field)
        if val is not None:
            order[field] = val

    order["timestamp"] = int(time.time())
    return OrderResponse(**order)


@app.delete("/orders/{order_id}", status_code=204)
def delete_order(order_id: str, user_id: str = Depends(get_user_id)) -> JSONResponse:
    """
    Delete an existing order for the authenticated user.

    Args:
        order_id (str): ID of the order to delete.
        user_id (str): User ID obtained from authentication dependency.

    Raises:
        HTTPException: If order not found.

    Returns:
        JSONResponse: 204 No Content on successful deletion.
    """
    user_orders = ORDERS.get(user_id, {})
    if order_id not in user_orders:
        raise HTTPException(status_code=404, detail="Order not found")
    del user_orders[order_id]
    return JSONResponse(status_code=204, content=None)


def publish_order_created_event_to_aws_sns(user_id: str, order: dict) -> None:
    try:
        sns_client = boto3.client('sns', region_name=os.environ["AWS_DEFAULT_REGION"])
        topic_arn = os.environ["AWS_ORDER_CREATED_SNS_TOPIC_ARN"]

        message_payload = {
            "user_email": user_id,
            "order_id": order["order_id"],
            "total": order["total"],
            "timestamp": order["timestamp"],
            "items": order["items"],
        }

        sns_client.publish(TopicArn=topic_arn, Message=json.dumps(message_payload), Subject="OrderCreated")
    except Exception as e:
        logging.error(f'os.environ["AWS_ORDER_CREATED_SNS_TOPIC_ARN"]: {os.environ["AWS_ORDER_CREATED_SNS_TOPIC_ARN"]}')
        logging.exception("Failed to publish order created event to SNS", e)


if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "5003")),
        workers=4,
        proxy_headers=True,  # to get real client IPs, not just the load balancer IP
        forwarded_allow_ips="*",  # trust requests from not just localhost, needed for ALB
    )
