import json
import logging
import os
import time
import uuid
from enum import Enum
from typing import Annotated, Literal

import boto3
import requests
import uvicorn
from aws_app_config import aws_app_config
from dotenv import load_dotenv
from fastapi import BackgroundTasks, Body, Cookie, Depends, FastAPI, Header, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, Field

load_dotenv()

app = FastAPI()
aws_app_config_client = aws_app_config.AWSAppConfig()
AUTH_SERVICE_URL = os.environ["AUTH_SERVICE_URL_REST_API"]

# which origins can request API - should only allow your frontend URLs
# ALLOWED_ORIGINS = [
#     "https://localhost.tiangolo.com",
#     "http://localhost",
#     "http://localhost:8080",
# ]

# * runs with every request before it is processed by any specific path operation, and with every response before returning it
app.add_middleware(
    CORSMiddleware,  # allows options below
    # allow_origins=[r"https://.*\.example\.com"],  # which origins can request API - should only allow your frontend URLs
    # allow_origin_regex=r"https://.*\.example\.com",  # which origins can request API - should only allow your frontend URLs
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],  # can add custom headers - `+= ["X-Request-ID", "X-CSRF-Token"]`
)

# * In-memory store: user_id -> {order_id -> order_data}
ORDERS: dict[str, dict[str, dict[str, any]]] = {  # type: ignore
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


# * Session verification dependency
async def get_user_id(
    request: Request,
    session_id: str | None = Cookie(default=None),
    x_user: str | None = Header(default=None),
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
        user_id = await verify_session(session_id)
    elif aws_app_config_client.get_config_api_gateway_authorizer_lambda_authorizer():
        user_id = x_user
    else:
        session_id = request.cookies.get("session_id")
        user_id = await verify_session(session_id)

    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    return user_id


async def verify_session(session_id: str | None) -> str | None:
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


UserId = Annotated[str, Depends(get_user_id)]


class OrderStatus(str, Enum):
    """Order status enum."""

    created = "created"
    shipped = "shipped"
    cancelled = "cancelled"


# * Pydantic models
class FilterParamsOrders(BaseModel):
    """Query parameters for filtering orders."""

    limit: int = Field(100, gt=0, le=100)
    offset: int = Field(0, ge=0)
    order_by: Literal["created_at", "updated_at"] = "created_at"
    tags: list[str] = []


class User(BaseModel):
    """User model."""

    email: EmailStr


class OrderCreate(BaseModel):
    """Order creation model."""

    model_config = {"extra": "forbid"}  # forbid extra fields not defined in the model when creating an order

    items: Annotated[
        list[str],
        Body(
            examples=[
                ["apple", "banana", "orange"],
                ["notebook", "pen"],
            ],
        ),
    ] = Field(
        description="items purchased - list of item names - will be replaced with Item model",
        min_items=1,  # type: ignore
        max_items=10,  # type: ignore
    )
    total: float = Field(description="total amount of the order", gt=0, examples=[35.4])


class OrderUpdate(BaseModel):
    """Order update model."""

    items: list[str] | None = None
    total: float | None = None
    status: OrderStatus | None = None


class OrderResponse(BaseModel):
    """Order response model."""

    order_id: str
    items: list[str]
    status: str
    total: float
    timestamp: int


class OrdersListResponse(BaseModel):
    """Response model for list of orders."""

    orders: list[OrderResponse]


def check_valid_status(status: str) -> str:
    """check if the status is valid."""
    allowed = [status.value for status in OrderStatus]
    if status not in allowed:
        raise ValueError(f"Status must be one of: {', '.join(allowed)}")
    return status


@app.get("/")
def index() -> JSONResponse:
    """
    Health check endpoint.

    Returns:
        JSONResponse: Health status.
    """
    return JSONResponse(status_code=status.HTTP_200_OK, content={"status": "ok"})


# * Endpoints
@app.get("/orders", response_model=OrdersListResponse)
def list_orders(user_id: UserId) -> OrdersListResponse:
    """
    Retrieve all orders for the authenticated user.

    Args:
        user_id (str): User ID obtained from authentication dependency.

    Returns:
        OrdersListResponse: List of orders.
    """
    return OrdersListResponse(orders=[OrderResponse(**order) for order in ORDERS.get(user_id, {}).values()])


@app.get("/orders/{order_id}", response_model=OrderResponse, response_model_exclude={"timestamp"})
def get_order(order_id: str, user_id: UserId) -> OrderResponse:
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return OrderResponse(**order)


@app.get("/orders/{order_id}/status", response_model=OrderResponse, deprecated=True)
def get_order_status(order_id: str, user_id: UserId) -> OrderResponse:
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    order_status = order.get("status")
    if not order_status:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid order status")

    return OrderStatus(order_status)


@app.post("/orders", status_code=status.HTTP_201_CREATED)
def create_order(
    order: OrderCreate,
    background_tasks: BackgroundTasks,
    user_id: UserId,
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
def update_order(order_id: str, update: OrderUpdate, user_id: UserId) -> OrderResponse:
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    for field in ["items", "status", "total"]:
        val = getattr(update, field)
        if val is not None:
            order[field] = val

    order["timestamp"] = int(time.time())
    return OrderResponse(**order)


@app.delete("/orders/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_order(order_id: str, user_id: UserId) -> JSONResponse:
    """
    Delete an existing order for the **authenticated** user.

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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    del user_orders[order_id]
    return JSONResponse(status_code=status.HTTP_204_NO_CONTENT, content=None)


def publish_order_created_event_to_aws_sns(user_id: str, order: dict) -> None:
    """publish order created event to AWS SNS topic."""
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
        logging.exception(f"Failed to publish order created event to SNS - {e}")


if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "5003")),
        workers=4,
        proxy_headers=True,  # to get real client IPs, not just the load balancer IP
        forwarded_allow_ips="*",  # trust requests from not just localhost, needed for ALB
    )
