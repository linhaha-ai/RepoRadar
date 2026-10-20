"""多模型 AEO 实测（V2，DESIGN.md §9）。

对配置的 OpenAI 兼容模型运行探测查询：「你是否了解 GitHub 仓库 owner/repo？」
检测回答中是否提及仓库身份，作为「模型知识中的可见度」抽样证据。

诚实标注：
- 这是「模型训练知识采样」，不是实时检索；单次回答存在随机性；
- 私有 / 冷门仓库大概率「不了解」——这是真实信号，不是失败；
- 多个模型可并行探测（REPO_SEO_PROBE_MODELS，逗号分隔）。
"""

from __future__ import annotations

from dataclasses import dataclass

from ..advice.llm import LLMClient, LLMError

_SYSTEM = (
    "You are a retrieval-evidence tester. Answer honestly based on your knowledge. "
    "If you have never seen or are not sure about the repository, say so directly. "
    "Do not guess or make things up. Reply in one or two short sentences."
)


def _build_user_prompt(owner: str, repo: str, description: str | None) -> str:
    desc = f" It is described as: {description}" if description else ""
    return (
        f"Do you know the GitHub repository {owner}/{repo}?{desc} "
        f"If you know it, briefly state what it is (one sentence). "
        f"If you do not know it, answer exactly: I do not know this repository."
    )


@dataclass
class AeoProbe:
    model: str
    mentioned: bool
    snippet: str | None
    status: str        # done / error
    error: str | None = None


def _mentioned(answer: str, owner: str, repo: str) -> bool:
    low = answer.lower()
    # 命中全名或仓库名（忽略"不知道/不了解"前缀的回答）
    if any(neg in low for neg in ("do not know", "don't know", "not aware", "不了解", "没听说过", "unknown")):
        return False
    return f"{owner.lower()}/{repo.lower()}" in low or repo.lower() in low


def probe_models(
    llm: LLMClient,
    owner: str,
    repo: str,
    description: str | None,
    models: list[str],
    temperature: float = 0.0,
) -> list[AeoProbe]:
    probes: list[AeoProbe] = []
    for model in models:
        client = llm if llm.model == model else LLMClient(
            api_key=llm.api_key, base_url=llm.base_url, model=model, timeout=llm.timeout
        )
        try:
            answer = client.chat_text(
                _SYSTEM, _build_user_prompt(owner, repo, description), temperature=temperature
            )
            answer = (answer or "").strip()
            probes.append(
                AeoProbe(
                    model=model,
                    mentioned=_mentioned(answer, owner, repo),
                    snippet=answer[:200] or None,
                    status="done",
                )
            )
        except LLMError as e:
            probes.append(AeoProbe(model=model, mentioned=False, snippet=None, status="error", error=str(e)))
    return probes
