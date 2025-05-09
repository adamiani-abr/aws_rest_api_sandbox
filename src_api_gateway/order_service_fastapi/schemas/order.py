from typing import List

from pydantic import BaseModel


class OrderCreate(BaseModel):
    """Order creation schema."""

    items: List[str]
    total: float


class OrderResponse(OrderCreate):
    """Order response schema."""

    order_id: str
    status: str = "created"
