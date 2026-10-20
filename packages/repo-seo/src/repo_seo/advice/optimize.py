"""一键优化（Web UI 功能）：基于体检报告让 LLM 产出「可直接落地执行」的修改清单。

与 orchestrator.py 的区别：
- orchestrator：对每条 FAIL 规则给一条结构化建议（suggestion/example），是「建议」；
- 本模块：把整份报告 + 提示词交给 LLM，产出具体的可修改内容
  （README 怎么改、缺失什么文件需要补充、描述/topics 改成什么），是「执行清单」。

设计约束：
- 需要 LLM（未配置 Key 时抛 LLMError，由 Web 层提示）；
- 事实纪律：只使用快照与报告中可验证的信息，禁止模型编造仓库不存在的功能/链接/数字；
- 输出 JSON：summary + actions（type/target/what/why/concrete）+ estimated_gain；
- concrete 必须具体到可直接复制粘贴（改写段落全文 / 新文件完整模板 / 推荐字段值）。
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field

from ..model import EvidenceStatus, RepoSnapshot
from ..scoring import ScoreReport
from .llm import LLMClient, LLMError

# 允许的 action 类型（前端据此渲染徽章与配色）
ACTION_TYPES = (
    "readme",        # README 内容修改
    "file",          # 新增/修改仓库文件（LICENSE、CONTRIBUTING、.github 等）
    "metadata",      # 仓库元数据（描述、topics、主页、语言）
    "repo_settings", # 仓库设置（默认分支、Release、启用 Pages 等）
    "other",         # 其他
)

SYSTEM_PROMPT = """你是一名资深开源项目 GitHub SEO/AEO 优化顾问。你的任务是：基于仓库体检报告，产出一份**可直接落地执行**的优化方案——告诉维护者具体要改什么、改成什么样。

输出 JSON，格式（严格遵守）：
{
  "summary": "一句话总结当前最关键的问题",
  "actions": [
    {
      "type": "readme | file | metadata | repo_settings | other",
      "target": "改动对象，如 README.md / LICENSE / 仓库描述 / topics",
      "what": "要做什么改动（一句话）",
      "why": "为什么（对应哪些体检失分点/规则）",
      "concrete": "可直接复制使用的具体内容：改写后的段落或章节全文、新文件的完整内容模板、推荐的描述与 topics 列表等"
    }
  ],
  "estimated_gain": "预期可提升的分数（整数，估算，可选）"
}

要求：
1. actions 至少覆盖体检报告中所有未通过项，按优先级 P0 → P1 → P2 排序；
2. concrete 必须具体到可直接复制粘贴：README 给改写后的完整段落/章节；缺失文件给完整文件内容模板；描述/topics 给推荐值；
3. 事实纪律：只基于报告提供的信息，不得编造仓库不存在的功能、命令、链接、徽章、数字；报告未提供的安装命令或包名，写"请按实际补充"而非自创；
4. 全程使用简体中文；
5. type 含义：readme=README 内容修改；file=新增/修改仓库文件（如 LICENSE、CONTRIBUTING.md、CODE_OF_CONDUCT.md、.github/workflows、.gitignore）；metadata=仓库元数据（描述、topics、主页、语言）；repo_settings=仓库设置（默认分支、Release、启用 Pages 等）；other=其他。"""


@dataclass
class OptimizeAction:
    type: str
    target: str
    what: str
    why: str
    concrete: str


@dataclass
class OptimizePlan:
    summary: str
    actions: list[OptimizeAction]
    estimated_gain: int | None = None
    note: str | None = None


def build_optimize_prompt(
    snap: RepoSnapshot,
    report: ScoreReport,
    readme_max_chars: int = 8000,
) -> str:
    """组装一键优化提示词：仓库快照摘要 + 评分 + 未通过项明细。"""
    readme = snap.readme_text or ""
    if len(readme) > readme_max_chars:
        readme = readme[:readme_max_chars] + "\n…（已截断）"

    topics = ", ".join(snap.topics) if snap.topics else "（空）"

    dim_lines = []
    for dim, d in report.dimensions.items():
        dim_lines.append(f"- {d.label}：{d.earned:.1f} / {d.total:.0f} 分")

    fails = [r for r in report.results if r.status == EvidenceStatus.FAIL]
    fails.sort(key=lambda r: ({"P0": 0, "P1": 1, "P2": 2}.get(r.priority, 9), -(r.score - r.score_earned)))
    fail_lines = []
    for r in fails:
        fail_lines.append(
            f"- [{r.rule_id}] {r.name}（维度 {r.dimension}，{r.score_earned:.1f}/{r.score:.0f} 分，优先级 {r.priority}）"
            f"\n  原因：{r.reason}"
            f"\n  证据：{r.evidence}"
            f"\n  当前建议：{r.suggestion}"
        )
    fail_section = "\n".join(fail_lines) if fail_lines else "（无未通过项）"

    root_files = ", ".join(snap.root_files) if snap.root_files else "（空）"

    return f"""仓库：{snap.full_name}（{'私有' if snap.is_private else '公开'}，默认分支 {snap.default_branch}）
