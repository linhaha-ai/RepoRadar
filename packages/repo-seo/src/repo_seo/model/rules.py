"""规则与证据数据模型（DESIGN.md §4.2 规格实现）。"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from .snapshot import RepoSnapshot


class CheckType(str, Enum):
    HARD = "hard"          # 程序可判定，无歧义
    SEMANTIC = "semantic"  # 语义判断，带置信度


class EvidenceStatus(str, Enum):
    PASS = "pass"          # 通过（得满分）
    FAIL = "fail"          # 未通过（按得分）
    N_A = "n_a"            # 不适用（不计入分母）
    UNKNOWN = "unknown"    # 无法检测（不计入分母，报告标注）


@dataclass(frozen=True)
class Rule:
    """规则声明：元数据 + 检测函数。"""

    id: str                # 如 R01 / M02 / A03 / D01 / H01 / AC01
    dimension: str         # readme / metadata / aeo / discoverability / health / activity
    name: str              # 检查项名
    score: float           # 满分分值
    check_type: CheckType
    priority: str          # P0 / P1 / P2
    pass_condition: str    # 通过条件（人可读，进报告）
    check: Callable[["RepoSnapshot"], "RuleResult"]

    # 语义检查项的置信度（hard 规则恒为 1.0）
    confidence: float = 1.0


@dataclass
class RuleResult:
    """单条规则的检测结果（证据驱动，DESIGN.md §4.2）。"""

    rule_id: str
    name: str
    dimension: str
    status: EvidenceStatus
    score: float           # 满分
    score_earned: float    # 实得分
    evidence: str          # 证据位置与内容（文件/行/URL/原文摘录）
    reason: str            # 通过/扣分原因
    suggestion: str        # 修复建议
    example: str | None = None   # 修复示例
    priority: str = "P1"
    check_type: CheckType = CheckType.HARD
    confidence: float = 1.0

    def to_dict(self) -> dict:
        return {
            "rule_id": self.rule_id,
            "name": self.name,
            "dimension": self.dimension,
            "status": self.status.value,
            "score": self.score,
            "score_earned": self.score_earned,
            "evidence": self.evidence,
            "reason": self.reason,
            "suggestion": self.suggestion,
            "example": self.example,
            "priority": self.priority,
            "check_type": self.check_type.value,
            "confidence": self.confidence,
        }


# ---------- 便捷构造 ----------

def result_pass(rule: Rule, evidence: str, reason: str) -> RuleResult:
    return RuleResult(
        rule_id=rule.id, name=rule.name, dimension=rule.dimension,
        status=EvidenceStatus.PASS, score=rule.score, score_earned=rule.score,
        evidence=evidence, reason=reason, suggestion="无需修改",
        priority=rule.priority, check_type=rule.check_type, confidence=rule.confidence,
    )


def result_fail(
    rule: Rule, earned: float, evidence: str, reason: str,
    suggestion: str, example: str | None = None,
) -> RuleResult:
    return RuleResult(
        rule_id=rule.id, name=rule.name, dimension=rule.dimension,
        status=EvidenceStatus.FAIL, score=rule.score, score_earned=earned,
        evidence=evidence, reason=reason, suggestion=suggestion, example=example,
        priority=rule.priority, check_type=rule.check_type, confidence=rule.confidence,
    )


def result_n_a(rule: Rule, evidence: str, reason: str) -> RuleResult:
    return RuleResult(
        rule_id=rule.id, name=rule.name, dimension=rule.dimension,
        status=EvidenceStatus.N_A, score=rule.score, score_earned=0.0,
        evidence=evidence, reason=reason, suggestion="不适用",
        priority=rule.priority, check_type=rule.check_type, confidence=rule.confidence,
    )


def result_unknown(rule: Rule, evidence: str, reason: str, suggestion: str) -> RuleResult:
    return RuleResult(
        rule_id=rule.id, name=rule.name, dimension=rule.dimension,
        status=EvidenceStatus.UNKNOWN, score=rule.score, score_earned=0.0,
        evidence=evidence, reason=reason, suggestion=suggestion,
        priority=rule.priority, check_type=rule.check_type, confidence=rule.confidence,
    )
