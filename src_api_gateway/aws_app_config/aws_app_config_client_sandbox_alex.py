import os

from aws_app_config_client import AWSAppConfigClient
from dotenv import load_dotenv

load_dotenv()


class AWSAppConfigClientSandboxAlex(AWSAppConfigClient):
    __AWS_APP_CONFIG_APP_ID = os.environ["AWS_APP_CONFIG_APP_ID"]
    __AWS_APP_CONFIG_ENV_ID = os.environ["AWS_APP_CONFIG_ENV_ID"]
    __AWS_APP_CONFIG_CONFIG_PROFILE_ID = os.environ["AWS_APP_CONFIG_CONFIG_PROFILE_ID"]
    __AWS_APP_CONFIG_CACHE_TTL = int(os.environ.get("AWS_APP_CONFIG_CACHE_TTL", 60))
    __AWS_APP_CONFIG_FEATURE_FLAG_KEY_API_GATEWAY_AUTHORIZER_AUTH_SERVICE = (
        os.environ.get(
            "AWS_APP_CONFIG_FEATURE_FLAG_KEY_API_GATEWAY_AUTHORIZER_AUTH_SERVICE",
        )
    )
    __AWS_APP_CONFIG_FEATURE_FLAG_KEY_API_GATEWAY_AUTHORIZER_ECS_LAMBDA_AUTHORIZER = (
        os.environ.get(
            "AWS_APP_CONFIG_FEATURE_FLAG_KEY_API_GATEWAY_AUTHORIZER_LAMBDA_AUTHORIZER",
        )
    )

    def __init__(self):
        """
        Initializes the AppConfig client with caching.
        :param app_id: AWS AppConfig Application ID.
        :param env_id: AWS AppConfig Environment ID.
        :param config_profile_id: AWS AppConfig Configuration Profile ID.
        :param ttl: Time-to-live for cache in seconds.
        """
        super().__init__(
            AWSAppConfigClientSandboxAlex.__AWS_APP_CONFIG_APP_ID,
            AWSAppConfigClientSandboxAlex.__AWS_APP_CONFIG_ENV_ID,
            AWSAppConfigClientSandboxAlex.__AWS_APP_CONFIG_CONFIG_PROFILE_ID,
            AWSAppConfigClientSandboxAlex.__AWS_APP_CONFIG_CACHE_TTL,
        )

    def get_config_value_by_key(self, key: str) -> str:
        """
        Retrieves a specific key's value from the configuration.
        :param config_name: Name of the configuration to retrieve.
        :param key: Key whose value is to be retrieved.
        :return: Value associated with the key in the configuration.
        """
        config = self.get_flags()
        if config and key in config:
            return config[key]
        return None

    def get_config_api_gateway_authorizer_ecs_auth_service(self) -> dict:
        """
        Retrieves the configuration from AWS AppConfig.
        :param config_name: Name of the configuration to retrieve.
        :return: Configuration data as a dictionary.
        """
        return self.get_config_value_by_key(
            AWSAppConfigClientSandboxAlex.__AWS_APP_CONFIG_FEATURE_FLAG_KEY_API_GATEWAY_AUTHORIZER_AUTH_SERVICE,
        )

    def get_config_api_gateway_authorizer_lambda_authorizer(self) -> dict:
        """
        Retrieves the configuration from AWS AppConfig.
        :param config_name: Name of the configuration to retrieve.
        :return: Configuration data as a dictionary.
        """
        return self.get_config_value_by_key(
            AWSAppConfigClientSandboxAlex.__AWS_APP_CONFIG_FEATURE_FLAG_KEY_API_GATEWAY_AUTHORIZER_ECS_LAMBDA_AUTHORIZER,
        )
