"""D2 仓库元数据（20 分）：M01-M05。"""

from __future__ import annotations

import re

from ..model import (
    CheckType,
    RepoSnapshot,
    Rule,
    result_fail,
    result_pass,
)

_BAD_NAME_PREFIX = ("my-", "demo-", "test-", "tmp-", "new-", "learn-")
_GENERIC_WORDS = {"app", "project", "tool", "test", "demo", "my", "new",
                  "website", "site", "code", "stuff", "thing", "repo", "github"}
# 中文字符占比检测
_CJK_RE = re.compile(r"[\u4e00-\u9fff]")


def _name_words(name: str) -> list[str]:
    return [w.lower() for w in re.split(r"[^a-zA-Z0-9]+", name) if w]


def _check_m01(snap: RepoSnapshot):
    name = snap.name
    length_ok = 3 <= len(name) <= 40
    bad_prefix = name.lower().startswith(_BAD_NAME_PREFIX) or name.lower() in (
        "test", "demo", "project", "my-project", "myproject", "new-project"
    )
    desc_kws = set(
        w.lower() for w in re.split(r"[^a-zA-Z]+", snap.description or "")
        if len(w) >= 3
    )
    shared = [w for w in _name_words(name) if w in desc_kws or w not in _GENERIC_WORDS]
    if length_ok and not bad_prefix and shared:
        return result_pass(
            RULES[0],
            f"名称「{name}」长度合法、无泛化词，与描述共享词：{', '.join(shared[:3])}",
            "仓库名是搜索与 AI 的第一标题信号",
        )
    problems: list[str] = []
    if not length_ok:
        problems.append("长度超出 3~40")
    if bad_prefix:
        problems.append("含 my-/demo-/test- 等泛化前缀")
    if not shared:
        problems.append("名称无领域词（与描述无关联）")
    return result_fail(
        RULES[0], 0.0, "；".join(problems) or "名称不规范",
        "无意义/泛化名称无法被关键词检索命中",
        "改为「关键词-连字符」形式，如 fast-python-csv-parser", None,
    )


def _check_m02(snap: RepoSnapshot, params: dict | None = None):
    desc = snap.description
    max_chars = (params or {}).get("max_desc_chars", 350)
    earned = 0.0
    parts: list[str] = []
    if desc and desc.strip():
        earned += 2.0
        parts.append("非空✅")
        if len(desc) <= max_chars:
            earned += 1.0
            parts.append(f"≤{max_chars}✅")
        else:
            parts.append(f"长度 {len(desc)} 超限（阈值 {max_chars}）❌")
        # 核心词前置：前 80 字符含 topics/名称词
        head = desc[:80].lower()
        key_src = [w.lower() for w in _name_words(snap.name)] + [t.lower() for t in snap.topics]
        if any(k and k in head for k in key_src):
            earned += 1.5
            parts.append("核心词前置✅")
        else:
            parts.append("核心词未前置❌")
        # 英文优先：ASCII 字母占比
        ascii_letters = sum(1 for c in desc if c.isascii() and c.isalpha())
        ratio = ascii_letters / max(len(desc), 1)
        if ratio >= 0.3:
            earned += 1.5
            parts.append("英文为主✅")
        else:
            earned += 0.5
            parts.append("全中文（英文优先建议）⚠️")
    else:
        parts.append("描述为空❌")

    if earned >= 6:
        return result_pass(RULES[1], "；".join(parts), "Description 规范")
    return result_fail(
        RULES[1], earned, "；".join(parts),
        "Description 是 GitHub 搜索摘要、Google 标题与 AI 读取的第一信息来源",
        "一句话能力 + 技术栈 + 痛点，核心词前置，≤350 字符（英文优先）",
        "Lightweight TypeScript ORM for SQLite, zero dependencies, supports migration and batch insert.",
    )


