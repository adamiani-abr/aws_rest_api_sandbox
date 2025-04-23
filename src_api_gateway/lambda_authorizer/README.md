# sandbox-alex-rest-api-authorizer-lambda

Must pass authorization bearer token in requests:

```python
session_id = request.cookies.get("session_id")
headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {session_id}"
}

response = requests.get(f"{AWS_REST_API_URL}/orders", headers=headers)
```
