"""D3 AI 检索准备度（20 分）：A01-A05 —— 本项目差异化维度。"""

from __future__ import annotations

import re

from ..model import (
    CheckType,
    RepoSnapshot,
    Rule,
    result_fail,
    result_pass,
)
from .readme_parser import parse_readme

_TECH_STACK = (
    "python", "typescript", "javascript", "node", "nodejs", "go", "golang",
    "rust", "java", "kotlin", "swift", "php", "ruby", "c++", "c#", "c",
    "react", "vue", "angular", "svelte", "django", "flask", "fastapi",
    "express", "spring", "rails", "laravel", "postgresql", "mysql", "sqlite",
    "redis", "mongodb", "docker", "kubernetes", "kubernetes", "aws", "gcp", "azure",
    "tensorflow", "pytorch", "llm", "openai", "cli", "api", "sdk",
)
_OVERCLAIM = ("最好", "最佳", "第一", "完美", "无敌", "碾压", "领先所有",
              "best", "perfect", "number one", "#1", "outperform everything")
_LIMIT_KW = ("限制", "limitation", "requirements", "要求", "compatible", "兼容",
             "requires", "支持环境", "supported", "works on", "依赖", "dependency")


def _tech_hits(text: str) -> list[str]:
    low = text.lower()
    return [t for t in _TECH_STACK if t in low]


def _check_a01(snap: RepoSnapshot):
    if not snap.has_readme:
        return result_fail(RULES[0], 0.0, "README 缺失", "AI 无内容可提取身份信息", "先创建 README", None)
    text = snap.readme_text or ""
    doc = parse_readme(snap.readme_text)
    earned = 0.0
    parts: list[str] = []
    # 身份一致性：README 含仓库名（或 owner）
    if snap.name.lower() in text.lower() or snap.owner.lower() in text.lower():
        earned += 2.0
        parts.append("项目名一致✅")
    else:
        parts.append("README 未提及项目名❌")
    # 技术栈明确：首段（前 2 段）含技术栈词
    head = " ".join(doc.paragraphs[:2]).lower()
    techs = _tech_hits(head)
    if techs:
        earned += 2.0
        parts.append(f"首段技术栈明确（{', '.join(techs[:3])}）✅")
    else:
        parts.append("首段无技术栈表述❌")
    if earned >= 4:
        return result_pass(RULES[0], "；".join(parts), "实体身份与技术栈清晰")
    return result_fail(
        RULES[0], earned, "；".join(parts),
        "AI 需要稳定识别「项目名 + 技术栈」才能正确归类与推荐",
        "README 首段明确写出项目名与技术栈", None,
    )


def _check_a02(snap: RepoSnapshot):
    if not snap.has_readme:
        return result_fail(RULES[1], 0.0, "README 缺失", "无场景表达", "先创建 README", None)
    text = (snap.readme_text or "").lower()
    scene_kw = ("use case", "use cases", "who is it for", "适用于", "适用场景",
                "适合谁", "best for", "when to use", "scenario", "场景")
    hit = next((k for k in scene_kw if k in text), None)
    if hit:
        return result_pass(RULES[1], f"命中适用场景表达：{hit}", "AI 能回答「它是什么、适合谁」")
    return result_fail(
        RULES[1], 0.0, "无 Use Cases / 适用场景段落",
        "缺少场景表达时 AI 无法匹配用户「我要做 X 用什么」类提问",
        "新增 ## Use Cases 段落，列出 3 个典型使用场景",
        "## Use Cases\n- Data pipeline monitoring: track repo activity across your team\n- OSS marketing: find weak READMEs before launch",
    )


