import pytest

pytestmark = pytest.mark.asyncio


async def test_honeypot_rickrolls_attack_probes(api_client):
    # классические проны сканеров получают пасхалку, а не стандартный 404/500
    probes = [
        "/api/v1/../../etc/passwd",
        "/api/v1/u/search?q=' OR 1=1--",
        "/api/v1/stories?q=<script>alert(1)</script>",
        "/.env",
        "/wp-login.php",
        "/api/v1/stories?q=union select",
        "/api/v1/x?sleep(5)",
    ]
    for path in probes:
        resp = await api_client.get(path)
        assert resp.status_code == 403, path
        assert "эй, отстань" in resp.text, path
        assert "youtube.com" in resp.text, path


async def test_honeypot_ignores_normal_traffic(api_client):
    # обычные запросы не задеваются: ни поиск, ни словари, ни истории
    normal = [
        "/api/v1/tags",
        "/api/v1/stories?q=космос",
        "/api/v1/u/search?q=мила",
        "/api/v1/stories?q=sleeping%20beauty",
        "/api/v1/auth/me",
    ]
    for path in normal:
        resp = await api_client.get(path)
        assert resp.status_code != 403, path
        assert "эй, отстань" not in resp.text, path


async def test_search_survives_null_byte(api_client):
    # postgres не принимает \x00 в строках — поиск чистит управляющие символы
    resp = await api_client.get("/api/v1/stories?q=%00")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data

    # и в поиске аккаунтов тоже
    resp = await api_client.get("/api/v1/u/search?q=%00")
    assert resp.status_code in {200, 422}
    if resp.status_code == 200:
        assert resp.json() == []
