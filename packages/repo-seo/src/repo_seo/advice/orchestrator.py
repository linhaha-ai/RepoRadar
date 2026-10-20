"""建议编排（DESIGN.md §10.6）：AI 优先，失败/无 Key 降级模板。

- 无 LLM（未配置 Key / --no-ai）→ 全模板；
- 有 LLM：调用（重试 1 次）→ 校验 → 全量通过用 AI 结果；
  调用失败 / 输出为空 / 校验后无有效项 → 降级模板；
  部分有效（LLM 只覆盖部分 fail 项）→ 合并：AI 项 + 未覆盖项的模板项（mixed）。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from ..model import RepoSnapshot, RuleResult
from .llm import LLMClient, LLMError
from .prompts import SYSTEM_PROMPT, build_user_prompt
from .schema import AIAdvice, validate_advice
from .templates import template_advice


class AdviceSource(str, Enum):
    AI = "ai"
    TEMPLATE = "template"
    MIXED = "mixed"


@dataclass
class AdviceResult:
    advices: list[AIAdvice]
    source: AdviceSource
    note: str | None = None


def generate_advice(
    snap: RepoSnapshot,
    results: list[RuleResult],
    llm: LLMClient | None,
    retries: int = 1,
) -> AdviceResult:
    if llm is None:
        return AdviceResult(template_advice(snap, results), AdviceSource.TEMPLATE)

    known_ids = {r.rule_id for r in results}
    fail_ids = {r.rule_id for r in results if r.status.value == "fail"}
    user_prompt = build_user_prompt(snap, results)

    ai_advices: list[AIAdvice] = []
    last_error: str | None = None
    for attempt in range(retries + 1):
        try:
            data = llm.chat_json(SYSTEM_PROMPT, user_prompt)
            ai_advices = validate_advice(data, known_ids)
            if ai_advices:
                break
            last_error = "LLM 输出为空或未通过校验"
        except LLMError as e:
            last_error = str(e)
    else:
        # for-else：全部尝试失败
        return AdviceResult(
            template_advice(snap, results),
            AdviceSource.TEMPLATE,
            note=f"AI 建议不可用（{last_error}），已使用规则模板",
        )

    covered = {a.rule_id for a in ai_advices}
    missing = fail_ids - covered
    if missing:
        merged = list(ai_advices)
        for r in results:
            if r.rule_id in missing:
                merged.append(
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
        return AdviceResult(merged, AdviceSource.MIXED)

    return AdviceResult(ai_advices, AdviceSource.AI)
