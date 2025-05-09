import requests
from core.config import get_settings


class AuthClient:
    """Client for interacting with the authentication service."""

    def __init__(self) -> None:
        settings = get_settings()
        self.__auth_service_url = settings.auth_service_url

    async def verify_session(self, session_id: str | None) -> str | None:
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
            response = requests.post(
                f"{self.__auth_service_url}/verify", json={"session_id": session_id}, headers=headers, timeout=3
            )

            if response.status_code == 200:
                return response.json().get("user", {}).get("email")
        except requests.RequestException:
            pass
        return None
