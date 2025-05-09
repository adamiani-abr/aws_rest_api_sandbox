import uvicorn
from core.config import get_settings
from core.logging_config import setup_logging
from fastapi import FastAPI
from middleware.cors import configure_cors
from routers.health import router as health_router
from routers.orders import router as orders_router

setup_logging()  # will setup logging across all files in the app - just need to import logging

settings = get_settings()  # load config settings from .env

app: FastAPI = FastAPI(title="OrderService", debug=settings.debug)

# * attach middleware
# configure_cors(app, settings.cors_origins)  # if passing in list of allowed origins for making requests to API
configure_cors(app)

# * include routers
app.include_router(health_router)
app.include_router(orders_router, prefix="/orders", tags=["orders"])


if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=settings.port,
        workers=4,
        proxy_headers=True,  # to get real client IPs, not just the load balancer IP
        forwarded_allow_ips="*",  # trust requests from not just localhost, needed for ALB
    )
