"""一键优化模块测试（Web UI 功能）。"""

from repo_seo.advice.llm import LLMError
from repo_seo.advice.optimize import (
    build_optimize_prompt,
    generate_optimize_plan,
    optimize_plan_to_dict,
)
from repo_seo.scoring import score_snapshot

from .fixtures import make_snapshot


class FakeLLM:
    def __init__(self, payload):
        self.payload = payload

    def chat_json(self, system, user, temperature=0.3):
        self.last_system = system
        self.last_user = user
        return self.payload


def test_build_optimize_prompt_contains_key_info():
    s = make_snapshot()
    report = score_snapshot(s)
    prompt = build_optimize_prompt(s, report)
    assert s.full_name in prompt
    assert "总分" in prompt
    assert "未通过检查项" in prompt
    assert "README 内容" in prompt
    # 根目录文件与工程信号应出现在提示词中
    assert "根目录文件" in prompt


def test_generate_optimize_plan_ok():
    s = make_snapshot(readme_text=None)
    report = score_snapshot(s)
    llm = FakeLLM(
        {
            "summary": "README 缺少价值主张与安装示例",
            "estimated_gain": 18,
            "actions": [
                {
                    "type": "readme",
                    "target": "README.md",
                    "what": "重写开头段落",
                    "why": "R01 失分",
                    "concrete": "# MyTool\n\nMyTool 是一个……",
                },
                {
                    "type": "file",
                    "target": "LICENSE",
                    "what": "补充许可证",
                    "why": "H01 失分",
                    "concrete": "MIT License\n\nCopyright (c) ……",
                },
            ],
        }
    )
    plan = generate_optimize_plan(s, report, llm)
    assert len(plan.actions) == 2
    assert plan.actions[0].type == "readme"
    assert plan.actions[1].concrete.startswith("MIT License")
    assert plan.estimated_gain == 18

    d = optimize_plan_to_dict(plan)
    assert d["summary"]
    assert d["actions"][0]["target"] == "README.md"


def test_generate_optimize_plan_drops_bad_type_and_missing_fields():
    s = make_snapshot()
    report = score_snapshot(s)
    llm = FakeLLM(
        {
            "summary": "ok",
            "actions": [
                {"type": "hack", "target": "X", "what": "w", "why": "", "concrete": "c"},
                {"type": "metadata", "target": "desc", "what": "w", "why": "", "concrete": ""},
                {"type": "file", "target": "Y", "what": "w", "why": "y", "concrete": "c"},
            ],
        }
    )
    plan = generate_optimize_plan(s, report, llm)
    # hack 类型归为 other；缺 concrete 的丢弃
    assert len(plan.actions) == 2
    assert {a.type for a in plan.actions} == {"other", "file"}


def test_generate_optimize_plan_raises_on_invalid():
    s = make_snapshot()
    report = score_snapshot(s)
    llm = FakeLLM({"summary": "x", "actions": []})
    try:
        generate_optimize_plan(s, report, llm)
        assert False, "应当抛出 LLMError"
    except LLMError:
        pass


def test_generate_optimize_plan_raises_on_llm_error():
    s = make_snapshot()
    report = score_snapshot(s)

    class ErrLLM:
        def chat_json(self, system, user, temperature=0.3):
            raise LLMError("网络失败")

    try:
        generate_optimize_plan(s, report, ErrLLM(), retries=0)
        assert False, "应当抛出 LLMError"
    except LLMError:
        pass
