"""raw.githubusercontent.com 直取 README（不占用 API 配额）。

注意：部分网络环境对 raw 域名存在连接黑洞（挂起且超时不生效），
因此本模块只做「API 失败后的兜底」，并设置严格短超时 + 总预算。
"""

from __future__ import annotations

import time

import httpx

_README_NAMES = ("README.md", "readme.md", "README", "readme")

_RAW_TIMEOUT = httpx.Timeout(connect=3.0, read=6.0, write=6.0, pool=3.0)
_RAW_BUDGET_SECONDS = 10.0  # raw 阶段总预算，超预算直接放弃


def fetch_raw_readme(
    owner: str,
    repo: str,
    branch: str,
    timeout: float | None = None,
    budget: float = _RAW_BUDGET_SECONDS,
) -> tuple[str | None, str | None]:
    """尝试从 raw.githubusercontent 抓取 README。

    返回 (文本, 来源标识)。全部失败返回 (None, None)。
    受总预算约束，避免网络黑洞导致长时间挂起。
    """
    deadline = time.monotonic() + budget
    for name in _README_NAMES:
        if time.monotonic() > deadline:
            break
        url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{name}"
        try:
            resp = httpx.get(
                url,
                headers={"User-Agent": "RepoSEO-Analyzer/0.1"},
                timeout=_RAW_TIMEOUT,
                follow_redirects=True,
            )
        except httpx.HTTPError:
            continue
        if resp.status_code == 200 and resp.text.strip():
            return resp.text, f"raw:{name}"
    return None, None
