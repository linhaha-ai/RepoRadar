"""HTML 报告导出（M5，DESIGN.md §8 扩展）。

单文件、自包含（内联 CSS，零外部依赖），浏览器直接打开、可打印。
中性蓝灰配色；总分 + 维度进度条 + Top3 卡片 + AI 建议 + 证据表。
"""

from __future__ import annotations

from datetime import datetime
from html import escape

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
    "indexed": ("已收录（有证据）", "ok"),
    "not_indexed": ("未发现收录证据", "warn"),
    "unknown": ("无法检测（未配置核验凭据）", "na"),
    "error": ("核验失败", "bad"),
}

_CSS = """
:root{--ink:#0f172a;--muted:#64748b;--line:#e2e8f0;--bg:#f8fafc;--card:#fff;
--brand:#2563eb;--ok:#16a34a;--warn:#d97706;--bad:#dc2626;--na:#94a3b8;}
*{box-sizing:border-box;margin:0;padding:0;}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;
background:var(--bg);color:var(--ink);line-height:1.6;padding:32px 16px;}
.wrap{max-width:960px;margin:0 auto;}
header.card{background:var(--card);border:1px solid var(--line);border-radius:14px;
padding:28px 32px;box-shadow:0 1px 3px rgba(15,23,42,.06);}
.repo{font-size:14px;color:var(--muted);}
.repo b{color:var(--ink);font-size:18px;}
.tag{display:inline-block;font-size:12px;padding:2px 10px;border-radius:999px;
background:#dbeafe;color:#1d4ed8;margin-left:8px;vertical-align:2px;}
.tag.priv{background:#fee2e2;color:#b91c1c;}
.score-row{display:flex;align-items:baseline;gap:14px;margin-top:14px;flex-wrap:wrap;}
.big{font-size:56px;font-weight:700;letter-spacing:-1px;}
.big small{font-size:18px;color:var(--muted);font-weight:400;}
.note{font-size:13px;color:var(--muted);margin-top:6px;}
h2{font-size:17px;margin:28px 0 12px;padding-left:10px;border-left:4px solid var(--brand);}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:18px 22px;margin-bottom:12px;}
.dim{display:grid;grid-template-columns:180px 1fr 90px;align-items:center;gap:14px;padding:9px 0;
border-bottom:1px dashed var(--line);font-size:14px;}
.dim:last-child{border-bottom:none;}
.bar{background:#eef2f7;border-radius:6px;height:12px;overflow:hidden;}
.bar i{display:block;height:100%;background:var(--brand);border-radius:6px;}
.bar i.ok{background:var(--ok);} .bar i.warn{background:var(--warn);} .bar i.bad{background:var(--bad);}
.dim .pts{text-align:right;color:var(--muted);font-variant-numeric:tabular-nums;}
.issue{padding:12px 0;border-bottom:1px dashed var(--line);}
.issue:last-child{border-bottom:none;}
.pri{display:inline-block;font-size:11px;font-weight:600;padding:1px 8px;border-radius:4px;margin-right:6px;}
.p0{background:#fee2e2;color:#b91c1c;} .p1{background:#fef3c7;color:#92400e;} .p2{background:#e2e8f0;color:#334155;}
.ev{color:var(--muted);font-size:13px;margin-top:3px;}
.sug{margin-top:3px;font-size:14px;}
.advice{padding:12px 0;border-bottom:1px dashed var(--line);}
.advice:last-child{border-bottom:none;}
table{width:100%;border-collapse:collapse;font-size:13.5px;background:var(--card);
border:1px solid var(--line);border-radius:12px;overflow:hidden;}
th,td{text-align:left;padding:9px 14px;border-bottom:1px solid var(--line);vertical-align:top;}
th{background:#f1f5f9;font-weight:600;white-space:nowrap;}
tr:last-child td{border-bottom:none;}
code{background:#f1f5f9;border-radius:4px;padding:1px 6px;font-size:12.5px;}
footer{margin-top:28px;font-size:12px;color:var(--muted);text-align:center;}
@media print{body{background:#fff;padding:0;} .card,header.card{box-shadow:none;break-inside:avoid;}}
"""


def _escape(text: str | None) -> str:
    return escape(text or "", quote=True)


def _bar_class(ratio: float) -> str:
    if ratio >= 0.7:
        return "ok"
    if ratio >= 0.4:
        return "warn"
    return "bad"


