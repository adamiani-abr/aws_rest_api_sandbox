import time
from typing import Any
from uuid import uuid4

from schemas.order import OrderCreate, OrderResponse

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


def create_order(order: OrderCreate, user_id: str) -> OrderResponse:
    """
    Create a new order and store it in the in-memory database.

    INPUT:
    - order: OrderCreate object containing order details.
    - user_id: ID of the user creating the order.

    RETURN:
    - OrderResponse object containing the created order details.
    """
    order_id = str(uuid4())
    new_order = {
        "order_id": order_id,
        "items": order.items,
        "status": "created",
        "total": order.total,
        "timestamp": int(time.time()),
    }
    ORDERS.setdefault(user_id, {})[order_id] = new_order
    return OrderResponse(**new_order)


def list_orders(user_id: str) -> list[OrderResponse]:
    """
    List all orders for a given user.

    INPUT:
    - user_id: ID of the user whose orders are to be listed.

    RETURN:
    - List of OrderResponse objects containing the details of each order.
    """
    return list(ORDERS.get(user_id, {}).values())


def get_order(order_id: str, user_id: str) -> OrderResponse | None:
    """
    Retrieve a specific order for a given user.

    INPUT:
    - order_id: ID of the order to retrieve.
    - user_id: ID of the user whose order is to be retrieved.

    RETURN:
    - OrderResponse object containing the order details, or None if not found.
    """
    return ORDERS.get(user_id, {}).get(order_id)


def update_order(order_id: str, order_update: OrderCreate, user_id: str) -> OrderResponse | None:
    """
    Update an existing order for a given user.

    INPUT:
    - order_id: ID of the order to update.
    - order_update: OrderCreate object containing the updated order details.
    - user_id: ID of the user whose order is to be updated.

    RETURN:
    - OrderResponse object containing the updated order details, or None if not found.
    """
    if order_existing := ORDERS.get(user_id, {}).get(order_id):
        order_final: dict = order_existing.copy()
        order_final.update(order_update.model_dump())
        ORDERS[user_id][order_id] = order_final
        return order_final
    return None


def delete_order(order_id: str, user_id: str) -> str | Any:
    """
    Delete an existing order for a given user.

    INPUT:
    - order_id: ID of the order to delete.
    - user_id: ID of the user whose order is to be deleted.

    RETURN:
    - The deleted order ID, or None if not found.
    """
    return ORDERS.get(user_id, {}).pop(order_id)
