"""D4 搜索可发现性（15 分）：D01-D05。

三状态设计（DESIGN.md §6.3）：
- N/A：无文档站时 D03/D04 不扣分；
- UNKNOWN：D02 收录证据无授权无法检测，不判为未收录。
"""

from __future__ import annotations

from ..model import (
    CheckType,
    EvidenceStatus,
    RepoSnapshot,
    Rule,
    result_fail,
    result_n_a,
    result_pass,
    result_unknown,
)
from .readme_parser import parse_readme


def _has_doc_site(snap: RepoSnapshot) -> bool:
    return bool(snap.homepage) or snap.has_pages


def _check_d01(snap: RepoSnapshot):
    if snap.is_private:
        return result_fail(
            RULES[0], 0.0, "仓库为私有（visibility=private）",
            "私有仓库无法被 GitHub 搜索、Google、AI 爬虫访问，可发现性为 0",
            "将仓库设为 Public 才能获得任何外部曝光；开发期可用 Token 本地体检",
            "Settings → General → Danger Zone → Change visibility → Public",
        )
    if snap.archived:
        return result_fail(
            RULES[0], 1.5, "仓库已归档（archived=True）",
            "归档仓库被 GitHub 标记只读，搜索权重显著降低",
            "如仍维护，取消归档；如已停止，接受低权重",
            None,
        )
    return result_pass(RULES[0], "仓库公开且非归档", "页面可被正常索引")


def _check_d02(snap: RepoSnapshot):
    # V1 无 Search Console 授权 → UNKNOWN（不计分，报告标注"未验证"）
    return result_unknown(
        RULES[1],
        "无 Search Console 授权（V1 静态审计无法核验）",
        "真实收录状态需要外部证据；未检测 ≠ 未收录",
        "V2 接入 Search Console 后核验；或手动搜索 site:github.com/owner/repo 自查",
    )


def _check_d03(snap: RepoSnapshot):
    if not _has_doc_site(snap):
        return result_n_a(RULES[2], "无独立文档站（无 Homepage 且无 GitHub Pages）", "Sitemap/文档站不适用，不扣分")
    source = snap.homepage or ("GitHub Pages" if snap.has_pages else "")
    return result_pass(RULES[2], f"文档站存在：{source}", "文档入口可被搜索引擎与 AI 抓取")


def _check_d04(snap: RepoSnapshot):
    if not _has_doc_site(snap):
        return result_n_a(RULES[3], "无独立文档站", "Sitemap 不适用，不扣分")
    if snap.has_pages or (snap.homepage and "github.io" in snap.homepage.lower()):
        return result_pass(RULES[3], "GitHub Pages 自动处理 sitemap/robots", "Pages 内置标准抓取协议")
    return result_fail(
        RULES[3], 1.0, f"Homepage 为 {snap.homepage}（非 GitHub Pages）",
        "自定义文档站需自查 sitemap.xml / robots.txt；存在入口但协议未验证",
        "确保文档站有 sitemap.xml 并可在 robots.txt 中被允许抓取", None,
    )


def _check_d05(snap: RepoSnapshot):
    if not snap.has_readme:
        return result_fail(
            RULES[4], 0.0, "README 缺失",
            "无链接可指引用例/文档，AI 无法通过链接扩展信息",
            "创建 README 并加入文档、示例链接", None,
        )
    doc = parse_readme(snap.readme_text)
    valid = [u for u in doc.links if u.startswith(("http://", "https://"))]
    if valid:
        return result_pass(
            RULES[4],
            f"README 含 {len(valid)} 个有效外链：{', '.join(valid[:3])}…",
            "内外部链接完整（真实可达性核验在 V2 接入）",
        )
    return result_fail(
        RULES[4], 1.0, "README 内无任何 http(s) 链接",
        "无文档/示例链接会减少信息通道，AI 引用受限",
        "在 README 中加入 Docs / API Reference / 示例链接", None,
    )


RULES: list[Rule] = [
    Rule("D01", "discoverability", "仓库页面可访问性", 3.0, CheckType.HARD, "P0",
         "公开且非归档", _check_d01),
    Rule("D02", "discoverability", "搜索引擎收录证据", 4.0, CheckType.HARD, "P1",
         "有外部收录证据（V2 接入 Search Console）", _check_d02),
    Rule("D03", "discoverability", "文档站可抓取性", 3.0, CheckType.HARD, "P2",
         "有文档站（Homepage 或 GitHub Pages）", _check_d03),
    Rule("D04", "discoverability", "Sitemap 与规范 URL", 2.0, CheckType.HARD, "P2",
         "文档站存在且具备 sitemap 协议", _check_d04),
    Rule("D05", "discoverability", "内外部链接完整性", 3.0, CheckType.HARD, "P1",
         "README 含有效 http(s) 链接", _check_d05),
]
