"""AIAdvice 数据模型与校验（DESIGN.md §10.4）。"""

from __future__ import annotations

from dataclasses import dataclass, field

VALID_PRIORITIES = {"P0", "P1", "P2"}
VALID_DIMENSIONS = {"readme", "metadata", "aeo", "discoverability", "health", "activity"}


@dataclass
class AIAdvice:
    rule_id: str
    priority: str
    problem: str
    suggestion: str
    reason: str
    example: str | None = None
    impact: dict = field(default_factory=dict)


def _clean(raw: dict) -> AIAdvice | None:
    """把 LLM 输出的一条记录转为 AIAdvice；字段缺失/非法返回 None。"""
    rule_id = str(raw.get("rule_id") or "").strip()
    suggestion = str(raw.get("suggestion") or "").strip()
    priority = str(raw.get("priority") or "").strip().upper()
    problem = str(raw.get("problem") or "").strip()
    reason = str(raw.get("reason") or "").strip()
    if not rule_id or not suggestion:
        return None
    if priority not in VALID_PRIORITIES:
        priority = "P1"
    example = raw.get("example")
    example = str(example).strip() if example else None
    impact = raw.get("impact")
    if isinstance(impact, dict):
        dims = impact.get("dimensions")
        if isinstance(dims, list):
            impact["dimensions"] = [d for d in dims if d in VALID_DIMENSIONS]
    else:
        impact = {}
    return AIAdvice(
        rule_id=rule_id,
        priority=priority,
        problem=problem or "（无问题描述）",
        suggestion=suggestion,
        reason=reason or "（无原因说明）",
        example=example,
        impact=impact,
    )


def validate_advice(data: object, known_rule_ids: set[str]) -> list[AIAdvice]:
    """校验 LLM 输出：
    - 顶层必须为 dict 且含 advice 数组；
    - 每条记录 rule_id 必须在规则库、suggestion 非空；
    - 非法项丢弃（由编排层决定是否降级整批）。
    """
    if not isinstance(data, dict):
        return []
    raw_list = data.get("advice")
    if not isinstance(raw_list, list):
        return []
    out: list[AIAdvice] = []
    for raw in raw_list:
        if not isinstance(raw, dict):
            continue
        adv = _clean(raw)
        if adv is None:
            continue
        if adv.rule_id not in known_rule_ids:
            continue
        out.append(adv)
    return out
