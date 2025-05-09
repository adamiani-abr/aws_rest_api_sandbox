from pydantic import AnyHttpUrl, Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Settings for the application."""

    auth_service_url: AnyHttpUrl = Field(..., env="AUTH_SERVICE_URL")  # type: ignore
    aws_default_region: str = Field("us-east-1", env="AWS_DEFAULT_REGION")  # type: ignore
    aws_order_created_sns_topic_arn: str = Field(..., env="AWS_ORDER_CREATED_SNS_TOPIC_ARN")  # type: ignore

    env: str = Field("production", env="ENVIRONMENT")  # type: ignore
    debug: bool = Field(False, env="DEBUG")  # type: ignore
    port: int = Field(5003, env="PORT")  # type: ignore

    aws_app_config_app_id: str = Field(..., env="AWS_APP_CONFIG_APP_ID")  # type: ignore
    aws_app_config_env_id: str = Field(..., env="AWS_APP_CONFIG_ENV_ID")  # type: ignore
    aws_app_config_config_profile_id: str = Field(..., env="AWS_APP_CONFIG_CONFIG_PROFILE_ID")  # type: ignore
    aws_app_config_cache_ttl: int = Field(60, env="AWS_APP_CONFIG_CACHE_TTL")  # type: ignore

    aws_app_config_feature_flag_key_api_gateway_authorizer_auth_service: str = Field(  # type: ignore
        ..., env="AWS_APP_CONFIG_FEATURE_FLAG_KEY_API_GATEWAY_AUTHORIZER_AUTH_SERVICE"
    )
    aws_app_config_feature_flag_key_api_gateway_authorizer_lambda_authorizer: str = Field(  # type: ignore
        ..., env="AWS_APP_CONFIG_FEATURE_FLAG_KEY_API_GATEWAY_AUTHORIZER_LAMBDA_AUTHORIZER"
    )

    class Config:
        """Configuration for the settings."""

        env_file = ".env"
        env_file_encoding = "utf-8"
        validate_assignment = True


settings = Settings()  # type: ignore


def get_settings() -> Settings:
    """Get the application settings."""
    global settings
    if settings is None:
        settings = Settings()
    return settings
