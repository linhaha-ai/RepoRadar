"""规则配置（规则可配置化，DESIGN.md §6.4 扩展）。

TOML 配置支持三件事：
1. 启用/禁用规则（enabled）
2. 覆盖分值（score）与优先级（priority）
3. 覆盖阈值参数（params，仅部分规则支持，见 DEFAULT_PARAMS）

示例（rules.toml）：
    [rules.R01]
    enabled = true
    score = 6.0
    priority = "P0"
    params = { min_chars = 80 }
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field, replace
from pathlib import Path

from ..model import Rule

# 可参数化规则及其参数定义：id -> {key: {"default": 默认值, "desc": 说明}}
DEFAULT_PARAMS: dict[str, dict[str, dict]] = {
    "R01": {
        "min_chars": {"default": 60, "desc": "README 首段最小字符数"},
    },
    "R02": {
        "min_hits": {"default": 3, "desc": "核心词最小命中次数"},
        "max_hits": {"default": 30, "desc": "核心词堆砌阈值（超过判定堆砌）"},
    },
    "M02": {
        "max_desc_chars": {"default": 350, "desc": "Description 最大字符数"},
    },
    "M03": {
        "min_topics": {"default": 6, "desc": "Topics 推荐数量下限"},
        "max_topics": {"default": 20, "desc": "Topics GitHub 硬上限"},
    },
    "AC01": {
        "new_threshold": {"default": 90, "desc": "新项目（<1 年）最近推送阈值天数"},
        "mature_threshold": {"default": 180, "desc": "成熟项目最近推送阈值天数"},
        "age_cutoff": {"default": 365, "desc": "新/成熟项目分界天数"},
    },
}


class ConfigError(Exception):
    """规则配置加载/校验失败。"""


@dataclass
class RuleConfig:
    enabled: bool = True
    score: float | None = None      # None = 使用默认分值
    priority: str | None = None     # None = 使用默认优先级
    params: dict = field(default_factory=dict)


def load_config(path: str | Path, known_rule_ids: set[str]) -> dict[str, RuleConfig]:
    """加载 TOML 配置文件；未知规则 / 非法字段报 ConfigError。"""
    p = Path(path)
    if not p.exists():
        raise ConfigError(f"配置文件不存在：{p}")
    try:
        raw = tomllib.loads(p.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as e:
        raise ConfigError(f"TOML 解析失败（{p.name}）：{e}") from e

    section = raw.get("rules")
    if section is None:
        raise ConfigError("配置缺少 [rules] 段")

    config: dict[str, RuleConfig] = {}
    for rule_id, item in section.items():
        if rule_id not in known_rule_ids:
            raise ConfigError(f"未知规则 id：{rule_id}（合法规则见 repo-seo rules）")
        if not isinstance(item, dict):
            raise ConfigError(f"规则 {rule_id} 配置必须是表（table）")
        rc = RuleConfig()
        if "enabled" in item:
            if not isinstance(item["enabled"], bool):
                raise ConfigError(f"规则 {rule_id}.enabled 必须是布尔值")
            rc.enabled = item["enabled"]
        if "score" in item:
            s = item["score"]
            if not isinstance(s, (int, float)) or s < 0:
                raise ConfigError(f"规则 {rule_id}.score 必须是非负数字")
            rc.score = float(s)
        if "priority" in item:
            pr = str(item["priority"]).upper()
            if pr not in {"P0", "P1", "P2"}:
                raise ConfigError(f"规则 {rule_id}.priority 必须是 P0/P1/P2")
            rc.priority = pr
        if "params" in item:
            if not isinstance(item["params"], dict):
                raise ConfigError(f"规则 {rule_id}.params 必须是表（table）")
            allowed = set(DEFAULT_PARAMS.get(rule_id, {}))
            unknown = set(item["params"]) - allowed
            if unknown:
                raise ConfigError(
                    f"规则 {rule_id} 不支持参数：{', '.join(sorted(unknown))}"
                    f"（支持：{', '.join(sorted(allowed)) or '无'}）"
                )
            rc.params = dict(item["params"])
        config[rule_id] = rc
    return config


def apply_config(rules: list[Rule], config: dict[str, RuleConfig]) -> list[Rule]:
    """把配置应用到规则列表：过滤禁用项、覆盖分值/优先级。"""
    out: list[Rule] = []
    for r in rules:
        rc = config.get(r.id)
        if rc is None:
            out.append(r)
            continue
        if not rc.enabled:
            continue
        new_score = rc.score if rc.score is not None else r.score
        new_priority = rc.priority if rc.priority is not None else r.priority
        if new_score == r.score and new_priority == r.priority:
            out.append(r)
        else:
            out.append(replace(r, score=new_score, priority=new_priority))
    return out


def params_for(rule_id: str, config: dict[str, RuleConfig] | None) -> dict | None:
    """取该规则最终生效的参数（None=无需传参）。"""
    if not config:
        return None
    rc = config.get(rule_id)
    if rc is None or not rc.params:
        return None
    return dict(rc.params)


def default_config_toml(known_rule_ids: list[str], rules: list[Rule]) -> str:
    """导出默认配置模板（全部规则 + 可配参数说明）。"""
    lines = ["# RepoRadar 规则配置模板（repo-seo rules --export-config）", ""]
    lines.append("# 1) 启用/禁用：enabled = true / false（禁用后该规则不计分，维度满分随之变化）")
    lines.append("# 2) 覆盖分值：score = 6.0（自定义配置下维度满分 = 启用规则分值之和）")
    lines.append("# 3) 覆盖优先级：priority = \"P0\"")
    lines.append("# 4) 阈值参数：params = { key = value }（仅下方标注 * 的规则支持）")
    lines.append("")
    for r in rules:
        lines.append(f"[rules.{r.id}]")
        lines.append(f"# {r.name}（{r.dimension}，默认 {r.score:.0f} 分，{r.priority}，{r.check_type.value}）")
        lines.append(f"# 通过条件：{r.pass_condition}")
        lines.append("enabled = true")
        param_defs = DEFAULT_PARAMS.get(r.id)
        if param_defs:
            lines.append("# 可配参数：")
            for key, meta in param_defs.items():
                lines.append(f"#   {key} = {meta['default']}  # {meta['desc']}")
        lines.append("")
    return "\n".join(lines)