def render_html(
    report: ScoreReport,
    snap: RepoSnapshot,
    advices: list[AIAdvice] | None = None,
    advice_source: AdviceSource | None = None,
    verification: VerificationResult | None = None,
) -> str:
    vis = "私有" if snap.is_private else "公开"
    vis_cls = "priv" if snap.is_private else ""
    now = datetime.now().isoformat(timespec="seconds")

    # 维度进度条
    dim_rows = []
    for dim, d in report.dimensions.items():
        ratio = d.ratio if d.eligible > 0 else 0.0
        bar_cls = _bar_class(ratio)
        eligible = f"（可评分 {d.eligible:.0f}）" if d.eligible != d.total else ""
        dim_rows.append(f"""<div class="dim">
  <div>{_escape(d.label)}{f' <span style="font-size:12px;color:var(--na)">{eligible}</span>' if eligible else ""}</div>
  <div class="bar"><i class="{bar_cls}" style="width:{ratio * 100:.0f}%"></i></div>
  <div class="pts">{d.earned:.1f} / {d.eligible:.1f}</div>
</div>""")
    dim_section = "\n".join(dim_rows)

    # Top3
    issue_rows = []
    for i, r in enumerate(report.top_issues, 1):
        pri = _escape(r.priority)
        issue_rows.append(f"""<div class="issue">
  <span class="pri {pri.lower()}">{pri}</span><b>{i}. {_escape(r.name)}</b>
  <span style="color:var(--muted);font-size:13px">（{_escape(r.dimension)} 维度，扣 {r.score - r.score_earned:.1f} 分）</span>
  <div class="ev">证据：{_escape(r.evidence)}</div>
  <div class="sug">建议：{_escape(r.suggestion)}</div>
</div>""")
    issue_section = "\n".join(issue_rows) if issue_rows else '<div class="card">（无未通过项）</div>'

    # AI 建议
    advice_html = ""
    if advices:
        label = _SOURCE_LABEL.get(advice_source or AdviceSource.TEMPLATE, "规则模板")
        rows = []
        for adv in advices:
            pri = _escape(adv.priority)
            example = (
                f'<div class="ev">示例：<code>{_escape(adv.example)}</code></div>'
                if adv.example
                else ""
            )
            rows.append(f"""<div class="advice">
  <span class="pri {pri.lower()}">{pri}</span><b>{_escape(adv.rule_id)} · {_escape(adv.problem)}</b>
  <div class="sug">建议：{_escape(adv.suggestion)}</div>
  {example}
</div>""")
        advice_rows = "\n".join(rows)
        advice_html = f"""<h2>优化建议（{_escape(label)}）</h2>
<div class="card">{advice_rows}</div>"""

    # 证据表
    fails = [r for r in report.results if r.status == EvidenceStatus.FAIL]
    if fails:
        rows = []
        for r in fails:
            example = f"<br><code>{_escape(r.example)}</code>" if r.example else ""
            rows.append(
                f"<tr><td><b>{_escape(r.rule_id)}</b></td><td>{_escape(r.name)}"
                f"<div class='ev'>{_escape(r.evidence)}</div>"
                f"<div class='ev'>{_escape(r.reason)}</div>{example}</td>"
                f"<td>{r.score_earned:.1f} / {r.score:.0f}</td></tr>"
            )
        evidence_rows = "\n".join(rows)
        evidence_table = f"""<h2>扣分项证据清单</h2>
<table><thead><tr><th>规则</th><th>检查项 / 证据 / 原因</th><th>得分</th></tr></thead>
<tbody>{evidence_rows}</tbody></table>"""
    else:
        evidence_table = '<h2>扣分项证据清单</h2><div class="card">（无扣分项）</div>'

    na_note = (
        f'<div class="note">注：{report.n_na_unknown} 项为不适用/无法检测，已从分母剔除；D02 收录证据需 V2 外部核验。</div>'
        if report.n_na_unknown
        else ""
    )

    # 外部验证证据（V2）
    verify_html = ""
    if verification is not None:
        g = verification.google
        label, tone = _GOOGLE_LABEL.get(g.status, (g.status, "na"))
        blocks = [
            f"""<h2>外部验证证据（Search Visibility Evidence · V2）</h2>
<div class="card">
  <div><b>Google 收录</b>：<span class="pri {tone}" style="text-transform:none">{_escape(label)}</span>
    <div class="ev">{_escape(g.evidence)}</div>
    {f'<div class="ev">site: 命中 {g.total_results} 条；Top URL：<code>{_escape(g.top_url or "（无）")}</code></div>' if g.total_results is not None else ""}
  </div>"""
        ]
        if verification.probes:
            probe_rows = [
                f"""<div class="ev" style="margin-top:8px"><b>{_escape(p.model)}</b>：{'提及 ✅' if p.mentioned else '未提及'}
  <span style="color:var(--na)">（{p.status}）</span>
  {f'<br>回答：{_escape(p.snippet)}' if p.snippet else ""}
  {f'<br><span style="color:var(--bad)">错误：{_escape(p.error)}</span>' if p.error else ""}</div>"""
                for p in verification.probes
            ]
            blocks.append(
                '<div class="ev" style="margin-top:10px"><b>模型知识探测</b>'
                '（训练知识采样，非实时检索）：</div>' + "\n".join(probe_rows)
            )
        for note in verification.notes:
            if note != g.evidence:
                blocks.append(f'<div class="note" style="margin-top:6px">{_escape(note)}</div>')
        blocks.append("</div>")
        verify_html = "\n".join(blocks)
    warns = (
        "<h2>配置告警</h2><div class='card'>" + "<br>".join(f"⚠ {_escape(w)}" for w in report.warnings) + "</div>"
        if report.warnings
        else ""
    )

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_escape(snap.full_name)} · 仓库可发现性评分报告</title>
<style>{_CSS}</style>
</head>
<body>
<div class="wrap">

<header class="card">
  <div class="repo"><b>{_escape(snap.full_name)}</b>
    <span class="tag {vis_cls}">{_escape(vis)}</span>
    <span class="tag">{_escape(snap.default_branch)}</span>
    {f'<span class="tag">{_escape(snap.license_spdx)}</span>' if snap.license_spdx else ""}
  </div>
  <div class="score-row">
    <div class="big">{report.total:.1f}<small>&nbsp;/ 100</small></div>
    <div>
      <b>仓库可发现性评分</b>（Repository Discoverability Score）
      <div class="note">总分代表优化准备度，不代表真实搜索排名；静态审计 ≠ 真实曝光</div>
    </div>
  </div>
</header>

<h2>维度得分</h2>
<div class="card">{dim_section}</div>

<h2>最优先修复的问题</h2>
<div class="card">{issue_section}</div>

{advice_html}

{evidence_table}
{na_note}
{verify_html}
{warns}

<footer>
  生成时间：{_escape(now)} · 抓取时间：{_escape(snap.fetched_at)} · RepoRadar（repo-seo）<br>
  描述：{_escape(snap.description or "（无）")}
</footer>

</div>
</body>
</html>
"""
