# aws_elasticache_redis

## Web Front-End

* deployed via AWS ECS Service (API Gateway routes also point to separate ECS Services)
* is not routable via the API Gateway
* is accessible via ALB
* needs separate validator, as API Gateway will use lambda authorizer

## Redis

* `redis` is used to store the user sessions so they will persist across updates of the microservices
  * example: need to udpate ECS Fargate web service, the user sessions will perists after new ECS Service task is deployed

### Verifying `redis` Container Session Keys

#### Locally

##### Redis Commands

* `docker-ps` to get container name of `redis` container
* `docker exec -it {redis_container_name} redis-cli`
* `keys *`

#### AWS

##### Prerequisites

* [AWS CLI installed](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)
* [AWS Session Manager for CLI installed](https://s3.amazonaws.com/session-manager-downloads/plugin/latest/windows/SessionManagerPluginSetup.exe)

##### AWS Commands for Redis

* `aws ecs update-service --cluster <CLUSTER> --service <SERVICE> --force-new-deployment --enable-execute-command`
  * enable `ecs exec` for AWS service if not already enabled
  * verify `enableExecuteCommand=True` - `aws ecs describe-tasks --cluster <CLUSTER> --tasks <TASK_ARN>`
* `aws ecs execute-command --cluster <CLUSTER> --task {TASK_ID} --container {CONTAINER_NAME} --command "/bin/sh" --interactive`
* `redis-cli`
* `keys *`

## AWS API Gateway

### HTTP API

* route to ECS Services with routes as: `/<route_name>/{proxy+}` where `{proxy+}` will map all requests and subrequests to the integration endpoint.
  * `/auth/login`, `/auth/login/{user_id}`, etc.
* `Integrations`
  * `Integration target` = `Private Resource`
  * `Integration details` = `Cloud Map`
* `VPC Link` - same private subnets used for ECS Services

#### Accessing via Private Resources

* for example, ECS Fargate services without public IPs and in private subnets
* for the VPC Endpoint must set `Private DNS names enabled = No`
  * private REST APIs require `Private DNS names enabled = Yes` though, so if developing both need **2 VPC Endpoints**

#### HTTP API - Potential Issues

* when routing requests to ECS Services, it will keep the entire path from API Gateway
  * ex: `/auth/login` is routed to the ECS Service
  * if the ECS Service isn't setup with the prepended value it will fail with `404` errors
  * to resolve this, in the `Integrations` section for that route, add a `Parameter Mapping`
    * `Parameter to modify` = `path`
    * `Modification type` = `Overwrite`
    * `Value` = `/$request.path.proxy`
      * even though AWS suggests `$request.path`, it will fail with `400` errors if you don't have the leading slash
        * [SO Reference](https://stackoverflow.com/questions/70402300/aws-api-gateway-cannot-rewrite-path-400-bad-request-error)

### REST API

* [Tutorial: Create a REST API with a private integration](https://docs.aws.amazon.com/apigateway/latest/developerguide/getting-started-with-private-integration.html)
* Have to create:
  * `VPC Endpoint` - for calling your private API from within a VPC
    * enables private DNS resolution for *.execute-api.amazonaws.com inside your VPC
    * `Private DNS names enabled` must be set to `Yes` so private DNS names can be resolved by private AWS services
      * HTTP APIs need `Private DNS names enabled = No` because only public option available
  * `VPC Link` - for API Gateway to connect to private services in your VPC
    * enables API Gateway to be able to forward requests to private services (EC2, ECS, NLB, etc.)
* If creating `{proxy}` resource, the `Integration Request` `Endpoint URL` of the route must also be terminated with `proxy`
  * example: `http://sandbox...-3fea....3.elb.us-east-1.amazonaws.com/{proxy}`
  * the `Endpoint URL` will be the URL of the `NLB` with the private service (example: `Fargate`) in the registered targets
* For stage, create `Stage Variable` `vpcLinkId` and set to `VPC Link ID` created earlier

#### VPC Endpoint

* `Service category`: `AWS services`
* `Service Name`: `com.amazonaws.<region>.execute-api`
* `VPC`: `your VPC`
* `Subnets`: `private subnets that need access`

#### Network Load Balancer (NLB)

* needed for the `VPC Link`
* encouraged to set `Enforce inbound rules on PrivateLink traffic` to `Off`
  * allows API Gateway traffic to reach the NLB without needing explicit inbound rules from API Gateway’s source IP range
* if using more than one AZ for NLB, then must ensure one or both:
  * NLB `Cross-zone load balancing` is set to `On`
    * [allow traffic distribution across all Availability Zones](https://docs.aws.amazon.com/elasticloadbalancing/latest/network/network-load-balancers.html#cross-zone-load-balancing)
  * target is registered in each of the AZs assigned to the NLB Target Group
    * ensure request handling capability across your NLB's entire deployment area

#### Resource - Method Request - HTTP Headers

* have to add `Cookie` if passing `session_id` via a Cookie

#### Resource Policy

example

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Deny",
      "Principal": "*",
      "Action": "execute-api:Invoke",
      "Resource": "arn:aws:execute-api:us-east-1:<aws_account_id>:<rest_api_gateway_id>/*",
      "Condition": {
        "StringNotEquals": {
          "aws:SourceVpc": "<vpc_id>"
        }
      }
    },
    {
      "Effect": "Allow",
      "Principal": "*",
      "Action": "execute-api:Invoke",
      "Resource": "arn:aws:execute-api:us-east-1:<aws_account_id>:<rest_api_gateway_id>/*"
    }
  ]
}
```

#### Returning Status Codes Not 200

* API Gateway has built-in for error codes, but not for success status codes (ex: `201`)
* Must create custom success status code in API Gateway
  * API Gateway > Resources > select Route
    * `Method Response` > `Create Response` > `HTTP status code`
      * nothing else needed
    * `Integration Response` > `Create Response`
      * Select `Method Response` just created
      * `HTTP status regex` - success status code (ex: `201`)
      * `Mapping templates`

```json
#set($resp = $input.json('$'))
#set($context.responseOverride.status = $resp.statusCode)
$resp.body
```

## ECS

### ECS Service Setup

#### ECS Service Connect

* each ECS Service should be setup with the `Client and Server` option, not the ~~`Client Side Only`~~ option
  * to be able to be mapped to in API Gateway in Integrations, there has to be an internally publicized `port mapping`

## Setup Stages

### V1

* no API Gateway
* two ECS Services and Tasks in single ECS Cluster
  * two services:
    * `web app`
    * `authorization`
  * use ECS Service Connnect for `web app` to send requests to `authorization`
  * both services in **private** subnet
* Elasticache Redis cluster to store user sessions
  * in **private** subnet
* ALB attached to `web app` with public DNS A record
  * cookies stored at ALB DNS A record level to persist rolling updates of `web app`

### V2
