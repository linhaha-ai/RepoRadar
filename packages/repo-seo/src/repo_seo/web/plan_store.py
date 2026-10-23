"""一键优化修改清单「最后一版」持久化（Web）。

每仓库覆盖写一个 JSON 文件（{历史目录}/{owner}__{repo}.plan.json），
只保留最近一次生成的清单，供深链 / 一键优化标签页直接回看（不重新调用 LLM）。
历史目录与扫描历史同目录（.repo-seo-history / REPO_SEO_HISTORY_DIR 卷），随容器持久化。
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from ..trend.history import default_history_dir


def plan_path(owner: str, repo: str, base: Path | None = None) -> Path:
    base = base or default_history_dir()
    return base / f"{owner}__{repo}.plan.json"


def save_last_plan(owner: str, repo: str, plan: dict, base: Path | None = None) -> None:
    """覆盖保存该仓库最近一次生成的修改清单（仅保留最后一版）。"""
    base = base or default_history_dir()
    base.mkdir(parents=True, exist_ok=True)
    payload = {
        "owner": owner,
        "repo": repo,
        "at": datetime.now().isoformat(timespec="seconds"),
        "plan": plan,
    }
    plan_path(owner, repo, base).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def load_last_plan(owner: str, repo: str, base: Path | None = None) -> dict | None:
    """读取最近一次保存的修改清单；不存在 / 损坏 / 结构非法 → None。"""
    p = plan_path(owner, repo, base)
    if not p.exists():
        return None
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    if not isinstance(raw, dict) or not isinstance(raw.get("plan"), dict):
        return None
    return raw
