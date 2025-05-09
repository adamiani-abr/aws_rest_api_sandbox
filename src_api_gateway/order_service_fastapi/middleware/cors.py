# ***************************************************************** #
# middleware - runs with every request before it is processed by any specific path operation,
# and with every response before returning it
# ***************************************************************** #


from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# which origins can request API - should only allow your frontend URLs
# ALLOWED_ORIGINS = [
#     "https://localhost.tiangolo.com",
#     "http://localhost",
#     "http://localhost:8080",
# ]


# def configure_cors(app: FastAPI, origins: list[str]) -> None:
def configure_cors(app: FastAPI) -> None:
    """Configure CORS for the FastAPI application."""
    app.add_middleware(
        CORSMiddleware,  # allows options below
        # allow_origins=[r"https://.*\.example\.com"],
        # allow_origin_regex=r"https://.*\.example\.com",
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],  # can add custom headers - `+= ["X-Request-ID", "X-CSRF-Token"]`
    )
