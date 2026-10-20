"""趋势监控测试（history / trend / report）。"""

from datetime import datetime, timedelta

import pytest

from repo_seo.trend.history import (
    DimensionSnapshot,
    HistoryStore,
    SnapshotRecord,
    default_history_dir,
    history_path,
)
from repo_seo.trend.report import render_trend_html, render_trend_markdown, render_trend_terminal
from repo_seo.trend.trend import analyze_trend, render_trend_svg


def _rec(at: str, total: float, readme: float = 0.0) -> SnapshotRecord:
    return SnapshotRecord(
        at=at,
        total=total,
        dimensions={
            "readme": DimensionSnapshot(earned=readme, eligible=25.0, total=25.0),
            "metadata": DimensionSnapshot(earned=8.0, eligible=20.0, total=20.0),
            "aeo": DimensionSnapshot(earned=0.0, eligible=20.0, total=20.0),
            "discoverability": DimensionSnapshot(earned=0.0, eligible=15.0, total=15.0),
            "health": DimensionSnapshot(earned=2.0, eligible=10.0, total=10.0),
            "activity": DimensionSnapshot(earned=4.0, eligible=10.0, total=10.0),
        },
    )


# ---------- history ----------

def test_history_append_and_load(tmp_path):
    store = HistoryStore(tmp_path)
    store.append(_rec("2026-10-01T10:00:00", 16.5), "linhaha-ai", "RepoRadar")
    store.append(_rec("2026-10-08T10:00:00", 30.0), "linhaha-ai", "RepoRadar")
    recs = store.load("linhaha-ai", "RepoRadar")
    assert [r.total for r in recs] == [16.5, 30.0]
    assert store.count("linhaha-ai", "RepoRadar") == 2


def test_history_unsorted_input_sorted_on_load(tmp_path):
    store = HistoryStore(tmp_path)
    store.append(_rec("2026-10-08T10:00:00", 30.0), "o", "r")
    store.append(_rec("2026-10-01T10:00:00", 16.5), "o", "r")
    recs = store.load("o", "r")
    assert [r.total for r in recs] == [16.5, 30.0]


def test_history_dedup_same_timestamp(tmp_path):
    store = HistoryStore(tmp_path)
    store.append(_rec("2026-10-01T10:00:00", 16.5), "o", "r")
    store.append(_rec("2026-10-01T10:00:00", 99.0), "o", "r")
    recs = store.load("o", "r")
    assert len(recs) == 1 and recs[0].total == 99.0


def test_history_corrupt_file_backup(tmp_path):
    store = HistoryStore(tmp_path)
    p = history_path("o", "r", tmp_path)
    p.write_text("{broken json", encoding="utf-8")
    assert store.load("o", "r") == []
    assert p.with_suffix(".corrupt.json").exists()


def test_default_history_dir():
    assert default_history_dir().name == ".repo-seo-history"


# ---------- trend ----------

def test_analyze_trend_up():
    recs = [_rec("2026-10-01T10:00:00", 16.5), _rec("2026-10-08T10:00:00", 30.0, readme=5.0)]
    diff = analyze_trend(recs)
    assert diff.direction == "up"
    assert diff.delta_total == pytest.approx(13.5)
    assert diff.delta_dimensions["readme"] == pytest.approx(5.0)
    assert diff.n_records == 2
    assert diff.span_days == 7


def test_analyze_trend_single_record():
    diff = analyze_trend([_rec("2026-10-01T10:00:00", 16.5)])
    assert diff.direction == "flat"
    assert diff.delta_total == 0.0
    assert diff.first is diff.latest


def test_analyze_trend_empty():
    diff = analyze_trend([])
    assert diff.n_records == 0


def test_svg_contains_series():
    recs = [_rec("2026-10-01T10:00:00", 16.5), _rec("2026-10-08T10:00:00", 30.0, readme=5.0)]
    svg = render_trend_svg(recs)
    assert "<svg" in svg and "<polyline" in svg
    assert "总分" in svg and "README 内容质量" in svg
    assert "2026-10-01" in svg and "2026-10-08" in svg


def test_svg_empty():
    svg = render_trend_svg([])
    assert "暂无历史记录" in svg


# ---------- reports ----------

def test_trend_reports(tmp_path):
    recs = [_rec("2026-10-01T10:00:00", 16.5), _rec("2026-10-08T10:00:00", 30.0)]
    diff = analyze_trend(recs)
    term = render_trend_terminal("o", "r", diff)
    assert "趋势监控" in term and "▲" in term and "+13.5" in term
    md = render_trend_markdown("o", "r", diff)
    assert "趋势监控报告" in md and "维度变化" in md
    html = render_trend_html("o", "r", diff)
    assert "<!DOCTYPE html>" in html and "趋势监控报告" in html and "<svg" in html
