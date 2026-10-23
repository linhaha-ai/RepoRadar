"""README 草稿生成测试（--readme-draft）。"""

from repo_seo.advice.llm import LLMError
from repo_seo.advice.readme_gen import (
    README_TARGET_RULES,
    build_user_prompt,
    generate_readme_draft,
    strip_code_fence,
)
from repo_seo.advice.schema import AIAdvice
from repo_seo.scoring import score_snapshot

from .fixtures import make_snapshot


def test_strip_code_fence():
    assert strip_code_fence("```markdown\n# Hi\n```") == "# Hi"
    assert strip_code_fence("```\n# Hi\n```\n") == "# Hi"
    assert strip_code_fence("# Hi") == "# Hi"


def test_build_prompt_contains_facts_and_advice():
    s = make_snapshot(readme_text=None)
    report = score_snapshot(s)
    advices = [
        AIAdvice(
            rule_id="R01", priority="P0", problem="定位缺失",
            suggestion="补充定位", reason="首段",
            impact={"dimensions": ["readme"]},
        )    ]
    user = build_user_prompt(s, report.results, advices)
    assert "owner/repo" in user            # 仓库名
    assert "A CLI tool" in user            # 描述
    assert "README 内容质量" in user        # 评分模型表
    assert "[R01]" in user                 # AI 建议
    assert "（未设置）" in user             # 缺失事实以占位说明


def test_build_prompt_total_matches_score_report():
    s = make_snapshot()
    report = score_snapshot(s)
    user = build_user_prompt(s, report.results, [])
    assert f"总分 {report.total:.1f}/100" in user
    assert f"总分 {sum(r.score_earned for r in report.results):.1f}/100" not in user


def test_generate_uses_only_target_rules():
    s = make_snapshot(readme_text=None)
    report = score_snapshot(s)
    advices = [
        AIAdvice(rule_id="R01", priority="P0", problem="x", suggestion="a", reason="r"),
        AIAdvice(rule_id="H02", priority="P1", problem="y", suggestion="b", reason="r"),
    ]
    # 无 LLM 应抛错
    try:
        generate_readme_draft(s, report.results, advices, None)
        assert False, "无 LLM 时应抛 LLMError"
    except LLMError:
        pass


def test_generate_ok_with_fake_llm():
    s = make_snapshot(readme_text=None)
    report = score_snapshot(s)
    advices = [
        AIAdvice(rule_id="R01", priority="P0", problem="x", suggestion="fix it", reason="r"),
    ]

    class FakeLLM:
        def chat_text(self, system, user, temperature=0.4):
            return "```markdown\n# My Repo\n\nGreat README.\n```"

    res = generate_readme_draft(s, report.results, advices, FakeLLM())
    assert res.content == "# My Repo\n\nGreat README."
    assert "R01" in res.rule_ids_used
    assert "H02" not in res.rule_ids_used


def test_target_rules_definition():
    assert {"R01", "R05", "A05", "D05"} <= README_TARGET_RULES
    # 工程健康/活跃度不直接进入 README 建议
    assert "H01" not in README_TARGET_RULES
    assert "AC01" not in README_TARGET_RULES
