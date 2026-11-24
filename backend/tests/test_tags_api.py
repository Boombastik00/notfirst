async def test_tag_groups_returned(api_client):
    resp = await api_client.get("/api/v1/tag-groups")

    assert resp.status_code == 200
    codes = [group["code"] for group in resp.json()]
    assert "obstacles" in codes
    assert "professions" in codes
    # отсортированы по sort_order
    orders = [group["sort_order"] for group in resp.json()]
    assert orders == sorted(orders)


async def test_tags_filtered_by_group(api_client):
    resp = await api_client.get("/api/v1/tags", params={"group": "professions"})

    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 15
    assert all(item["group_code"] == "professions" for item in items)


async def test_tags_obstacles_have_parent_child(api_client):
    resp = await api_client.get("/api/v1/tags", params={"group": "obstacles"})

    assert resp.status_code == 200
    items = resp.json()
    assert any(item["parent_id"] is None for item in items)
    assert any(item["parent_id"] is not None for item in items)


async def test_tags_unknown_group_404(api_client):
    resp = await api_client.get("/api/v1/tags", params={"group": "no-such-group"})

    assert resp.status_code == 404


async def test_tags_without_group_returns_all(api_client):
    resp = await api_client.get("/api/v1/tags")

    assert resp.status_code == 200
    items = resp.json()
    group_codes = {item["group_code"] for item in items}
    assert len(group_codes) == 8
