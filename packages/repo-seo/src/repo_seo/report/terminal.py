"""终端报告渲染（DESIGN.md §7.4 / §8 / §10.8）。"""

from __future__ import annotations

from ..advice.schema import AIAdvice
from ..advice.orchestrator import AdviceSource
from ..model import EvidenceStatus, RepoSnapshot
from ..scoring.scorer import ScoreReport
from ..verify.orchestrator import VerificationResult

_STATUS_ICON = {
    EvidenceStatus.PASS: "✅",
    EvidenceStatus.FAIL: "❌",
    EvidenceStatus.N_A: "➖",
    EvidenceStatus.UNKNOWN: "❓",
}

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


def render_terminal(
    report: ScoreReport,
    snap: RepoSnapshot,
    advices: list[AIAdvice] | None = None,
    advice_source: AdviceSource | None = None,
    verification: VerificationResult | None = None,
) -> str:
    lines: list[str] = []
    vis = "私有" if snap.is_private else "公开"
    lines.append(f"{snap.full_name}  [{vis}]  ·  仓库可发现性评分")
    lines.append("")
    lines.append(f"{report.total:.1f} / 100 ｜ Repository Discoverability Score")
    lines.append("（总分代表优化准备度，不代表真实搜索排名；静态审计 ≠ 真实曝光）")
    lines.append("")

    lines.append("维度得分")
    for dim, d in report.dimensions.items():
        bar = "█" * int(round(d.ratio * 10)) if d.eligible > 0 else ""
        status = "" if d.eligible == d.total else f"（可评分值 {d.eligible:.0f}）"
        lines.append(f"  {d.label:<10} {d.earned:>5.1f} / {d.eligible:.1f} {bar} {status}")

    lines.append("")
    lines.append("最优先修复的问题")
    if report.top_issues:
        for i, r in enumerate(report.top_issues, 1):
            lines.append(f"  {i}. [{r.priority}] {r.name}（{r.dimension} 维度，扣 {r.score - r.score_earned:.1f} 分）")
            lines.append(f"      证据：{r.evidence}")
            lines.append(f"      建议：{r.suggestion}")
    else:
        lines.append("  无（全部通过）")

    if advices:
        label = _SOURCE_LABEL.get(advice_source or AdviceSource.TEMPLATE, "规则模板")
        lines.append("")
        lines.append(f"优化建议（{label}）")
        for adv in advices:
            lines.append(f"  [{adv.priority}] {adv.rule_id} · {adv.problem}")
            lines.append(f"      建议：{adv.suggestion}")
            if adv.reason and adv.reason != "（无原因说明）":
                lines.append(f"      原因：{adv.reason}")
            if adv.example:
                lines.append(f"      示例：{adv.example}")
        if advice_source == AdviceSource.TEMPLATE:
            lines.append("  （提示：配置 REPO_SEO_API_KEY 可启用 AI 生成建议）")

    lines.append("")
    lines.append("扣分项证据清单")
    fails = [r for r in report.results if r.status == EvidenceStatus.FAIL]
    if fails:
        for r in fails:
            lines.append(f"  {_STATUS_ICON[r.status]} [{r.rule_id}] {r.name}：{r.score_earned:.1f}/{r.score:.0f}")
            lines.append(f"      {r.evidence}")
            lines.append(f"      原因：{r.reason}")
            if r.example:
                lines.append(f"      示例：{r.example}")
    else:
        lines.append("  无")

    if report.n_na_unknown:
        lines.append("")
        lines.append(f"（注：{report.n_na_unknown} 项为不适用/无法检测，已从分母剔除；D02 收录证据需 V2 外部核验）")

    if verification is not None:
        lines.append("")
        lines.append("外部验证证据（Search Visibility Evidence · V2）")
        g = verification.google
        g_icon = {"indexed": "✅", "not_indexed": "❌", "unknown": "❓", "error": "⚠️"}.get(g.status, "❓")
        lines.append(f"  {g_icon} Google 收录：{_GOOGLE_LABEL[g.status]}")
        lines.append(f"      {g.evidence}")
        if g.total_results is not None:
            lines.append(f"      site: 命中 {g.total_results} 条；Top URL：{g.top_url or '（无）'}")
        if verification.probes:
            lines.append("  模型知识探测（训练知识采样，非实时检索）：")
            for p in verification.probes:
                icon = "✅" if p.mentioned else "—"
                lines.append(f"    {icon} {p.model}：{'提及' if p.mentioned else '未提及'}"
                             f"（{p.status}）")
                if p.snippet:
                    lines.append(f"        回答：{p.snippet}")
                if p.error:
                    lines.append(f"        [错误] {p.error}")
        for note in verification.notes:
            if note not in (g.evidence if g.status == "unknown" else ""):
                lines.append(f"  （{note}）")

    if report.warnings:
        lines.append("")
        lines.append("[配置告警]")
        for w in report.warnings:
            lines.append(f"  - {w}")

    return "\n".join(lines)
