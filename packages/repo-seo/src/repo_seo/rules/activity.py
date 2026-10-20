"""D6 项目活跃度（10 分）：AC01-AC04。

设计约束（DESIGN.md §6.2 D6）：
- 活跃度不数 commit：按项目类型与发布周期动态评估；
- 无 issue 历史 → UNKNOWN（不误判"处理快"或"没人用"）。
"""

from __future__ import annotations

from datetime import datetime, timezone

from ..model import (
    CheckType,
    RepoSnapshot,
    Rule,
    result_fail,
    result_pass,
    result_unknown,
)


def _days_ago(iso: str | None) -> int | None:
    if not iso:
        return None
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return max(0, int((datetime.now(timezone.utc) - dt).total_seconds() // 86400))
    except ValueError:
        return None


def _repo_age_days(snap: RepoSnapshot) -> int | None:
    return _days_ago(snap.created_at)


def _check_ac01(snap: RepoSnapshot, params: dict | None = None):
    pushed = _days_ago(snap.pushed_at)
    p = params or {}
    new_threshold = p.get("new_threshold", 90)
    mature_threshold = p.get("mature_threshold", 180)
    age_cutoff = p.get("age_cutoff", 365)
    if pushed is None:
        return result_unknown(RULES[0], "无法解析 pushed_at", "缺少最近推送数据", "确认仓库已提交代码")
    age = _repo_age_days(snap)
    threshold = new_threshold if (age is not None and age < age_cutoff) else mature_threshold
    if pushed <= threshold:
        return result_pass(
            RULES[0], f"最近推送 {pushed} 天前（阈值 {threshold} 天）",
            "维护活跃，按项目阶段动态评估",
        )
    if pushed <= threshold * 2:
        return result_fail(
            RULES[0], 1.5, f"最近推送 {pushed} 天前（阈值 {threshold} 天）",
            "更新间隔偏长，搜索与 AI 会判定项目维护放缓",
            "保持周期性小提交与更新", None,
        )
    return result_fail(
        RULES[0], 0.0, f"最近推送 {pushed} 天前（阈值 {threshold} 天）",
        "长期未更新，可发现性与信任度显著下降",
        "恢复维护并发布新版本", None,
    )


def _check_ac02(snap: RepoSnapshot):
    open_issues = snap.open_issues
    if open_issues <= 0:
        return result_unknown(
            RULES[1],
            "open_issues = 0（无法区分「从未开 issue」与「已全部处理」）",
            "缺少 issue 历史数据，不做「无人使用」或「响应迅速」的误判",
            "开启 Issues 并保持响应；或补充 issue 历史后复检",
        )
    if open_issues <= 3:
        return result_pass(RULES[1], f"Open Issues ×{open_issues}（少且可控）", "Issue 池健康")
    if open_issues <= 15:
        return result_fail(
            RULES[1], 2.0, f"Open Issues ×{open_issues}",
            "积压 issue 偏多，用户与 AI 会怀疑维护响应",
            "清理并回复存量 issue，建立 triage 节奏", None,
        )
    return result_fail(
        RULES[1], 1.0, f"Open Issues ×{open_issues}",
        "大量未处理 issue 是明显的维护停滞信号",
        "优先关闭/回复历史 issue", None,
    )


def _check_ac03(snap: RepoSnapshot):
    if not snap.releases:
        return result_fail(
            RULES[2], 0.0, "无 Release",
            "无版本发布节奏，AI 与用户难以确认项目在演进",
            "发布语义化版本并写 Release Notes", None,
        )
    latest = snap.releases[0]
    days = _days_ago(latest.get("published_at"))
    if days is None:
        return result_unknown(RULES[2], "无法解析最近 Release 时间", "缺发布时间数据", "补充 Release 发布时间")
    if days <= 180:
        return result_pass(RULES[2], f"最近 Release {days} 天前（{latest.get('tag')}）", "版本更新及时")
    return result_fail(
        RULES[2], 1.0, f"最近 Release {days} 天前",
        "发布间隔过长，演进信号弱",
        "发布新版本，保持合理的发布节奏", None,
    )


def _check_ac04(snap: RepoSnapshot):
    n = len(snap.contributors)
    if n >= 2:
        return result_pass(RULES[3], f"贡献者 ×{n}", "多人协作信号")
    if n == 1:
        if snap.has_contributing:
            return result_pass(RULES[3], "贡献者 ×1 但有 CONTRIBUTING", "已有协作引导")
        return result_fail(
            RULES[3], 1.0, "贡献者 ×1 且无 CONTRIBUTING",
            "单人项目缺乏协作入口，社区参与度低",
            "添加 CONTRIBUTING.md 引导贡献，或邀请协作者", None,
        )
    return result_fail(
        RULES[3], 0.0, "无贡献者记录",
            "无任何贡献记录（可能未提交代码）",
            "先完成首次提交；添加 CONTRIBUTING.md", None,
    )


RULES: list[Rule] = [
    Rule("AC01", "activity", "近期有效维护", 3.0, CheckType.HARD, "P1",
         "按项目年龄动态阈值内保持推送（<1 年看 90 天，≥1 年看 180 天）", _check_ac01),
    Rule("AC02", "activity", "Issue 处理与响应", 3.0, CheckType.HARD, "P1",
         "有 issue 历史且积压可控；无历史 → UNKNOWN", _check_ac02),
    Rule("AC03", "activity", "Release 与版本更新", 2.0, CheckType.HARD, "P2",
         "180 天内有 Release", _check_ac03),
    Rule("AC04", "activity", "贡献活动与协作", 2.0, CheckType.HARD, "P2",
         "贡献者 ≥2 或有 CONTRIBUTING", _check_ac04),
]