def _check_a03(snap: RepoSnapshot):
    if not snap.has_readme:
        return result_fail(RULES[2], 0.0, "README 缺失", "无可引用内容", "先创建 README", None)
    doc = parse_readme(snap.readme_text)
    earned = 0.0
    parts: list[str] = []
    if doc.code_blocks:
        earned += 2.0
        parts.append(f"代码示例×{len(doc.code_blocks)}✅")
    else:
        parts.append("无代码示例❌")
    if doc.list_items >= 5:
        earned += 2.0
        parts.append(f"功能列表项×{doc.list_items}✅")
    elif doc.list_items >= 2:
        earned += 1.0
        parts.append(f"列表项×{doc.list_items}⚠️")
    else:
        parts.append("功能清单过少❌")
    if earned >= 4:
        return result_pass(RULES[2], "；".join(parts), "具备可被 LLM 摘引的具体内容")
    return result_fail(
        RULES[2], earned, "；".join(parts),
        "AI 引用需要「具体事实」：可执行示例 + 功能清单，缺失则无料可引",
        "补充功能列表（每条一行）与 ≥1 个带输出注释的代码示例", None,
    )


def _check_a04(snap: RepoSnapshot):
    if not snap.has_readme:
        return result_fail(RULES[3], 0.0, "README 缺失", "无结构可评估", "先创建 README", None)
    doc = parse_readme(snap.readme_text)
    earned = 0.0
    parts: list[str] = []
    h2_count = sum(1 for lv, _ in doc.headings if lv == 2)
    if h2_count >= 3:
        earned += 2.0
        parts.append(f"H2 章节×{h2_count}✅")
    else:
        parts.append(f"H2 章节×{h2_count}（建议≥3）❌")
    if doc.has_table or doc.list_items >= 3:
        earned += 2.0
        parts.append("列表/表格结构✅")
    else:
        parts.append("无可抽取结构（列表/表格）❌")
    if earned >= 4:
        return result_pass(RULES[3], "；".join(parts), "文档语义组织清晰，AI 易抽取")
    return result_fail(
        RULES[3], earned, "；".join(parts),
        "LLM 偏爱结构化内容（表格/列表/独立短段），长散文难以被准确引用",
        "用 H2 分章节 + 列表/表格承载功能、参数、对比", None,
    )


def _check_a05(snap: RepoSnapshot):
    if not snap.has_readme:
        return result_fail(RULES[4], 0.0, "README 缺失", "无法评估一致性", "先创建 README", None)
    text = snap.readme_text or ""
    low = text.lower()
    earned = 0.0
    parts: list[str] = []
    claims = [k for k in _OVERCLAIM if k in low]
    if claims:
        parts.append(f"夸大表述：{', '.join(claims[:3])}❌")
    else:
        earned += 2.0
        parts.append("无夸大表述✅")
    limits = [k for k in _LIMIT_KW if k in low]
    if limits:
        earned += 2.0
        parts.append(f"限制/兼容说明（{', '.join(limits[:3])}）✅")
    else:
        parts.append("无限制/兼容性说明❌")
    if earned >= 4:
        return result_pass(RULES[4], "；".join(parts), "信息一致且诚实")
    return result_fail(
        RULES[4], earned, "；".join(parts),
        "夸大表述降低 AI 信任；缺少限制说明让 AI 无法判断适用边界",
        "删除夸大词；补充支持平台/版本要求/已知限制", None,
    )


RULES: list[Rule] = [
    Rule("A01", "aeo", "实体与项目身份清晰度", 4.0, CheckType.SEMANTIC, "P0",
         "README 含项目名且首段明确技术栈", _check_a01, confidence=0.85),
    Rule("A02", "aeo", "功能与适用场景表达", 4.0, CheckType.SEMANTIC, "P1",
         "含 Use Cases / 适用场景段落", _check_a02, confidence=0.9),
    Rule("A03", "aeo", "可引用的事实与示例", 4.0, CheckType.SEMANTIC, "P1",
         "有代码示例 + 功能清单", _check_a03, confidence=0.8),
    Rule("A04", "aeo", "结构化文档与语义组织", 4.0, CheckType.HARD, "P1",
         "H2 章节 ≥3 且有列表/表格", _check_a04),
    Rule("A05", "aeo", "信息一致性与限制说明", 4.0, CheckType.SEMANTIC, "P1",
         "无夸大词且有限制/兼容说明", _check_a05, confidence=0.85),
]
