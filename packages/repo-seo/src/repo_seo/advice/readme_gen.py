"""README 草稿生成（正式功能，DESIGN.md §10.7 扩展）。

输入：RepoSnapshot（自动提取真实事实）+ 规则结果 + AI 建议（R/A/D05 相关）。
输出：英文 README 草稿 Markdown（由 OpenAI 兼容 LLM 生成）。

设计约束：
- 事实纪律：只使用快照中可验证的信息，禁止模型编造包名/命令/链接/徽章；
- 需要 LLM（无 LLM 时抛 LLMError，由 CLI 提示配置）；
- 只落实与 README 直接相关的建议（R01-R05 / A01-A05 / D05）。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..model import EvidenceStatus, RepoSnapshot, RuleResult
from ..rules.engine import DIMENSION_LABELS
from .llm import LLMClient, LLMError
from .schema import AIAdvice

# README 写作需要落实的建议（R=README、A=AEO、D05=链接）
README_TARGET_RULES = {
    "R01", "R02", "R03", "R04", "R05",
    "A01", "A02", "A03", "A04", "A05",
    "D05",
}

SYSTEM_PROMPT = """你是资深开源维护者 + GitHub SEO/AEO 顾问。请根据【项目真实事实】和【AI 体检建议】撰写一份可直接发布的英文 README.md。

硬性要求：
1. 事实纪律（最高优先级）：只使用【项目真实事实】中明确给出的信息。禁止编造包名、命令、链接、数字、徽章、截图、文档站地址、分数；事实中出现的所有数字（如体检总分）必须原文照抄，不得改写。若事实中没有安装命令或包名，Installation 章节必须写诚实的占位说明（如 "installation instructions will be added when the first package release is published"），禁止自创命令
2. 结构：H1 → H2 → H3 标准层级，至少 5 个 H2 章节（建议：Overview / Features / Installation / Usage / Scoring Model / FAQ / Limitations），代码块必须带语言标注
3. AEO：首段 ≥60 词，说清「是什么 / 解决什么问题 / 目标用户」；关键词 GitHub search optimization、AEO、LLM retrieval、repository discoverability、SEO score 自然出现 3 次以上，禁止堆砌
4. FAQ：3~5 个真实问题与诚实回答（可围绕：评分是否等于真实排名、私有仓库怎么用、AI 建议怎么开启、是否支持任意语言仓库、如何安装）
5. Limitations：诚实说明限制（静态审计≠排名、私有仓库受限、AI 需要 API Key 等，以事实为准）
6. 语言：英文（全球开源曝光最大化）；【评分模型】表中维度为中文标签，必须翻译为英文再写入；若仓库描述为中文，需翻译为准确英文
7. 输出：完整 Markdown 正文，不要任何前后解释文字，不要用代码块包裹整个文件"""


# RepoRadar 工具自身能力事实：仅当被扫描仓库就是 RepoRadar 自身时注入
# （此时 Installation/Usage 可写真实命令；其他仓库禁止使用本段信息）
REPORADAR_SELF_FACTS = """- 工具自身能力（仅当被扫描仓库是 RepoRadar 自身时可写入 README，这是该仓库的真实产品事实）：
  - 技术栈：Python 3.10+；httpx（GitHub REST API / raw / 网页三级降级抓取）；typer（CLI）；markdown-it-py + beautifulsoup4（README 语义解析）；可选 OpenAI 兼容 LLM 客户端
  - 安装（当前真实可用）：git clone https://github.com/linhaha-ai/RepoRadar.git 后 cd RepoRadar && pip install -e ".[dev]"；PyPI 发布规划中（尚未发布，禁止写 pip install repo-seo 为已发布）
  - 扫描命令（真实）：repo-seo scan <repository-url>；等价 python -m repo_seo.cli scan <repository-url>
  - 常用选项（真实）：--ai（启用 AI 优化建议）、--no-ai、--json 导出结构化报告、--readme-draft（生成 README 草稿）、--model / --base-url（指定 LLM）
  - 环境变量（真实）：GITHUB_TOKEN（私有仓库访问）、REPO_SEO_API_KEY / REPO_SEO_BASE_URL / REPO_SEO_MODEL（LLM 配置）
  - 测试：单元测试覆盖抓取 / 规则 / 评分 / AI 建议模块"""


@dataclass
class ReadmeDraftResult:
    content: str
    rule_ids_used: list[str] = field(default_factory=list)


def _dimension_table() -> str:
    lines = [
        "| Dimension | Max Points |",
        "|---|---|",
    ]
    for dim, label in DIMENSION_LABELS.items():
        lines.append(f"| {label} | {_dim_total(dim)} |")
    return "\n".join(lines)


def _dim_total(dim: str) -> int:
    from ..rules import engine  # 避免循环导入

    return int(engine.DIMENSION_TOTAL[dim])


def _facts(snap: RepoSnapshot, results: list[RuleResult]) -> str:
    """从快照自动提取真实事实（禁止模型编造的边界）。"""
    f: list[str] = []
    f.append(
        f"- 项目名：{snap.name}；GitHub 仓库：{snap.full_name}"
        f"（{'私有仓库' if snap.is_private else '公开仓库'}，默认分支 {snap.default_branch}，"
        f"许可 {snap.license_spdx or '未设置'}）"
    )
    f.append(f"- 仓库描述：{snap.description or '（仓库未设置描述）'}")
    f.append(f"- Topics：{', '.join(snap.topics) if snap.topics else '（未设置）'}")
    f.append(f"- 主语言：{snap.language or '（未识别）'}")
    f.append(f"- 首页/文档链接：{snap.homepage or '（未设置）'}")
    f.append(f"- Stars：{snap.stars}  Forks：{snap.forks}  开源 Issue：{snap.open_issues}")
    if snap.has_readme:
        f.append("- README 现状：已存在（可基于现有内容重写增强）")
    else:
        f.append("- README 现状：缺失（本次为首次创建）")
    f.append(f"- 根目录文件：{', '.join(snap.root_files) if snap.root_files else '（无）'}")
    signals = []
    if snap.has_license_file:
        signals.append("LICENSE")
    if snap.has_ci:
        signals.append("CI")
    if snap.has_tests:
        signals.append("tests")
    if snap.has_gitignore:
        signals.append(".gitignore")
    if snap.has_contributing:
        signals.append("CONTRIBUTING")
    if snap.has_code_of_conduct:
        signals.append("CoC")
    f.append(f"- 工程信号：{', '.join(signals) if signals else '（无额外工程信号）'}")
    if snap.package_meta:
        f.append(f"- 包元信息：{snap.package_meta}")
    f.append(f"- Releases：{len(snap.releases)}  贡献者数：{len(snap.contributors)}")
    if snap.fetch_errors:
        f.append(f"- 抓取告警：{'; '.join(snap.fetch_errors)}")
    return "\n".join(f)


def _advice_lines(advices: list[AIAdvice]) -> str:
    picked = [a for a in advices if a.rule_id in README_TARGET_RULES]
    if not picked:
        return "（无可用建议，请依据事实自行组织内容）"
    lines = []
    for a in picked:
        lines.append(f"- [{a.rule_id}] {a.problem}\n  建议：{a.suggestion}")
    return "\n".join(lines)


def build_user_prompt(
    snap: RepoSnapshot,
    results: list[RuleResult],
    advices: list[AIAdvice],
) -> str:
    total = _score_total(results)
    self_facts = ""
    if snap.full_name.lower() == "linhaha-ai/reporadar":
        self_facts = f"\n\n{REPORADAR_SELF_FACTS}"
    else:
        self_facts = (
            "\n\n【诚实占位要求】本仓库事实中没有任何安装命令/包名/命令信息，"
            "Installation 与 Usage 章节必须写诚实的占位说明，禁止编造命令。"
        )
    return f"""{_facts(snap, results)}
{self_facts}

