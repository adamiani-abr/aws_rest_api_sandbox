from dependencies import get_current_user
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from schemas.order import OrderCreate, OrderResponse
from services.notifications import NotificationService
from services.orders import create_order, delete_order, get_order, list_orders, update_order

router = APIRouter()
notification_service = NotificationService()


@router.post("/", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_user_order(
    order: OrderCreate,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user),
) -> OrderResponse:
    """
    Create a new order for the authenticated user.

    Schedules an SNS notification in the background once the order is created.

    Args:
        order (OrderCreate): Payload containing items and total amount.
        background_tasks (BackgroundTasks): FastAPI background task manager.
        user_id (str): Authenticated user's ID, injected by dependency.

    Returns:
        OrderResponse: The newly created order, including generated `order_id` and `timestamp`.
    """
    result = create_order(order, user_id)
    # * schedule publishing to sns in the background
    background_tasks.add_task(
        notification_service.publish_order_created,
        result,
        user_id,
    )
    return result


@router.get("/", response_model=list[OrderResponse])
async def get_user_orders(
    user_id: str = Depends(get_current_user),
) -> list[OrderResponse]:
    """
    Retrieve all orders belonging to the authenticated user.

    Args:
        user_id (str): Authenticated user's ID, injected by dependency.

    Returns:
        list[OrderResponse]: A list of the user's existing orders.
    """
    return list_orders(user_id)


@router.get("/{order_id}", response_model=OrderResponse)
async def get_user_order(
    order_id: str,
    user_id: str = Depends(get_current_user),
) -> OrderResponse:
    """
    Retrieve a single order by its ID for the authenticated user.

    Args:
        order_id (str): The unique identifier of the order to fetch.
        user_id (str): Authenticated user's ID, injected by dependency.

    Raises:
        HTTPException (404): If no order with `order_id` exists for this user.

    Returns:
        OrderResponse: The requested order details.
    """
    order = get_order(order_id, user_id)
    if not order:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Order not found")
    return order


@router.put("/{order_id}", response_model=OrderResponse)
async def update_user_order(
    order_id: str,
    order: OrderCreate,
    user_id: str = Depends(get_current_user),
) -> OrderResponse:
    """
    Update an existing order for the authenticated user.

    Args:
        order_id (str): The unique identifier of the order to update.
        order (OrderCreate): Payload with updated items and total.
        user_id (str): Authenticated user's ID, injected by dependency.

    Raises:
        HTTPException (404): If no order with `order_id` exists for this user.

    Returns:
        OrderResponse: The updated order details.
    """
    updated = update_order(order_id, order, user_id)
    if not updated:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Order not found")
    return updated


@router.delete("/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_order(
    order_id: str,
    user_id: str = Depends(get_current_user),
) -> None:
    """
    Delete an existing order for the authenticated user.

    Args:
        order_id (str): The unique identifier of the order to delete.
        user_id (str): Authenticated user's ID, injected by dependency.

    Raises:
        HTTPException (404): If no order with `order_id` exists for this user.

    Returns:
        None: Returns HTTP 204 No Content on success.
    """
    success = delete_order(order_id, user_id)
    if not success:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Order not found")
