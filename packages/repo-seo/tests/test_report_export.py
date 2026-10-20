"""Markdown / HTML 报告导出测试（M5）。"""

from repo_seo.advice.orchestrator import AdviceSource
from repo_seo.advice.schema import AIAdvice
from repo_seo.report import render_html, render_markdown
from repo_seo.scoring import score_snapshot

from .fixtures import make_snapshot


def _report_and_advice():
    s = make_snapshot()
    report = score_snapshot(s)
    advices = [
        AIAdvice(
            rule_id="R01", priority="P0", problem="定位缺失",
            suggestion="补充定位", reason="首段", example="Example text",
        )
    ]
    return s, report, advices


def test_markdown_contains_core_sections():
    s, report, advices = _report_and_advice()
    md = render_markdown(report, s, advices, AdviceSource.AI)
    assert "# owner/repo · 仓库可发现性评分报告" in md
    assert "总分" in md and "/ 100" in md
    assert "维度得分" in md
    assert "README 内容质量" in md
    assert "最优先修复的问题" in md
    assert "优化建议（AI 生成）" in md
    assert "扣分项证据清单" in md
    assert "[R01]" in md or "R01" in md
    assert "生成时间" in md


def test_markdown_na_excluded():
    s = make_snapshot(homepage=None, has_pages=False)
    report = score_snapshot(s)
    md = render_markdown(report, s)
    assert "已从分母剔除" in md


def test_html_is_self_contained():
    s, report, advices = _report_and_advice()
    html = render_html(report, s, advices, AdviceSource.AI)
    assert "<!DOCTYPE html>" in html
    assert "<title>owner/repo · 仓库可发现性评分报告</title>" in html
    assert 'href="' not in html.split("<style>")[1]  # 样式之后无外部 CSS 链接
    assert "<script" not in html or html.count("<script") == 0  # 零外部脚本
    assert "16.5" not in html  # 占位断言：不含静态数字（分数由数据驱动）
    assert "维度得分" in html
    assert "最优先修复的问题" in html
    assert "优化建议（AI 生成）" in html
    assert "扣分项证据清单" in html


def test_html_escapes_evidence():
    s, report, advices = _report_and_advice()
    # 注入带特殊字符的建议，验证转义
    advices = [
        AIAdvice(
            rule_id="R01", priority="P0", problem="<script>alert(1)</script>",
            suggestion="补充定位 & 说明", reason="首段",
        )
    ]
    html = render_html(report, s, advices, AdviceSource.AI)
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html
    assert "&amp;" in html
