"""趋势报告渲染：终端 / Markdown / HTML（V2.2）。"""

from __future__ import annotations

from datetime import datetime
from html import escape

from .history import SnapshotRecord
from .trend import DIM_ORDER, DIM_LABELS, TrendDiff, render_trend_svg

_ARROW = {"up": "▲", "down": "▼", "flat": "—"}


def _dim_line(diff: TrendDiff) -> list[tuple[str, float]]:
    return [(DIM_LABELS.get(d, d), diff.delta_dimensions.get(d, 0.0)) for d in DIM_ORDER]


def render_trend_terminal(owner: str, repo: str, diff: TrendDiff) -> str:
    lines: list[str] = []
    lines.append(f"{owner}/{repo} · 趋势监控（V2.2）")
    lines.append("")
    if not diff.records:
        lines.append("暂无历史记录（先运行 repo-seo monitor <url>）")
        return "\n".join(lines)
    lines.append(f"体检次数：{diff.n_records} · 跨度：{diff.span_days} 天")
    if diff.first and diff.latest:
        lines.append(
            f"总分：{diff.first.total:.1f} → {diff.latest.total:.1f} "
            f"{_ARROW[diff.direction]} {diff.delta_total:+.1f}"
        )
    lines.append("")
    lines.append("维度变化（首 → 末）：")
    for label, delta in _dim_line(diff):
        if delta > 0.05:
            icon = "▲"
        elif delta < -0.05:
            icon = "▼"
        else:
            icon = "—"
        lines.append(f"  {icon} {label:<16} {delta:+.1f}")
    lines.append("")
    lines.append("历史记录：")
    for r in diff.records:
        lines.append(f"  {r.at[:16]}  总分 {r.total:.1f}")
    return "\n".join(lines)


def render_trend_markdown(owner: str, repo: str, diff: TrendDiff) -> str:
    lines: list[str] = []
    lines.append(f"# {owner}/{repo} · 趋势监控报告")
    lines.append("")
    if not diff.records:
        lines.append("暂无历史记录（先运行 `repo-seo monitor <url>`）")
        return "\n".join(lines)
    lines.append(f"- 体检次数：{diff.n_records} · 跨度：{diff.span_days} 天")
    if diff.first and diff.latest:
        lines.append(
            f"- 总分：**{diff.first.total:.1f} → {diff.latest.total:.1f}** "
            f"（{_ARROW[diff.direction]} {diff.delta_total:+.1f}）"
        )
    lines.append("")
    lines.append("## 维度变化（首 → 末）")
    lines.append("")
    lines.append("| 维度 | 变化 |")
    lines.append("|---|---:|")
    for label, delta in _dim_line(diff):
        lines.append(f"| {label} | {delta:+.1f} |")
    lines.append("")
    lines.append("## 历史记录")
    lines.append("")
    lines.append("| 时间 | 总分 |")
    lines.append("|---|---:|")
    for r in diff.records:
        lines.append(f"| {r.at[:16]} | {r.total:.1f} |")
    lines.append("")
    lines.append(
        f"*生成时间：{datetime.now().isoformat(timespec='seconds')} · RepoRadar 趋势监控*"
    )
    return "\n".join(lines)


def render_trend_html(owner: str, repo: str, diff: TrendDiff) -> str:
    now = datetime.now().isoformat(timespec="seconds")
    if not diff.records:
        body = '<div class="card">暂无历史记录（先运行 <code>repo-seo monitor &lt;url&gt;</code>）</div>'
    else:
        svg = render_trend_svg(diff.records)
        body = f"""
<div class="card" style="overflow-x:auto">{svg}</div>
<div class="card"><b>总分</b>：{diff.first.total:.1f} → {diff.latest.total:.1f}
  <span style="color:var(--muted)">（{diff.n_records} 次体检 · {diff.span_days} 天）</span></div>
<div class="card">
  <table>
    <thead><tr><th>维度</th><th>变化（首 → 末）</th></tr></thead>
    <tbody>
      {''.join(f"<tr><td>{escape(label)}</td><td>{delta:+.1f}</td></tr>" for label, delta in _dim_line(diff))}
    </tbody>
  </table>
</div>
<h2>历史记录</h2>
<div class="card">
  <table>
    <thead><tr><th>时间</th><th>总分</th></tr></thead>
    <tbody>
      {''.join(f"<tr><td>{escape(r.at[:16])}</td><td>{r.total:.1f}</td></tr>" for r in diff.records)}
    </tbody>
  </table>
</div>"""

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(owner)}/{escape(repo)} · 趋势监控报告</title>
<style>
:root{{--ink:#0f172a;--muted:#64748b;--line:#e2e8f0;--bg:#f8fafc;--card:#fff;--brand:#2563eb;}}
*{{box-sizing:border-box;margin:0;padding:0;}}
body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;
background:var(--bg);color:var(--ink);line-height:1.6;padding:32px 16px;}}
.wrap{{max-width:960px;margin:0 auto;}}
header.card{{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:24px 28px;}}
h2{{font-size:17px;margin:24px 0 12px;padding-left:10px;border-left:4px solid var(--brand);}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:18px 22px;margin-bottom:12px;}}
table{{width:100%;border-collapse:collapse;font-size:13.5px;}}
th,td{{text-align:left;padding:8px 14px;border-bottom:1px solid var(--line);}}
th{{background:#f1f5f9;}}
code{{background:#f1f5f9;border-radius:4px;padding:1px 6px;font-size:12.5px;}}
footer{{margin-top:24px;font-size:12px;color:var(--muted);text-align:center;}}
@media print{{body{{background:#fff;padding:0;}} .card{{box-shadow:none;break-inside:avoid;}}}}
</style>
</head>
<body>
<div class="wrap">
<header class="card">
  <div class="repo" style="color:var(--muted);font-size:14px">{escape(owner)}/{escape(repo)}</div>
  <div style="font-size:20px;font-weight:700;margin-top:6px">趋势监控报告（V2.2）</div>
</header>
{body}
<footer>生成时间：{escape(now)} · RepoRadar 趋势监控 · 数据源：.repo-seo-history/</footer>
</div>
</body>
</html>
"""
