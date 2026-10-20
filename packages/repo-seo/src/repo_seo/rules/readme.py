"""D1 README 内容质量（25 分）：R01-R05。"""

from __future__ import annotations

import re

from ..model import (
    CheckType,
    EvidenceStatus,
    RepoSnapshot,
    Rule,
    result_fail,
    result_pass,
)
from .readme_parser import parse_readme

# 弱词：定位不明的表述
_WEAK_WORDS = (
    "练习项目", "测试项目", "学习项目", "待更新", "正在开发", "占位",
    "placeholder", "todo", "tbd", "just for fun", "demo project", "test project",
)
# 安装命令正则
_INSTALL_RE = re.compile(
    r"\b(pip install|npm install|yarn add|pnpm add|cargo install|go install|"
    r"brew install|apt install|apt-get install|pipenv install|poetry add|"
    r"composer require|gem install|docker pull|git clone)\b",
    re.IGNORECASE,
)
# 英文停用词（关键词提取时过滤）
_STOPWORDS = {
    "the", "and", "for", "with", "that", "this", "from", "your", "you",
    "are", "was", "were", "has", "have", "its", "into", "more", "than",
    "will", "can", "use", "using", "used", "make", "made", "like", "just",
    "not", "but", "all", "any", "our", "their", "his", "her", "them",
    "about", "after", "before", "between", "over", "under", "again",
}


def _extract_keywords(snapshot: RepoSnapshot) -> list[str]:
    """从 topics + description 提取核心词（英文词 ≥3 字符，过滤停用词）。"""
    kws: list[str] = []
    for t in snapshot.topics:
        for w in re.split(r"[^a-zA-Z0-9]+", t):
            if len(w) >= 3 and w.lower() not in _STOPWORDS:
                kws.append(w.lower())
    if snapshot.description:
        for w in re.split(r"[^a-zA-Z]+", snapshot.description):
            if len(w) >= 3 and w.lower() not in _STOPWORDS:
                kws.append(w.lower())
    return list(dict.fromkeys(kws))


def _first_paragraph_after_h1(doc) -> str | None:
    """H1 之后的第一段文本（项目定位核心区）。"""
    if not doc.headings:
        return doc.paragraphs[0] if doc.paragraphs else None
    first_h1_idx = next((i for i, (lv, _) in enumerate(doc.headings) if lv == 1), None)
    if first_h1_idx is None:
        return doc.paragraphs[0] if doc.paragraphs else None
    return doc.paragraphs[0] if doc.paragraphs else None


def _check_r01(snap: RepoSnapshot, params: dict | None = None):
    doc = parse_readme(snap.readme_text)
    para = _first_paragraph_after_h1(doc)
    min_chars = (params or {}).get("min_chars", 60)
    if not snap.has_readme or not para:
        return result_fail(
            RULES[0], 0.0, "README 缺失或首段为空",
            "AI 与 GitHub 搜索把 README 首段当作项目定位的第一信息源",
            "在 H1 标题后补充一段：项目是什么 + 解决什么问题 + 目标用户",
            "RepoRadar is a CLI tool that scans any GitHub repo and reports its "
            "search & AI discoverability issues with actionable fixes.",
        )
    low = para.lower()
    if len(para) >= min_chars and not any(w in low for w in _WEAK_WORDS):
        return result_pass(RULES[0], f"README 首段（{len(para)} 字符）：{para[:80]}…", "首段清晰说明定位")
    if len(para) < min_chars:
        return result_fail(
            RULES[0], 2.0, f"首段过短（{len(para)} 字符，阈值 {min_chars}）：{para[:80]}",
            "首段过短无法传达「是什么+解决什么」，AI 摘要时会丢失核心语义",
            f"扩写首段至 {min_chars} 字符以上，说清用途与痛点",
        )
    return result_fail(
        RULES[0], 2.0, f"首段含弱词：{para[:80]}",
        "弱词（练习/待更新/placeholder）会让 GitHub 与 AI 判定项目定位不明确",
        "删除弱词，用具体能力描述替代",
    )


def _check_r02(snap: RepoSnapshot, params: dict | None = None):
    doc = parse_readme(snap.readme_text)
    text = (snap.readme_text or "").lower()
    p = params or {}
    min_hits = p.get("min_hits", 3)
    max_hits = p.get("max_hits", 30)
    if not snap.has_readme:
        return result_fail(RULES[1], 0.0, "README 缺失", "无内容可供关键词匹配", "先创建 README", None)
    kws = _extract_keywords(snap)
    if not kws:
        return result_fail(
            RULES[1], 2.0, "无可提取核心词（description/topics 为空）",
            "缺少关键词锚点，GitHub 搜索与 AI 无法判断项目主题",
            "先补齐 Description 与 Topics，再在 README 中自然覆盖", None,
        )
    hits = {k: text.count(k) for k in kws if text.count(k) > 0}
    total_hits = sum(hits.values())
    if total_hits >= max_hits:
        return result_fail(
            RULES[1], 4.0, f"核心词总出现 {total_hits} 次（堆砌风险，阈值 {max_hits}）",
            "关键词过度重复会被判定堆砌而降权",
            "减少重复，改用同义表达（如 monitor / track / watch）", None,
        )
    if total_hits >= min_hits:
        matched = ", ".join(f"{k}×{n}" for k, n in list(hits.items())[:5])
        return result_pass(RULES[1], f"核心词命中：{matched}", "关键词自然覆盖")
    return result_fail(
        RULES[1], 2.0, f"核心词命中不足（{total_hits} 次，需 ≥{min_hits}，关键词：{', '.join(kws[:5])}）",
        "核心用途缺少关键词与同义词覆盖，搜索相关性弱",
        "在 Features/FAQ 中自然覆盖核心词与 2 种以上同义表达", None,
    )


