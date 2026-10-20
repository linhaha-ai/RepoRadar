"""V2 外部验证层测试（google / aeo_probe / orchestrator / 报告集成）。"""

import pytest

from repo_seo.advice.llm import LLMError
from repo_seo.report import render_html, render_markdown, render_terminal
from repo_seo.scoring import score_snapshot
from repo_seo.verify.aeo_probe import _mentioned, probe_models
from repo_seo.verify.google import check_google_index
from repo_seo.verify.orchestrator import run_external_verification

from .fixtures import make_snapshot


# ---------- google ----------

def test_google_unknown_without_credentials():
    c = check_google_index("owner", "repo", None, None)
    assert c.status == "unknown"
    assert "未配置" in c.evidence


def test_google_parse_indexed(monkeypatch):
    class FakeResp:
        status_code = 200

        def json(self):
            return {
                "searchInformation": {"totalResults": "3"},
                "items": [{"link": "https://github.com/owner/repo"}],
            }

    monkeypatch.setattr("httpx.get", lambda *a, **k: FakeResp())
    c = check_google_index("owner", "repo", "k", "cse")
    assert c.status == "indexed"
    assert c.total_results == 3
    assert c.top_url == "https://github.com/owner/repo"


def test_google_parse_not_indexed(monkeypatch):
    class FakeResp:
        status_code = 200

        def json(self):
            return {"searchInformation": {"totalResults": "0"}, "items": []}

    monkeypatch.setattr("httpx.get", lambda *a, **k: FakeResp())
    c = check_google_index("owner", "repo", "k", "cse")
    assert c.status == "not_indexed"
    assert c.total_results == 0


def test_google_api_error(monkeypatch):
    class FakeResp:
        status_code = 500
        text = "boom"

    monkeypatch.setattr("httpx.get", lambda *a, **k: FakeResp())
    c = check_google_index("owner", "repo", "k", "cse")
    assert c.status == "error"


# ---------- aeo probe ----------

def test_mentioned_detection():
    assert _mentioned("Yes, RepoRadar is a GitHub SEO tool.", "linhaha-ai", "RepoRadar")
    assert _mentioned("I do not know this repository.", "linhaha-ai", "RepoRadar") is False
    assert _mentioned("I am not aware of it.", "linhaha-ai", "RepoRadar") is False
    assert _mentioned("No idea.", "linhaha-ai", "RepoRadar") is False
    assert _mentioned("RepoRadar helps with SEO.", "linhaha-ai", "RepoRadar")


def test_probe_models_ok():
    class FakeLLM:
        model = "m1"
        api_key = "k"
        base_url = "http://x"
        timeout = 30

        def chat_text(self, system, user, temperature=0.0):
            return "Yes, I know linhaha-ai/RepoRadar, a GitHub SEO tool."

    probes = probe_models(FakeLLM(), "linhaha-ai", "RepoRadar", "desc", ["m1"])
    assert len(probes) == 1
    assert probes[0].mentioned is True
    assert probes[0].status == "done"


def test_probe_models_error():
    class BoomLLM:
        model = "m1"
        api_key = "k"
        base_url = "http://x"
        timeout = 30

        def chat_text(self, system, user, temperature=0.0):
            raise LLMError("boom")

    probes = probe_models(BoomLLM(), "owner", "repo", None, ["m1"])
    assert probes[0].status == "error"
    assert probes[0].mentioned is False


# ---------- orchestrator ----------

def test_run_verification_without_llm():
    s = make_snapshot()
    v = run_external_verification(s, llm=None)
    assert v.google.status == "unknown"
    assert v.probes == []
    assert any("未配置 LLM" in n for n in v.notes)
    d = v.to_dict()
    assert d["google"]["status"] == "unknown"
    assert "ran_at" in d


# ---------- 报告集成 ----------

def test_reports_include_verification():
    s = make_snapshot()
    report = score_snapshot(s)
    v = run_external_verification(s, llm=None)
    term = render_terminal(report, s, verification=v)
    assert "外部验证证据" in term
    assert "Google 收录" in term
    md = render_markdown(report, s, verification=v)
    assert "外部验证证据（Search Visibility Evidence · V2）" in md
    html = render_html(report, s, verification=v)
    assert "外部验证证据" in html
    assert "Google 收录" in html
