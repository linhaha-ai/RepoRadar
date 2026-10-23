"""Web 路由测试：单页入口与 /owner/repo 深链。"""

from fastapi.testclient import TestClient

from repo_seo.web.app import app

client = TestClient(app)


def test_index_serves_spa():
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/html")
    assert "RepoRadar" in resp.text


def test_deep_link_serves_spa():
    resp = client.get("/linhaha-ai/AgentWriter")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/html")
    assert "RepoRadar" in resp.text


def test_deep_link_reserved_prefix_404_json():
    resp = client.get("/api/nope")
    assert resp.status_code == 404
    assert resp.headers["content-type"].startswith("application/json")


def test_deep_link_invalid_chars_404():
    resp = client.get("/foo/ba$r")
    assert resp.status_code == 404
    assert resp.headers["content-type"].startswith("application/json")