【评分模型】（6 维度共 100 分，维度标签为中文，写入 README 时必须翻译为英文）
{_dimension_table()}

【本工具体检结果】总分 {total:.1f}/100（此数字必须原文照抄，禁止改写）。

【AI 体检建议】（README 写作必须落实的建议）
{_advice_lines(advices)}
"""


def _score_total(results: list[RuleResult]) -> float:
    """与 score_snapshot 一致：按可评分值归一化到 0–100。

    不能只累加 score_earned——各维度满分合计为 100，但 N/A / UNKNOWN
    会改变可评分值，直接求和会得到 60 多分并误导 README 中的自评分。
    """
    earned = sum(r.score_earned for r in results)
    eligible = sum(
        r.score
        for r in results
        if r.status not in (EvidenceStatus.N_A, EvidenceStatus.UNKNOWN)
    )
    return earned / eligible * 100 if eligible else 0.0


def strip_code_fence(content: str) -> str:
    """去掉模型可能添加的整体 ```markdown 包裹。"""
    text = content.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text


def generate_readme_draft(
    snap: RepoSnapshot,
    results: list[RuleResult],
    advices: list[AIAdvice],
    llm: LLMClient | None,
    temperature: float = 0.4,
) -> ReadmeDraftResult:
    """生成 README 草稿；无 LLM 或调用失败时抛 LLMError。"""
    if llm is None:
        raise LLMError("未配置 LLM：README 草稿生成需要 OpenAI 兼容 API Key（REPO_SEO_API_KEY）")
    user = build_user_prompt(snap, results, advices)
    content = llm.chat_text(SYSTEM_PROMPT, user, temperature=temperature)
    return ReadmeDraftResult(
        content=strip_code_fence(content),
        rule_ids_used=[a.rule_id for a in advices if a.rule_id in README_TARGET_RULES],
    )