def _check_m03(snap: RepoSnapshot, params: dict | None = None):
    topics = snap.topics
    p = params or {}
    min_topics = p.get("min_topics", 6)
    max_topics = p.get("max_topics", 20)
    if not topics:
        return result_fail(
            RULES[2], 0.0, "Topics 为空",
            "无 Topics 时 GitHub 与 AI 无法进行主题归类与相关搜索匹配",
            f"添加 {min_topics}~{max_topics} 个精准标签（大类 + 技术栈 + 场景长尾）",
            "typescript, sqlite, orm, database, nodejs, migration, zero-dependency",
        )
    if len(topics) > max_topics:
        return result_fail(
            RULES[2], 1.0, f"Topics 共 {len(topics)} 个（超 {max_topics} 上限）",
            f"GitHub 限制 {max_topics} 个，超限标签会被忽略",
            f"删减至 ≤{max_topics} 个精准标签", None,
        )
    earned = 2.0
    parts = [f"非空×{len(topics)}✅"]
    if len(topics) >= min_topics:
        earned += 2.0
        parts.append("数量充足✅")
    elif len(topics) >= min_topics - 2:
        earned += 1.5
        parts.append("数量一般⚠️")
    elif len(topics) >= 2:
        earned += 1.0
        parts.append("数量偏少⚠️")
    else:
        earned += 0.5
        parts.append("数量过少⚠️")
    # 相关度：topics 与 description 关键词重叠
    desc_words = set(
        w.lower() for w in re.split(r"[^a-zA-Z]+", snap.description or "")
        if len(w) >= 3
    )
    overlap = sum(1 for t in topics if any(w in t.lower() for w in desc_words) or t.lower() in desc_words)
    ratio = overlap / len(topics)
    if ratio >= 0.5:
        earned += 2.0
        parts.append("语义相关✅")
    elif ratio >= 0.2:
        earned += 1.0
        parts.append("部分相关⚠️")
    else:
        parts.append("存在无关标签❌")
    if earned >= 6:
        return result_pass(RULES[2], "；".join(parts), "Topics 精准且相关")
    return result_fail(
        RULES[2], earned, "；".join(parts),
        "无关/宽泛标签稀释主题相关性，GitHub 与 AI 均会降低匹配",
        "只保留与项目主题强相关的标签，删除无关词", None,
    )


def _check_m04(snap: RepoSnapshot):
    if snap.language:
        return result_pass(RULES[3], f"主语言：{snap.language}", "技术栈可被识别")
    return result_fail(
        RULES[3], 0.0, "language 未识别（仓库无代码提交）",
        "无主语言时项目类别定位缺失，相关技术栈搜索无法命中",
        "提交至少一个代码文件（如 src/main.py）让 GitHub 识别语言", None,
    )


def _check_m05(snap: RepoSnapshot):
    hp = snap.homepage
    if hp and hp.startswith(("http://", "https://")):
        return result_pass(RULES[4], f"Homepage：{hp}", "项目入口存在（可达性由 D05 核验）")
    return result_fail(
        RULES[4], 0.0, "未设置 Homepage",
        "缺少官网/文档/演示入口，用户与 AI 少一个信任与理解通道",
        "在仓库 Settings 的 Website 填入官网或 GitHub Pages 地址", None,
    )


RULES: list[Rule] = [
    Rule("M01", "metadata", "仓库名称", 4.0, CheckType.HARD, "P1",
         "名称 3~40 字符、无泛化前缀、含领域词", _check_m01),
    Rule("M02", "metadata", "Description", 6.0, CheckType.HARD, "P0",
         "非空、≤350、核心词前置、英文优先", _check_m02),
    Rule("M03", "metadata", "Topics", 6.0, CheckType.SEMANTIC, "P0",
         "1~20 个、≥6 最佳、与主题语义相关", _check_m03, confidence=0.85),
    Rule("M04", "metadata", "主语言与分类定位", 2.0, CheckType.HARD, "P2",
         "language 非空", _check_m04),
    Rule("M05", "metadata", "官网/文档/演示链接", 2.0, CheckType.HARD, "P2",
         "Homepage 非空且为 http(s)", _check_m05),
]
