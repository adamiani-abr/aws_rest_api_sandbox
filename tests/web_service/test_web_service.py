from unittest.mock import patch


@patch("requests.post")
def test_login_redirect_on_invalid_session(mock_post, client):
    mock_post.return_value.status_code = 401
    res = client.get("/dashboard", follow_redirects=False)
    assert res.status_code == 302
    assert "/login" in res.headers["Location"]
