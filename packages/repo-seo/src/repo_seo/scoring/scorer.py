"""评分聚合（DESIGN.md §7）。

聚合规则：
- 维度分 = Σ(该维度检查项实得分)
- 可评分值 = Σ(该维度检查项分值) − Σ(N_A 项分值) − Σ(UNKNOWN 项分值)
- 总分 = Σ所有维度实得分 / Σ所有可评分值 × 100

规则可配置化（--config）：维度满分随启用规则分值动态计算（默认 = 权重）。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..model import EvidenceStatus, RepoSnapshot, RuleResult
from ..rules.config import RuleConfig
from ..rules.engine import (
    DIMENSION_LABELS,
    applied_rules,
    dimension_totals,
    run_rules,
    validate_dimensions,
)

_PRIORITY_ORDER = {"P0": 0, "P1": 1, "P2": 2}


@dataclass
class DimensionScore:
    label: str
    earned: float
    eligible: float      # 可评分值（剔除 N/A 与 UNKNOWN 后）
    total: float         # 维度权重满分
    results: list[RuleResult] = field(default_factory=list)

    @property
    def ratio(self) -> float:
        return self.earned / self.eligible if self.eligible > 0 else 0.0


@dataclass
class ScoreReport:
    total: float                 # 0~100
    dimensions: dict[str, DimensionScore]
    top_issues: list[RuleResult]  # Top3 修复问题
    results: list[RuleResult]     # 全部结果
    n_na_unknown: int             # N/A 与 UNKNOWN 计数（报告标注）
    warnings: list[str] = field(default_factory=list)


def _top_issues(results: list[RuleResult], limit: int = 3) -> list[RuleResult]:
    fails = [r for r in results if r.status == EvidenceStatus.FAIL]
    fails.sort(
        key=lambda r: (
            _PRIORITY_ORDER.get(r.priority, 99),
            -(r.score - r.score_earned),  # 同优先级内扣分越多越靠前
        )
    )
    return fails[:limit]


def score_snapshot(
    snapshot: RepoSnapshot,
    config: dict[str, RuleConfig] | None = None,
) -> ScoreReport:
    rules = applied_rules(config)
    warnings = list(validate_dimensions())
    if config:
        warnings.append("已应用自定义规则配置（--config）：维度满分按启用规则动态计算")
    results = run_rules(snapshot, config)
    dim_totals = dimension_totals(rules)

    dims: dict[str, DimensionScore] = {}
    for dim, total in dim_totals.items():
        dim_results = [r for r in results if r.dimension == dim]
        excluded = {
            r.rule_id
            for r in dim_results
            if r.status in (EvidenceStatus.N_A, EvidenceStatus.UNKNOWN)
        }
        eligible = sum(r.score for r in dim_results if r.rule_id not in excluded)
        earned = sum(r.score_earned for r in dim_results)
        dims[dim] = DimensionScore(
            label=DIMENSION_LABELS[dim],
            earned=earned,
            eligible=eligible,
            total=total,
            results=dim_results,
        )

    total_earned = sum(d.earned for d in dims.values())
    total_eligible = sum(d.eligible for d in dims.values())
    total = (total_earned / total_eligible * 100) if total_eligible > 0 else 0.0

    n_na_unknown = sum(
        1
        for r in results
        if r.status in (EvidenceStatus.N_A, EvidenceStatus.UNKNOWN)
    )

    return ScoreReport(
        total=round(total, 1),
        dimensions=dims,
        top_issues=_top_issues(results),
        results=results,
        n_na_unknown=n_na_unknown,
        warnings=warnings,
    )
