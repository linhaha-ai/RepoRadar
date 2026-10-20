"""AI 建议模块测试（DESIGN.md §10）。"""

from repo_seo.advice.llm import LLMError
from repo_seo.advice.orchestrator import AdviceSource, generate_advice
from repo_seo.advice.prompts import SYSTEM_PROMPT, build_user_prompt
from repo_seo.advice.schema import validate_advice
from repo_seo.rules.engine import ALL_RULES
from repo_seo.scoring import score_snapshot

from .fixtures import make_snapshot


def _known_ids() -> set[str]:
    return {r.id for r in ALL_RULES}


def test_validate_ok():
    data = {
        "advice": [
            {
                "rule_id": "R01",
                "priority": "P0",
                "problem": "首段缺失",
                "suggestion": "补充定位",
                "reason": "AI 依赖首段",
                "example": "x",
                "impact": {"dimensions": ["readme", "aeo"], "expected_gain": "+3"},
            }
        ]
    }
    out = validate_advice(data, _known_ids())
    assert len(out) == 1
    assert out[0].rule_id == "R01"
    assert out[0].impact["dimensions"] == ["readme", "aeo"]


def test_validate_drop_unknown_rule():
    data = {"advice": [
        {"rule_id": "R999", "suggestion": "x"},
        {"rule_id": "R01", "suggestion": "y"},
    ]}
    out = validate_advice(data, _known_ids())
    assert [a.rule_id for a in out] == ["R01"]


def test_validate_drop_empty_suggestion():
    data = {"advice": [{"rule_id": "R01", "suggestion": ""}]}
    assert validate_advice(data, _known_ids()) == []


def test_validate_bad_top_level():
    assert validate_advice([], _known_ids()) == []
    assert validate_advice({"advice": "not-a-list"}, _known_ids()) == []
    assert validate_advice(None, _known_ids()) == []


def test_template_when_no_llm():
    s = make_snapshot(readme_text=None)
    report = score_snapshot(s)
    res = generate_advice(s, report.results, None)
    assert res.source == AdviceSource.TEMPLATE
    assert res.advices  # 有 fail 项即有建议


def test_fallback_when_llm_fails():
    s = make_snapshot(readme_text=None)
    report = score_snapshot(s)

    class BoomLLM:
        def chat_json(self, system, user):
            raise LLMError("boom")

    res = generate_advice(s, report.results, BoomLLM())
    assert res.source == AdviceSource.TEMPLATE
    assert res.note and "AI 建议不可用" in res.note


def test_mixed_when_llm_partial():
    s = make_snapshot(readme_text=None)
    report = score_snapshot(s)
    fail_ids = [r.rule_id for r in report.results if r.status.value == "fail"]
    first = fail_ids[0]

    class FakeLLM:
        def chat_json(self, system, user):
            return {"advice": [{"rule_id": first, "suggestion": "AI fix", "priority": "P0"}]}

    res = generate_advice(s, report.results, FakeLLM())
    assert res.source == AdviceSource.MIXED
    assert any(a.rule_id == first and a.suggestion == "AI fix" for a in res.advices)
    assert len(res.advices) == len(fail_ids)


def test_ai_when_full_coverage():
    s = make_snapshot(readme_text=None)
    report = score_snapshot(s)
    fail_ids = [r.rule_id for r in report.results if r.status.value == "fail"]

    class FullLLM:
        def chat_json(self, system, user):
            return {"advice": [
                {"rule_id": rid, "suggestion": f"AI {rid}", "priority": "P0"}
                for rid in fail_ids
            ]}

    res = generate_advice(s, report.results, FullLLM())
    assert res.source == AdviceSource.AI
    assert len(res.advices) == len(fail_ids)


def test_prompt_contains_rules_and_evidence():
    s = make_snapshot(readme_text=None)
    report = score_snapshot(s)
    user = build_user_prompt(s, report.results)
    assert "R01" in SYSTEM_PROMPT          # 规则表注入系统提示
    assert "P0" in SYSTEM_PROMPT
    assert "README" in user                # 快照摘要
    assert "R01" in user                   # 扣分项证据
