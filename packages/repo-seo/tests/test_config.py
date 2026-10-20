"""规则配置化测试（--config / TOML / 动态维度满分）。"""

import pytest

from repo_seo.rules.config import (
    ConfigError,
    apply_config,
    default_config_toml,
    load_config,
)
from repo_seo.rules.engine import ALL_RULES, applied_rules, run_rules
from repo_seo.scoring import score_snapshot

from .fixtures import GOOD_README, make_snapshot

KNOWN = {r.id for r in ALL_RULES}


def _write(tmp_path, content: str):
    p = tmp_path / "rules.toml"
    p.write_text(content, encoding="utf-8")
    return p


def test_load_config_basic(tmp_path):
    p = _write(
        tmp_path,
        "[rules.R01]\nenabled = true\nscore = 6.0\npriority = \"P0\"\nparams = { min_chars = 80 }\n",
    )
    cfg = load_config(p, KNOWN)
    assert cfg["R01"].score == 6.0
    assert cfg["R01"].priority == "P0"
    assert cfg["R01"].params == {"min_chars": 80}


def test_load_config_unknown_rule(tmp_path):
    p = _write(tmp_path, "[rules.XX99]\nenabled = true\n")
    with pytest.raises(ConfigError, match="未知规则"):
        load_config(p, KNOWN)


def test_load_config_bad_param(tmp_path):
    p = _write(tmp_path, "[rules.R01]\nparams = { nope = 1 }\n")
    with pytest.raises(ConfigError, match="不支持参数"):
        load_config(p, KNOWN)


def test_load_config_bad_toml(tmp_path):
    p = _write(tmp_path, "[rules.R01\nbroken")
    with pytest.raises(ConfigError, match="TOML 解析失败"):
        load_config(p, KNOWN)


def test_apply_config_disable_and_override():
    cfg = {"R01": __import__("repo_seo.rules.config", fromlist=["RuleConfig"]).RuleConfig(enabled=False)}
    rules = apply_config(ALL_RULES, cfg)
    assert all(r.id != "R01" for r in rules)
    assert len(rules) == len(ALL_RULES) - 1

    cfg2 = {"M02": __import__("repo_seo.rules.config", fromlist=["RuleConfig"]).RuleConfig(score=8.0, priority="P1")}
    rules2 = apply_config(ALL_RULES, cfg2)
    m02 = next(r for r in rules2 if r.id == "M02")
    assert m02.score == 8.0 and m02.priority == "P1"


def test_score_with_disabled_rule_changes_dimension_total():
    from repo_seo.rules.config import RuleConfig

    s = make_snapshot()
    # 禁用 R01（README 维度 -5 分）
    cfg = {"R01": RuleConfig(enabled=False)}
    report = score_snapshot(s, cfg)
    assert report.dimensions["readme"].total == 20.0
    assert all(r.rule_id != "R01" for r in report.results)
    assert any("自定义规则配置" in w for w in report.warnings)


def test_threshold_param_takes_effect():
    from repo_seo.rules.config import RuleConfig

    # 首段很短（MINIMAL_README 第一段 "A small test."）
    s = make_snapshot(readme_text="# My Project\n\nA small test.")
    base = score_snapshot(s)
    # 默认 min_chars=60 → 首段过短（fail）
    r01_default = next(r for r in base.results if r.rule_id == "R01")
    assert r01_default.status.value == "fail"

    # min_chars=1 → 首段 12 字符 ≥1 → pass（但含弱词？"A small test." 无弱词）
    cfg = {"R01": RuleConfig(params={"min_chars": 1})}
    report = score_snapshot(s, cfg)
    r01 = next(r for r in report.results if r.rule_id == "R01")
    assert r01.status.value == "pass"


def test_metadata_threshold_effect():
    from repo_seo.rules.config import RuleConfig

    s = make_snapshot(topics=["cli"])  # 只有 1 个 topic
    base = score_snapshot(s)
    m03 = next(r for r in base.results if r.rule_id == "M03")
    assert m03.status.value == "fail"  # 默认 min_topics=6 → 不足

    cfg = {"M03": RuleConfig(params={"min_topics": 1})}
    report = score_snapshot(s, cfg)
    m03b = next(r for r in report.results if r.rule_id == "M03")
    assert m03b.status.value == "pass"


def test_default_config_keeps_baseline():
    """无配置时数值与基准一致（动态维度满分 = 权重）。"""
    s = make_snapshot(readme_text=GOOD_README)
    report = score_snapshot(s)
    assert report.dimensions["readme"].total == 25.0
    assert report.dimensions["metadata"].total == 20.0
    assert report.dimensions["aeo"].total == 20.0
    assert report.dimensions["discoverability"].total == 15.0
    assert report.dimensions["health"].total == 10.0
    assert report.dimensions["activity"].total == 10.0
    assert not report.warnings  # 默认无告警


def test_run_rules_with_config_passes_params():
    from repo_seo.rules.config import RuleConfig

    s = make_snapshot(readme_text="# My Project\n\nA small test.")
    cfg = {"R01": RuleConfig(params={"min_chars": 1})}
    results = run_rules(s, cfg)
    r01 = next(r for r in results if r.rule_id == "R01")
    assert r01.status.value == "pass"


def test_export_template_contains_all_rules_and_params(tmp_path):
    toml = default_config_toml([r.id for r in ALL_RULES], ALL_RULES)
    assert all(f"[rules.{r.id}]" in toml for r in ALL_RULES)
    assert "min_chars" in toml and "max_desc_chars" in toml and "new_threshold" in toml
    # 导出的模板应能被重新加载
    p = tmp_path / "exported.toml"
    p.write_text(toml, encoding="utf-8")
    cfg = load_config(p, KNOWN)
    assert len(cfg) == len(ALL_RULES)
