"""趋势监控（V2.2，DESIGN.md §9 扩展）。

- history.py  历史记录存储（每仓库一个 JSON 文件，追加扫描快照）
- trend.py    趋势分析（变化 diff）+ SVG 折线渲染（零外部依赖）
- report.py   终端 / Markdown 趋势报告
- cli          monitor（定时体检入口：scan + record + trend）/ trend（读历史出曲线）

定时能力：本工具是无守护进程 CLI；「定时体检」通过系统 cron / CI / 豆包定时任务
定期调用 `repo-seo monitor <url>` 实现（每次调用只做一次体检并追加历史）。
"""

from .history import HistoryStore, SnapshotRecord, default_history_dir
from .trend import TrendDiff, analyze_trend, render_trend_svg
from .report import render_trend_terminal, render_trend_markdown, render_trend_html

__all__ = [
    "HistoryStore",
    "SnapshotRecord",
    "default_history_dir",
    "TrendDiff",
    "analyze_trend",
    "render_trend_svg",
    "render_trend_terminal",
    "render_trend_markdown",
    "render_trend_html",
]
