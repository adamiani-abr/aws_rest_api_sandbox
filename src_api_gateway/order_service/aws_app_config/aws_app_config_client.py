import json
import logging
import time

import boto3

# Configure logging for debugging
logging.basicConfig(level=logging.INFO)


class AWSAppConfigClient:
    def __init__(self, app_id, env_id, config_profile_id, ttl=60):
        """
        Initializes the AppConfig client with caching.
        :param app_id: AWS AppConfig Application ID.
        :param env_id: AWS AppConfig Environment ID.
        :param config_profile_id: AWS AppConfig Configuration Profile ID.
        :param ttl: Time-to-live for cache in seconds.
        """
        self.app_id = app_id
        self.env_id = env_id
        self.config_profile_id = config_profile_id
        self.ttl = ttl
        self.last_fetched = 0
        self.flags = {}
        self.client = boto3.client("appconfigdata")
        self.configuration_token = None

    def _start_configuration_session(self):
        """
        Starts a new configuration session and obtains the initial token.
        """
        logging.info("Starting new AppConfig configuration session")
        response = self.client.start_configuration_session(
            ApplicationIdentifier=self.app_id,
            EnvironmentIdentifier=self.env_id,
            ConfigurationProfileIdentifier=self.config_profile_id,
        )
        self.configuration_token = response.get("InitialConfigurationToken")
        return self.configuration_token

    def _fetch_configuration(self):
        """
        Uses the configuration token to fetch the latest configuration.
        Updates the internal cache if new configuration is retrieved.
        """
        # Ensure we have a valid token
        if not self.configuration_token:
            self._start_configuration_session()

        print("Fetching latest AppConfig configuration")
        response = self.client.get_latest_configuration(
            ConfigurationToken=self.configuration_token
        )

        # 'Configuration' is a streaming body that needs to be read.
        config_data = response.get("Configuration").read()
        if config_data:
            try:
                # * {'api_gateway_authorizer_ecs_auth_service': {'enabled': False}, '...': {'enabled': True}, ...}
                config_json = json.loads(config_data)

                # * {'api_gateway_authorizer_ecs_auth_service': False, '...': True, ...}
                self.flags = {k: v["enabled"] for k, v in config_json.items()}

                self.last_fetched = time.time()
                # print("AppConfig configuration updated: %s", self.flags)
            except json.JSONDecodeError as e:
                logging.error("Error decoding AppConfig configuration: %s", e)
        else:
            # print("No new configuration data received.")
            pass

    def get_flags(self):
        """
        Returns the cached feature flags, fetching from AppConfig if needed.
        """
        current_time = time.time()
        if (current_time - self.last_fetched) > self.ttl:
            self._fetch_configuration()
        return self.flags
