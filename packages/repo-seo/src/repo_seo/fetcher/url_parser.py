"""GitHub 仓库 URL 解析：支持多种输入形式，统一输出 (owner, repo)。"""

from __future__ import annotations

import re

_GITHUB_COM = re.compile(r"^https?://github\.com/([^/\s]+)/([^/\s#?]+)", re.IGNORECASE)
_GIT_SSH = re.compile(r"^git@github\.com:([^/\s]+)/([^/\s#?]+)", re.IGNORECASE)
_SHORT = re.compile(r"^([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)$")


def strip_git_suffix(name: str) -> str:
    return name[:-4] if name.endswith(".git") else name


def parse_github_url(url: str) -> tuple[str, str]:
    """解析 GitHub 仓库 URL/标识，返回 (owner, repo)。

    支持：
      https://github.com/owner/repo[.git]
      git@github.com:owner/repo[.git]
      owner/repo

    无法识别时抛出 ValueError（含原因）。
    """
    if not url or not url.strip():
        raise ValueError("仓库地址为空")

    text = url.strip()
    m = _GITHUB_COM.match(text)
    if m:
        return m.group(1), strip_git_suffix(m.group(2))

    m = _GIT_SSH.match(text)
    if m:
        return m.group(1), strip_git_suffix(m.group(2))

    m = _SHORT.match(text)
    if m:
        return m.group(1), strip_git_suffix(m.group(2))

    raise ValueError(
        f"无法识别的 GitHub 仓库地址：{url!r}（支持 https://github.com/owner/repo、"
        "git@github.com:owner/repo.git、owner/repo）"
    )
