import pytest

pytestmark = pytest.mark.asyncio


async def test_security_headers_on_api(api_client):
    resp = await api_client.get("/api/v1/health")

    assert resp.headers["x-content-type-options"] == "nosniff"
    assert resp.headers["x-frame-options"] == "DENY"
    assert resp.headers["referrer-policy"] == "no-referrer"
    assert "camera=(), microphone=(), geolocation=()" in resp.headers["permissions-policy"]
    assert "frame-ancestors 'none'" in resp.headers["content-security-policy"]
    # api-ответы не кэшируются
    assert resp.headers["cache-control"] == "no-store"


async def test_mutating_request_with_foreign_origin_rejected(api_client):
    resp = await api_client.post(
        "/api/v1/auth/logout",
        headers={"origin": "https://evil.example"},
    )
    assert resp.status_code == 403


async def test_mutating_request_with_same_origin_allowed(api_client):
    # origin совпадает с хостом запроса -> тот же источник
    resp = await api_client.post("/api/v1/auth/logout", headers={"origin": "http://test"})
    assert resp.status_code in (204, 401)  # без сессии 401 но не 403

    resp = await api_client.post(
        "/api/v1/auth/logout", headers={"origin": "http://localhost:3000"}
    )
    assert resp.status_code in (204, 401)


async def test_rate_limit_kicks_in(api_client):
    from app.rate_limit import limiter

    limiter.enabled = True
    try:
        saw_429 = False
        for _ in range(12):
            resp = await api_client.get("/api/v1/auth/google/start")
            if resp.status_code == 429:
                saw_429 = True
                break
        assert saw_429, "лимит 10 в минуту должен сработать"
    finally:
        limiter.reset()
        limiter.enabled = False
