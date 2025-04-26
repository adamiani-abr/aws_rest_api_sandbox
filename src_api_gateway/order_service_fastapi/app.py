import os
import time
import uuid
from typing import Any, Dict, List, Optional

import requests
import uvicorn
from aws_app_config.aws_app_config_client_sandbox_alex import AWSAppConfigClientSandboxAlex
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# * Load environment variables
load_dotenv(dotenv_path="src_api_gateway/.env")

app = FastAPI()
aws_app_config_client = AWSAppConfigClientSandboxAlex()
AUTH_SERVICE_URL = os.environ["AUTH_SERVICE_URL_REST_API"]

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
def get_user_id(session_id: Optional[str] = None, x_user: Optional[str] = Header(None), request: Request = None) -> str:
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
def list_orders(user_id: str = Depends(get_user_id)):
    return {'orders': list(ORDERS.get(user_id, {}).values())}


@app.get("/orders/{order_id}", response_model=OrderResponse)
def get_order(order_id: str, user_id: str = Depends(get_user_id)):
    order = ORDERS.get(user_id, {}).get(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@app.post("/orders", status_code=201)
def create_order(order: OrderCreate, user_id: str = Depends(get_user_id)):
    order_id = str(uuid.uuid4())
    new_order = {
        "order_id": order_id,
        "items": order.items,
        "status": "created",
        "total": order.total,
        "timestamp": int(time.time()),
    }
    ORDERS.setdefault(user_id, {})[order_id] = new_order
    return {"order_id": order_id, "message": "Order created"}


@app.put("/orders/{order_id}", response_model=OrderResponse)
def update_order(order_id: str, update: OrderUpdate, user_id: str = Depends(get_user_id)):
    user_orders = ORDERS.get(user_id, {})
    order = user_orders.get(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    for field in {"items", "status", "total"}:
        val = getattr(update, field)
        if val is not None:
            order[field] = val

    order["timestamp"] = int(time.time())
    return order


@app.delete("/orders/{order_id}", status_code=204)
def delete_order(order_id: str, user_id: str = Depends(get_user_id)):
    user_orders = ORDERS.get(user_id, {})
    if order_id not in user_orders:
        raise HTTPException(status_code=404, detail="Order not found")
    del user_orders[order_id]
    return JSONResponse(status_code=204, content=None)


if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "5003")),
        workers=4,
        proxy_headers=True,  # to get real client IPs, not just the load balancer IP
        forwarded_allow_ips="*",  # trust requests from not just localhost, needed for ALB
    )
