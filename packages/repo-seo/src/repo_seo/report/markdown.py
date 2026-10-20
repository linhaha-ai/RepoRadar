"""Markdown 报告导出（M5，DESIGN.md §8 扩展）。

与终端报告同构：总分、维度得分、Top3、AI 建议、扣分项证据、元信息。
适用于：粘贴到 GitHub Issue / 飞书文档 / 内部 Wiki。
"""

from __future__ import annotations

from datetime import datetime

from ..advice.orchestrator import AdviceSource
from ..advice.schema import AIAdvice
from ..model import EvidenceStatus, RepoSnapshot
from ..scoring.scorer import ScoreReport
from ..verify.orchestrator import VerificationResult

_SOURCE_LABEL = {
    AdviceSource.AI: "AI 生成",
    AdviceSource.TEMPLATE: "规则模板",
    AdviceSource.MIXED: "AI 生成 + 模板补充",
}

_GOOGLE_LABEL = {
    "indexed": "已收录（有证据）",
    "not_indexed": "未发现收录证据",
    "unknown": "无法检测（未配置核验凭据）",
    "error": "核验失败",
}


def render_markdown(
    report: ScoreReport,
    snap: RepoSnapshot,
    advices: list[AIAdvice] | None = None,
    advice_source: AdviceSource | None = None,
    verification: VerificationResult | None = None,
) -> str:
    vis = "私有" if snap.is_private else "公开"
    lines: list[str] = []
    lines.append(f"# {snap.full_name} · 仓库可发现性评分报告")
    lines.append("")
    lines.append(
        f"**仓库**：`{snap.full_name}`（{vis}，默认分支 `{snap.default_branch}`）"
    )
    lines.append("")
    lines.append(f"## 总分：**{report.total:.1f} / 100**")
    lines.append("")
    lines.append("> 总分代表仓库的优化准备度，不代表真实搜索排名；静态审计 ≠ 真实曝光。")
    lines.append("")

    # 维度得分
    lines.append("## 维度得分")
    lines.append("")
    lines.append("| 维度 | 得分 | 满分 | 得分率 |")
    lines.append("|---|---:|---:|---:|")
    for dim, d in report.dimensions.items():
        ratio = f"{d.ratio * 100:.0f}%" if d.eligible > 0 else "—"
        eligible = "" if d.eligible == d.total else f"（可评分 {d.eligible:.0f}）"
        lines.append(f"| {d.label} | {d.earned:.1f} | {d.eligible:.1f}{eligible} | {ratio} |")
    lines.append("")

    # Top3
    lines.append("## 最优先修复的问题")
    lines.append("")
    if report.top_issues:
        for i, r in enumerate(report.top_issues, 1):
            lines.append(
                f"{i}. **[{r.priority}] {r.name}**（{r.dimension} 维度，扣 {r.score - r.score_earned:.1f} 分）"
            )
            lines.append(f"   - 证据：{r.evidence}")
            lines.append(f"   - 建议：{r.suggestion}")
    else:
        lines.append("（无未通过项）")
    lines.append("")

    # AI 建议
    if advices:
        label = _SOURCE_LABEL.get(advice_source or AdviceSource.TEMPLATE, "规则模板")
        lines.append(f"## 优化建议（{label}）")
        lines.append("")
        for adv in advices:
            lines.append(f"- **[{adv.priority}] {adv.rule_id} · {adv.problem}**")
            lines.append(f"  - 建议：{adv.suggestion}")
            if adv.reason and adv.reason != "（无原因说明）":
                lines.append(f"  - 原因：{adv.reason}")
            if adv.example:
                lines.append(f"  - 示例：`{adv.example}`")
        lines.append("")

    # 证据清单
    lines.append("## 扣分项证据清单")
    lines.append("")
    fails = [r for r in report.results if r.status == EvidenceStatus.FAIL]
    if fails:
        for r in fails:
            lines.append(
                f"- **[{r.rule_id}] {r.name}**：{r.score_earned:.1f}/{r.score:.0f}"
            )
            lines.append(f"  - 证据：{r.evidence}")
            lines.append(f"  - 原因：{r.reason}")
            if r.example:
                lines.append(f"  - 示例：`{r.example}`")
    else:
        lines.append("（无扣分项）")
    lines.append("")

    if report.n_na_unknown:
        lines.append(
            f"> 注：{report.n_na_unknown} 项为不适用/无法检测，已从分母剔除；D02 收录证据需 V2 外部核验。"
        )
        lines.append("")

    # 外部验证证据（V2）
    if verification is not None:
        g = verification.google
        lines.append("## 外部验证证据（Search Visibility Evidence · V2）")
        lines.append("")
        lines.append(f"- **Google 收录**：{_GOOGLE_LABEL.get(g.status, g.status)}")
        lines.append(f"  - 证据：{g.evidence}")
        if g.total_results is not None:
            lines.append(f"  - site: 命中 {g.total_results} 条；Top URL：`{g.top_url or '（无）'}`")
        if verification.probes:
            lines.append("- **模型知识探测**（训练知识采样，非实时检索）：")
            for p in verification.probes:
                state = "提及 ✅" if p.mentioned else "未提及"
                lines.append(f"  - `{p.model}`：{state}（{p.status}）")
                if p.snippet:
                    lines.append(f"    - 回答：{p.snippet}")
                if p.error:
                    lines.append(f"    - 错误：{p.error}")
        for note in verification.notes:
            if note != g.evidence:
                lines.append(f"- 注：{note}")
        lines.append("")

    if report.warnings:
        lines.append("**配置告警**")
        for w in report.warnings:
            lines.append(f"- {w}")
        lines.append("")

    # 元信息
    lines.append("---")
    lines.append("")
    lines.append(
        f"*生成时间：{datetime.now().isoformat(timespec='seconds')} · "
        f"抓取时间：{snap.fetched_at} · RepoRadar（repo-seo）*"
    )
    lines.append("")
    return "\n".join(lines)
