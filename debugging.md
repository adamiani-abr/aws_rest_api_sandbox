# Debugging

## AWS ECS

### Enable `ecs exec` for ECS Service

Allows being able to `exec` into Docker container running on ECS Task under that ECS Service to run commands, like `telnet`, `ping`, etc.

```
aws ecs update-service \
  --cluster <CLUSTER_NAME> \
  --service <SERVICE_NAME> \
  --force-new-deployment \
  --enable-execute-command
```

### Exec into Docker container running on AWS ECS Task
```
aws ecs execute-command \
  --cluster <CLUSTER_NAME> \
  --task <TASK_ID> \
  --container <CONTAINER_NAME> \
  --command "/bin/sh" \
  --interactive
```

## Redis

* initiate connection to redis server - `redis-cli -h $REDIS_HOST -p 6379 --tls`
  * `--tls` needed when connecting to AWS Elasticache instance
* see keys currently stored on redis instance on Elasticache - `redis-cli -h <REDIS_HOST> -p <REDIS_PORT> --tls SCAN 0`
  * `redis-cli -h <REDIS_HOST> -p <REDIS_PORT> keys *` disabled on Elasticache
* flush all current key-value pairs - `redis-cli -h $REDIS_HOST -p 6379 --tls FLUSHALL`

## Setting Authentication Cookie

* fails if attempting to set in `auth service`
* must set in `web app service` for now
* may potentially be work-around after enabling `HTTPS` in production
