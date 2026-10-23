"""Web 路由测试：单页入口、/owner/repo 深链、修改清单最后一版持久化。"""

from types import SimpleNamespace

from fastapi.testclient import TestClient

from repo_seo.advice.optimize import OptimizeAction, OptimizePlan
from repo_seo.web import plan_store
from repo_seo.web.app import app

import repo_seo.web.app as web_app

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


def test_plan_store_last_version_wins(tmp_path):
    plan_store.save_last_plan("o", "r", {"summary": "v1"}, base=tmp_path)
    plan_store.save_last_plan("o", "r", {"summary": "v2"}, base=tmp_path)
    got = plan_store.load_last_plan("o", "r", base=tmp_path)
    assert got is not None
    assert got["plan"]["summary"] == "v2"
    assert got["owner"] == "o"
    assert got["at"]


def test_last_plan_endpoint_404_when_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(plan_store, "default_history_dir", lambda: tmp_path)
    resp = client.get("/api/optimize/last/no/suchrepo")
    assert resp.status_code == 404
    assert resp.headers["content-type"].startswith("application/json")


def test_last_plan_endpoint_returns_saved(tmp_path, monkeypatch):
    monkeypatch.setattr(plan_store, "default_history_dir", lambda: tmp_path)
    plan_store.save_last_plan(
        "linhaha-ai", "RepoRadar", {"summary": "s", "actions": [], "estimated_gain": 3}
    )
    resp = client.get("/api/optimize/last/linhaha-ai/RepoRadar")
    assert resp.status_code == 200
    data = resp.json()
    assert data["plan"]["summary"] == "s"
    assert data["plan"]["estimated_gain"] == 3
    assert data["at"]
    assert data["owner"] == "linhaha-ai"


def test_optimize_endpoint_persists_last_plan(tmp_path, monkeypatch):
    """回归：/api/optimize 成功后按 snapshot 键落盘（曾因 owner 未定义 500）。"""
    snap = SimpleNamespace(owner="o", name="r")
    monkeypatch.setattr(web_app, "_scan_for", lambda url: (snap, None))
    monkeypatch.setattr(web_app, "_make_llm", lambda: object())
    monkeypatch.setattr(
        web_app,
        "generate_optimize_plan",
        lambda s, r, l: OptimizePlan(
            summary="s",
            actions=[
                OptimizeAction(
                    type="readme", target="README.md", what="w", why="y", concrete="c"
                )
            ],
        ),
    )
    monkeypatch.setattr(plan_store, "default_history_dir", lambda: tmp_path)

    resp = client.post("/api/optimize", json={"url": "o/r"})
    assert resp.status_code == 200
    assert resp.json()["summary"] == "s"
    saved = plan_store.load_last_plan("o", "r", base=tmp_path)
    assert saved is not None
    assert saved["plan"]["summary"] == "s"
    assert saved["at"]
