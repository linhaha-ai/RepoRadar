"""规则引擎：注册与运行（DESIGN.md §6.1 / §6.4）。

新增规则不改引擎：在对应维度模块的 RULES 列表追加即可。
规则可配置化：--config 加载 TOML，支持启用/分值/优先级/阈值参数覆盖。
"""

from __future__ import annotations

import inspect

from ..model import RepoSnapshot, Rule, RuleResult
from .activity import RULES as ACTIVITY_RULES
from .aeo import RULES as AEO_RULES
from .config import RuleConfig, apply_config, params_for
from .discoverability import RULES as DISCOVERABILITY_RULES
from .health import RULES as HEALTH_RULES
from .metadata import RULES as METADATA_RULES
from .readme import RULES as README_RULES

ALL_RULES: list[Rule] = (
    README_RULES
    + METADATA_RULES
    + AEO_RULES
    + DISCOVERABILITY_RULES
    + HEALTH_RULES
    + ACTIVITY_RULES
)

# 维度满分（必须与规则分值总和一致，运行期校验）
DIMENSION_TOTAL: dict[str, float] = {
    "readme": 25.0,
    "metadata": 20.0,
    "aeo": 20.0,
    "discoverability": 15.0,
    "health": 10.0,
    "activity": 10.0,
}

DIMENSION_LABELS: dict[str, str] = {
    "readme": "README 内容质量",
    "metadata": "仓库元数据",
    "aeo": "AI 检索准备度",
    "discoverability": "搜索可发现性",
    "health": "工程健康与可信度",
    "activity": "项目活跃度",
}


def validate_dimensions() -> list[str]:
    """校验默认规则分值总和与维度权重一致；返回不一致告警。"""
    warnings: list[str] = []
    for dim, total in DIMENSION_TOTAL.items():
        rules = [r for r in ALL_RULES if r.dimension == dim]
        actual = sum(r.score for r in rules)
        if abs(actual - total) > 1e-6:
            warnings.append(
                f"维度 {dim}: 规则分值总和 {actual} ≠ 权重 {total}"
            )
    return warnings


def applied_rules(config: dict[str, RuleConfig] | None = None) -> list[Rule]:
    """应用配置后的规则列表（禁用项移除、分值/优先级覆盖）。"""
    if not config:
        return list(ALL_RULES)
    return apply_config(ALL_RULES, config)


def dimension_totals(rules: list[Rule]) -> dict[str, float]:
    """按实际规则分值聚合维度满分（自定义配置下动态计算）。"""
    totals: dict[str, float] = {}
    for r in rules:
        totals[r.dimension] = totals.get(r.dimension, 0.0) + r.score
    return totals


def _call_check(rule: Rule, snap: RepoSnapshot, params: dict | None) -> RuleResult:
    """调用规则检测函数：签名含 params 的规则传入阈值参数。"""
    sig = inspect.signature(rule.check)
    if len(sig.parameters) > 1:
        return rule.check(snap, params or {})
    return rule.check(snap)


def run_rules(
    snapshot: RepoSnapshot,
    config: dict[str, RuleConfig] | None = None,
) -> list[RuleResult]:
    """运行全部（已应用配置的）规则，返回 RuleResult 列表。"""
    rules = applied_rules(config)
    return [
        _call_check(rule, snapshot, params_for(rule.id, config))
        for rule in rules
    ]