def _check_r03(snap: RepoSnapshot):
    if not snap.has_readme:
        return result_fail(RULES[2], 0.0, "README 缺失", "无安装/示例内容", "先创建 README", None)
    doc = parse_readme(snap.readme_text)
    has_install = bool(_INSTALL_RE.search(snap.readme_text or ""))
    coded_blocks = [b for b in doc.code_blocks if b]
    earned = 0.0
    parts: list[str] = []
    if has_install:
        earned += 2.5
        parts.append("安装命令✅")
    else:
        parts.append("安装命令❌")
    if coded_blocks:
        earned += 2.5
        parts.append(f"带语言代码示例×{len(coded_blocks)}✅")
    else:
        parts.append("代码示例❌")
    if earned >= 5:
        return result_pass(RULES[2], "；".join(parts), "可复制安装命令 + 带语言示例齐全")
    return result_fail(
        RULES[2], earned, "；".join(parts),
        "缺少可直接执行的安装/示例，用户与 AI 无法验证项目可用性",
        "补充一行复制即用的安装命令 + 最小可运行代码示例（标注语言）", None,
    )


def _check_r04(snap: RepoSnapshot):
    if not snap.has_readme:
        return result_fail(RULES[3], 0.0, "README 缺失", "无结构可言", "先创建 README", None)
    doc = parse_readme(snap.readme_text)
    h1s = [t for lv, t in doc.headings if lv == 1]
    earned = 0.0
    parts: list[str] = []
    # H1 唯一
    if len(h1s) == 1:
        earned += 1.5
        parts.append("H1 唯一✅")
    elif not h1s:
        parts.append("无 H1❌")
    else:
        earned += 0.5
        parts.append(f"H1×{len(h1s)}（应唯一）⚠️")
    # 标题层级连续（h1->h2->h3 不跳级）
    levels = [lv for lv, _ in doc.headings]
    ok = True
    prev = 1
    for lv in levels:
        if lv - prev > 1:
            ok = False
            break
        prev = lv
    earned += 1.5 if ok else 0.5
    parts.append("层级连续✅" if ok else "层级跳级⚠️")
    # 代码块语言标注（无代码块视为满分）
    if doc.code_blocks:
        ratio = sum(1 for b in doc.code_blocks if b) / len(doc.code_blocks)
        earned += 2.0 * ratio
        parts.append(f"代码块标注 {ratio:.0%}")
    else:
        earned += 2.0
        parts.append("无代码块（不扣分）")
    if earned >= 5:
        return result_pass(RULES[3], "；".join(parts), "README 结构完整")
    return result_fail(
        RULES[3], earned, "；".join(parts),
        "标题层级/代码标注问题影响 AI 结构化抽取",
        "保持 H1→H2→H3 层级连续；代码块标注语言（```python）", None,
    )


def _check_r05(snap: RepoSnapshot):
    if not snap.has_readme:
        return result_fail(RULES[4], 0.0, "README 缺失", "无 AEO 内容", "先创建 README", None)
    doc = parse_readme(snap.readme_text)
    headings = doc.heading_texts()
    aeo_kw = (
        "faq", "frequently asked", "常见问题", "use case", "使用场景", "适用",
        "who is it for", "适合", "limitation", "限制", "definition", "定义",
        "require", "要求", "compatible", "兼容", "support", "支持",
    )
    hit = next((h for h in headings if any(k in h for k in aeo_kw)), None)
    if hit:
        return result_pass(RULES[4], f"命中 AEO 段落：{hit}", "含 FAQ/场景/限制等 AI 友好内容")
    return result_fail(
        RULES[4], 0.0, "无 FAQ / 使用场景 / 限制说明段落",
        "问句式 FAQ 最容易被 ChatGPT/Perplexity 直接摘引回答用户，缺失将失去被 AI 引用的机会",
        "新增 ## FAQ（问句标题，如 Does it support Windows?）与 Use Cases 段",
        "## FAQ\n### Does it support Windows?\nYes, RepoRadar runs on Windows / macOS / Linux.",
    )


RULES: list[Rule] = [
    Rule("R01", "readme", "项目定位与价值主张", 5.0, CheckType.SEMANTIC, "P0",
         "README 首段 ≥60 字符且说明是什么+解决什么", _check_r01, confidence=0.85),
    Rule("R02", "readme", "关键词与语义覆盖", 5.0, CheckType.SEMANTIC, "P0",
         "核心词自然出现 ≥3 次且无堆砌", _check_r02, confidence=0.8),
    Rule("R03", "readme", "快速开始与使用示例", 5.0, CheckType.HARD, "P0",
         "有可复制安装命令 + ≥1 个带语言代码示例", _check_r03),
    Rule("R04", "readme", "内容结构与链接完整性", 5.0, CheckType.HARD, "P1",
         "H1 唯一、层级连续、代码块有语言标注", _check_r04),
    Rule("R05", "readme", "AEO 友好内容", 5.0, CheckType.SEMANTIC, "P1",
         "含 FAQ/使用场景/限制说明之一", _check_r05, confidence=0.85),
]
