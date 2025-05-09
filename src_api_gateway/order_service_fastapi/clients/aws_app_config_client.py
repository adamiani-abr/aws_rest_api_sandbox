from aws_app_config.aws_app_config import AWSAppConfig
from core.config import get_settings


class AWSAppConfigClient:
    """Client for interacting with AWS AppConfig."""

    def __init__(self) -> None:
        settings = get_settings()
        self.__client = AWSAppConfig(
            app_id=settings.aws_app_config_app_id,  # replace with real IDs
            env_id=settings.aws_app_config_env_id,
            config_profile_id=settings.aws_app_config_config_profile_id,
            ttl=settings.aws_app_config_cache_ttl,
        )
        self.__aws_app_config_feature_flag_key_api_gateway_authorizer_auth_service = (
            settings.aws_app_config_feature_flag_key_api_gateway_authorizer_auth_service
        )
        self.__aws_app_config_feature_flag_key_api_gateway_authorizer_lambda_authorizer = (
            settings.aws_app_config_feature_flag_key_api_gateway_authorizer_lambda_authorizer
        )

    def get_config_value_by_key(self, key: str) -> str | None:
        """
        Retrieves a specific key's value from the configuration.
        :param config_name: Name of the configuration to retrieve.
        :param key: Key whose value is to be retrieved.
        :return: Value associated with the key in the configuration.
        """
        config = self.__client.get_flags()
        if config and key in config:
            return config[key]
        return None

    def get_config_api_gateway_authorizer_ecs_auth_service(self) -> str | None:
        """
        Retrieves the configuration from AWS AppConfig.
        :param config_name: Name of the configuration to retrieve.
        :return: Configuration data as a dictionary.
        """
        return self.get_config_value_by_key(self.__aws_app_config_feature_flag_key_api_gateway_authorizer_auth_service)

    def get_config_api_gateway_authorizer_lambda_authorizer(self) -> str | None:
        """
        Retrieves the configuration from AWS AppConfig.
        :param config_name: Name of the configuration to retrieve.
        :return: Configuration data as a dictionary.
        """
        return self.get_config_value_by_key(self.__aws_app_config_feature_flag_key_api_gateway_authorizer_lambda_authorizer)
