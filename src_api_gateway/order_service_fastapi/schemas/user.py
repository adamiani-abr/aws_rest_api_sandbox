from pydantic import BaseModel


class TokenData(BaseModel):
    """Token data schema."""

    user_id: str
