from clients.auth_client import AuthClient
from clients.aws_app_config_client import AWSAppConfigClient
from fastapi import Cookie, Header, HTTPException, Request, status

aws_app_config_client = AWSAppConfigClient()
auth_client = AuthClient()


async def get_current_user(
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
        user_id = await auth_client.verify_session(session_id)
    elif aws_app_config_client.get_config_api_gateway_authorizer_lambda_authorizer():
        user_id = x_user
    else:
        session_id = request.cookies.get("session_id")
        user_id = await auth_client.verify_session(session_id)

    print(f"User ID: {user_id}")

    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    return user_id
