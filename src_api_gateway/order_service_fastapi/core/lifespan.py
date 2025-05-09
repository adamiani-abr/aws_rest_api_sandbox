import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from core.config import get_settings
from fastapi import FastAPI

settings = get_settings()
logger = logging.getLogger(__name__)  # pulling logging config from the main app.py file


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator:
    """
    Application lifespan context.

    Runs on startup and shutdown of the FastAPI app.

    Startup:
      - Initialize external resources
      - Log startup events

    Shutdown:
      - Close resources
      - Log shutdown events
    """
    logger.info("Starting order_service")
    try:
        yield
    finally:
        logger.info("Stopping order_service")