描述：{snap.description or '（空）'}
Topics：{topics}
主语言：{snap.language or '（未识别）'}
许可：{snap.license_spdx or '（无）'}
Star：{snap.stars} / Fork：{snap.forks}
首页/文档链接：{snap.homepage or '（空）'}

根目录文件：{root_files}
信号：LICENSE={'有' if snap.has_license_file else '无'} · CI={'有' if snap.has_ci else '无'} · 测试={'有' if snap.has_tests else '无'} · .gitignore={'有' if snap.has_gitignore else '无'} · CONTRIBUTING={'有' if snap.has_contributing else '无'} · CODE_OF_CONDUCT={'有' if snap.has_code_of_conduct else '无'}

README 内容（前 {readme_max_chars} 字符）：
{readme}

体检评分：总分 {report.total:.1f} / 100
六维得分：
{chr(10).join(dim_lines)}

未通过检查项（按优先级排序）：
{fail_section}"""


def generate_optimize_plan(
    snap: RepoSnapshot,
    report: ScoreReport,
    llm: LLMClient,
    retries: int = 1,
) -> OptimizePlan:
    """调用 LLM 生成优化清单；输出非法或调用失败抛 LLMError。"""
    user_prompt = build_optimize_prompt(snap, report)
    last_error: str | None = None
    for attempt in range(retries + 1):
        try:
            data = llm.chat_json(SYSTEM_PROMPT, user_prompt)
            plan = _parse_plan(data)
            if plan.actions:
                return plan
            last_error = "LLM 输出为空或未通过校验"
        except LLMError as e:
            last_error = str(e)
    raise LLMError(f"一键优化不可用（{last_error}）")


def _parse_plan(data: dict) -> OptimizePlan:
    """解析并校验 LLM 输出的 JSON。"""
    if not isinstance(data, dict):
        raise LLMError("LLM 输出非对象")

    summary = str(data.get("summary", "")).strip()
    actions_raw = data.get("actions")
    if not isinstance(actions_raw, list) or not actions_raw:
        raise LLMError("LLM 输出缺少有效 actions")

    actions: list[OptimizeAction] = []
    for a in actions_raw:
        if not isinstance(a, dict):
            continue
        atype = str(a.get("type", "other")).strip()
        if atype not in ACTION_TYPES:
            atype = "other"
        target = str(a.get("target", "")).strip()
        what = str(a.get("what", "")).strip()
        why = str(a.get("why", "")).strip()
        concrete = str(a.get("concrete", "")).strip()
        if not (target and what and concrete):
            continue
        actions.append(
            OptimizeAction(type=atype, target=target, what=what, why=why, concrete=concrete)
        )

    if not actions:
        raise LLMError("LLM 输出缺少有效 actions")

    gain = data.get("estimated_gain")
    try:
        gain_int = int(float(gain)) if gain is not None else None
    except (TypeError, ValueError):
        gain_int = None

    return OptimizePlan(
        summary=summary,
        actions=actions,
        estimated_gain=gain_int,
        note=None,
    )


def optimize_plan_to_dict(plan: OptimizePlan) -> dict:
    return {
        "summary": plan.summary,
        "estimated_gain": plan.estimated_gain,
        "note": plan.note,
        "actions": [dataclasses.asdict(a) for a in plan.actions],
    }
