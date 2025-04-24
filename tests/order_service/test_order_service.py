from unittest.mock import patch


@patch("app.verify_session", return_value="admin")
def test_create_order(mock_verify, client):
    res = client.post("/orders", json={"items": ["apple"], "total": 3.5})
    assert res.status_code == 201
    assert "order_id" in res.json


@patch("app.verify_session", return_value=None)
def test_unauthorized_order_access(mock_verify, client):
    res = client.get("/orders")
    assert res.status_code == 401
