"""趋势分析 + SVG 折线渲染（V2.2）。

- analyze_trend：对比首末/最近两次记录，输出总分与各维度变化（改善/恶化/持平）
- render_trend_svg：零依赖 SVG 折线图（总分 + 6 维度），适合 HTML 报告内嵌
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from .history import DimensionSnapshot, SnapshotRecord

DIM_ORDER = ["readme", "metadata", "aeo", "discoverability", "health", "activity"]
DIM_LABELS = {
    "readme": "README 内容质量",
    "metadata": "仓库元数据",
    "aeo": "AI 检索准备度",
    "discoverability": "搜索可发现性",
    "health": "工程健康与可信度",
    "activity": "项目活跃度",
}
DIM_COLORS = {
    "readme": "#2563eb",
    "metadata": "#0891b2",
    "aeo": "#7c3aed",
    "discoverability": "#d97706",
    "health": "#16a34a",
    "activity": "#dc2626",
}
TOTAL_COLOR = "#0f172a"


@dataclass
class TrendDiff:
    records: list[SnapshotRecord]
    first: SnapshotRecord | None = None
    latest: SnapshotRecord | None = None
    delta_total: float = 0.0
    delta_dimensions: dict[str, float] = field(default_factory=dict)
    direction: str = "flat"       # up / down / flat

    @property
    def n_records(self) -> int:
        return len(self.records)

    @property
    def span_days(self) -> int:
        if not self.records or len(self.records) < 2:
            return 0
        try:
            first = datetime.fromisoformat(self.records[0].at)
            last = datetime.fromisoformat(self.records[-1].at)
            return max(0, (last - first).days)
        except ValueError:
            return 0

    def to_dict(self) -> dict:
        return {
            "n_records": self.n_records,
            "span_days": self.span_days,
            "first_total": self.first.total if self.first else None,
            "latest_total": self.latest.total if self.latest else None,
            "delta_total": round(self.delta_total, 1),
            "delta_dimensions": {
                k: round(v, 1) for k, v in self.delta_dimensions.items()
            },
            "direction": self.direction,
        }


def _dim_earned(rec: SnapshotRecord, dim: str) -> float:
    d = rec.dimensions.get(dim)
    return d.earned if d else 0.0


def analyze_trend(records: list[SnapshotRecord]) -> TrendDiff:
    recs = sorted(records, key=lambda r: r.at)
    if not recs:
        return TrendDiff(records=[])
    diff = TrendDiff(records=recs, first=recs[0], latest=recs[-1])
    if len(recs) >= 2:
        diff.delta_total = recs[-1].total - recs[0].total
        for dim in DIM_ORDER:
            diff.delta_dimensions[dim] = _dim_earned(recs[-1], dim) - _dim_earned(recs[0], dim)
        eps = 0.05
        if diff.delta_total > eps:
            diff.direction = "up"
        elif diff.delta_total < -eps:
            diff.direction = "down"
    return diff


def _svg_points(values: list[float], width: int, height: int, pad: int) -> str:
    """把 0~100 的数值序列映射为 SVG 折线点串。"""
    if len(values) < 2:
        return ""
    n = len(values)
    step = (width - 2 * pad) / (n - 1) if n > 1 else 0
    pts = []
    for i, v in enumerate(values):
        x = pad + i * step
        y = pad + (height - 2 * pad) * (1 - max(0.0, min(100.0, v)) / 100)
        pts.append(f"{x:.1f},{y:.1f}")
    return " ".join(pts)


def render_trend_svg(
    records: list[SnapshotRecord],
    width: int = 860,
    height: int = 320,
) -> str:
    """零依赖 SVG 折线图：总分 + 各维度，X 轴为体检时间。"""
    recs = sorted(records, key=lambda r: r.at)
    if not recs:
        return (
            "<svg width='860' height='120' xmlns='http://www.w3.org/2000/svg'>"
            "<text x='10' y='20' font-size='14' fill='#64748b'>（暂无历史记录）</text></svg>"
        )

    pad = 44
    inner_h = height - 2 * pad
    series: list[tuple[str, str, list[float]]] = [
        ("总分", TOTAL_COLOR, [r.total for r in recs]),
    ]
    for dim in DIM_ORDER:
        series.append(
            (DIM_LABELS.get(dim, dim), DIM_COLORS[dim], [_dim_earned(r, dim) for r in recs])
        )

    # X 轴刻度（首/中/末时间）
    ticks = [recs[0], recs[len(recs) // 2], recs[-1]] if len(recs) >= 3 else recs
    tick_x = []
    for i, t in enumerate(ticks):
        x = pad + i * ((width - 2 * pad) / (max(len(ticks) - 1, 1)))
        tick_x.append((x, t.at[:16]))
    # Y 轴刻度 0/25/50/75/100
    y_ticks = [0, 25, 50, 75, 100]

    grid = "\n".join(
        f'<line x1="{pad}" y1="{pad + inner_h * (1 - y / 100):.1f}" x2="{width - pad}" '
        f'y2="{pad + inner_h * (1 - y / 100):.1f}" stroke="#eef2f7" stroke-width="1"/>'
        f'<text x="{pad - 6}" y="{pad + inner_h * (1 - y / 100) + 4:.1f}" '
        f'font-size="10" fill="#94a3b8" text-anchor="end">{y}</text>'
        for y in y_ticks
    )
    tick_text = "\n".join(
        f'<text x="{x:.1f}" y="{height - 12}" font-size="10" fill="#94a3b8" text-anchor="middle">{label}</text>'
        for x, label in tick_x
    )
    lines = "\n".join(
        f'<polyline points="{_svg_points(vals, width, height, pad)}" '
        f'fill="none" stroke="{color}" stroke-width="2" opacity="0.9"/>'
        f'<text x="{width - pad + 4}" y="{pad + inner_h * (1 - vals[-1] / 100):.1f}" '
        f'font-size="10" fill="{color}">{name}</text>'
        for name, color, vals in series
        if len(vals) >= 2
    )

    legend = "\n".join(
        f'<text x="{pad + 14 + i * 118}" y="18" font-size="11" fill="{color}">'
        f'<tspan dx="-10" fill="{color}">■</tspan> {name}</text>'
        for i, (name, color, _) in enumerate(series)
    )

    return (
        f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
        f'xmlns="http://www.w3.org/2000/svg" font-family="system-ui,-apple-system,sans-serif">'
        f"{legend}\n{grid}\n{tick_text}\n{lines}</svg>"
    )
