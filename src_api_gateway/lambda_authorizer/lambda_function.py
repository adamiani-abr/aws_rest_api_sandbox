import redis
import os

# REDIS_HOST = "sandbox-alex-elasticache-redis-pvt-sbnt-m6dcul.serverless.use1.cache.amazonaws.com"
# r = redis.Redis(host=REDIS_HOST, port=6379, decode_responses=False, )
redis_connection = redis.Redis(
    host=os.environ["REDIS_HOST"],
    port=int(os.getenv("REDIS_PORT", 6379)),
    # decode_responses=True,  # Redis responses returned as Python strings instead of raw bytes - for debugging
    decode_responses=False,  # Redis responses returned as raw bytes - must be False if trying to read session data
    socket_timeout=5,
    ssl=True,  # must be enabled if connecting to Redis in AWS ElastiCache
)


def lambda_handler(event={}, context={}):
    print(f"event: {event}")
    print(f"context: {context}")
    token = event.get("authorizationToken", "").replace("Bearer ", "")
    print(f"Auth token: {token}")

    if not token:
        raise Exception("Unauthorized")

    session_key = f"session:{token}"
    print(f"session_key: {session_key}")
    user = redis_connection.get(session_key)

    if user:
        user_str = user.decode("utf-8")
        print(f"user: {user_str}")

        return {
            "principalId": user_str,
            "policyDocument": {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Action": "execute-api:Invoke",
                        "Effect": "Allow",
                        "Resource": event["methodArn"],
                    }
                ],
            },
            "context": {"user": user_str},
        }

    raise Exception("Unauthorized")


# event = {
#     "key1": "value1",
#     "key2": "value2",
#     "key3": "value3",
#     "headers": {"Authorization": "Bearer 20bc0c3f-e487-4170-ac82-f8ce2e7a6c9a"},
#     "methodArn": "arn:aws:apigateway:us-east-1::/apis/hlzxgyshmc/dev/orders/get_order",
# }
# lambda_handler(event=event)
