"""规则模板建议（本地兜底，DESIGN.md §10.5）。

从 RuleResult 的 suggestion/reason/example 直接生成 AIAdvice，
用于：无 API Key、LLM 失败、LLM 输出校验失败三种降级场景。
"""

from __future__ import annotations

from ..model import EvidenceStatus, RepoSnapshot, RuleResult
from .schema import AIAdvice


def template_advice(snapshot: RepoSnapshot, results: list[RuleResult]) -> list[AIAdvice]:
    out: list[AIAdvice] = []
    for r in results:
        if r.status != EvidenceStatus.FAIL:
            continue
        out.append(
            AIAdvice(
                rule_id=r.rule_id,
                priority=r.priority,
                problem=r.name,
                suggestion=r.suggestion,
                reason=r.reason,
                example=r.example,
                impact={"dimensions": [r.dimension]},
            )
        )
    return out
