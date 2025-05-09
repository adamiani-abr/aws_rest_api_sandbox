import json
import logging

import boto3
from core.config import get_settings
from schemas.order import OrderResponse

logger = logging.getLogger(__name__)  # pulling logging config from the main app.py file


class NotificationService:
    """Service to publish notifications to AWS SNS."""

    def __init__(self) -> None:
        settings = get_settings()
        self.__aws_sns_client = boto3.client("sns", region_name=settings.aws_default_region)
        self.__aws_order_created_sns_topic_arn = settings.aws_order_created_sns_topic_arn

    def publish_order_created(self, order: OrderResponse, user_id: str) -> None:
        """
        Publishes an order-created event to AWS SNS.

        INPUT:
        - order: OrderResponse object containing order details.
        - user_id: ID of the user who created the order.
        """
        message = {
            "order_id": order.order_id,
            "user_id": user_id,
            "items": order.items,
            "total": order.total,
        }
        payload = json.dumps(message)

        logger.info(
            "Publishing order-created event",
            extra={"order_id": order.order_id, "user_id": user_id},
        )

        try:
            resp = self.__aws_sns_client.publish(
                TopicArn=self.__aws_order_created_sns_topic_arn,
                Message=payload,
            )
            logger.debug(
                "SNS publish response",
                extra={"message_id": resp.get("MessageId")},
            )
        except Exception as e:
            logger.error(
                "Failed to publish SNS message",
                exc_info=e,
                extra={"order_id": order.order_id, "user_id": user_id},
            )
