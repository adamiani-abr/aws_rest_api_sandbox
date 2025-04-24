def test_login_success(client):
    res = client.post("/login", json={"username": "admin", "password": "password123"})
    assert res.status_code == 200
    assert "session_id" in res.json


def test_login_fail(client):
    res = client.post("/login", json={"username": "admin", "password": "wrong"})
    assert res.status_code == 401
