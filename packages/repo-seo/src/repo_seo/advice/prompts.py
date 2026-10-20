"""Prompt 组装（DESIGN.md §10.3）。

- 系统提示：角色 + 评分规则定义（让 AI 理解「为什么扣分」）+ 输出 JSON 约束；
- 用户提示：项目快照摘要 + 检查结果（只传扣分项，控制 token）；
- Prompt 版本化：PROMPT_V1，变更需同步更新单测。
"""

from __future__ import annotations

from ..model import EvidenceStatus, RepoSnapshot, RuleResult
from ..rules.engine import ALL_RULES

PROMPT_V1 = "PROMPT_V1"


def _rules_table() -> str:
    lines = [
        "| 规则 | 检查项 | 维度 | 分值 | 优先级 | 通过条件 |",
        "|---|---|---|---|---|---|",
    ]
    for r in ALL_RULES:
        lines.append(
            f"| {r.id} | {r.name} | {r.dimension} | {r.score:.0f} | {r.priority} | {r.pass_condition} |"
        )
    return "\n".join(lines)


SYSTEM_PROMPT = f"""你是一名资深开源项目 SEO/AEO 顾问（{PROMPT_V1}）。
你负责根据仓库体检结果，为每个未通过的检查项生成具体、可执行的优化建议。

评分规则定义（6 维度，总分 100）：
{_rules_table()}

输出要求（严格遵守）：
1. 只对体检结果中 status=fail 的检查项生成建议；
2. 输出 JSON，格式为：{{"advice": [{{"rule_id": "...", "priority": "P0|P1|P2", "problem": "...", "suggestion": "...", "reason": "...", "example": "...", "impact": {{"dimensions": [...], "expected_gain": "..."}}}}]}}
3. rule_id 必须来自上表，不得编造；
4. suggestion 要结合项目实际情况（技术栈、描述、README 内容），不要套模板；
5. example 必须是可直接复制粘贴的优化文本；
6. 全程使用与项目描述相同的语言（项目描述为中文则用中文，否则用英文）。"""


def build_user_prompt(
    snap: RepoSnapshot,
    results: list[RuleResult],
    readme_max_chars: int = 8000,
) -> str:
    """组装用户提示：项目快照 + 扣分项检查结果。"""
    readme = snap.readme_text or ""
    if len(readme) > readme_max_chars:
        # 保留首段 + Features/FAQ（AI 最需要的段落）
        readme = readme[:readme_max_chars] + "\n…（已截断）"

    fails = [r for r in results if r.status == EvidenceStatus.FAIL]
    check_lines = [
        f"- [{r.rule_id}] {r.name}（{r.dimension}，{r.score_earned:.1f}/{r.score:.0f} 分）"
        f"\n  证据：{r.evidence}"
        f"\n  当前建议：{r.suggestion}"
        for r in fails
    ]
    check_section = "\n".join(check_lines) if check_lines else "（无未通过项）"

    topics = ", ".join(snap.topics) if snap.topics else "（空）"
    snapshot_section = f"""仓库：{snap.full_name}（{'私有' if snap.is_private else '公开'}）
描述：{snap.description or '（空）'}
Topics：{topics}
主语言：{snap.language or '（未识别）'}
许可：{snap.license_spdx or '（无）'}

README 内容（前 {readme_max_chars} 字符）：
{readme}

体检结果（仅未通过项）：
{check_section}"""

    return snapshot_section
