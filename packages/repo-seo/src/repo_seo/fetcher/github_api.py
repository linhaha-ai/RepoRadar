"""GitHub REST API 客户端。

- 支持 GITHUB_TOKEN（私有仓库读取 + 更高限流）；
- 未认证限流 60 次/时，触发 403 rate limit 时抛出 RateLimitError 引导配置 Token；
- 所有错误映射为可读异常，供上层诊断。
"""

from __future__ import annotations

import base64
from typing import Any

import httpx

API_BASE = "https://api.github.com"
API_VERSION = "2022-11-28"


class FetchError(Exception):
    """抓取失败（通用）。"""


class RepoNotFoundError(FetchError):
    """仓库不存在或无权访问（404 / 403 且无 rate limit）。"""


class RateLimitError(FetchError):
    """API 限流（403 rate limit exceeded）。"""


def default_timeout() -> httpx.Timeout:
    """显式分离各阶段超时；连接黑洞时保证快速失败。"""
    return httpx.Timeout(connect=5.0, read=10.0, write=10.0, pool=5.0)


class GitHubAPI:
    def __init__(self, token: str | None = None, timeout: httpx.Timeout | float | None = None) -> None:
        self.token = token
        self.timeout = default_timeout() if timeout is None else timeout

    def _headers(self) -> dict[str, str]:
        h = {
            "User-Agent": "RepoSEO-Analyzer/0.1",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": API_VERSION,
        }
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    def get(self, path: str, params: dict[str, Any] | None = None) -> dict | list:
        url = f"{API_BASE}{path}" if path.startswith("/") else f"{API_BASE}/{path}"
        try:
            resp = httpx.get(url, headers=self._headers(), params=params, timeout=self.timeout)
        except httpx.HTTPError as e:
            raise FetchError(f"网络请求失败：{e}") from e

        if resp.status_code == 200:
            return resp.json()

        if resp.status_code == 403:
            body = resp.text.lower()
            if "rate limit" in body:
                raise RateLimitError(
                    "GitHub API 限流（403 rate limit）。请通过 GITHUB_TOKEN 环境变量或 "
                    "--token 提供 Token 以提升配额并支持私有仓库。"
                )
            raise RepoNotFoundError(
                f"无权访问（403）：可能是私有仓库且未提供有效 Token，或仓库不存在。"
            )

        if resp.status_code == 404:
            raise RepoNotFoundError(f"仓库不存在或无权访问（404）：{path}")

        if resp.status_code == 401:
            raise FetchError("Token 无效或已过期（401），请检查 GITHUB_TOKEN。")

        raise FetchError(f"GitHub API 异常（{resp.status_code}）：{resp.text[:200]}")

    # ---------- 仓库元数据 ----------
    def get_repo(self, full_name: str) -> dict:
        return self.get(f"/repos/{full_name}")

    # ---------- README（API 方式，base64） ----------
    def get_readme_via_api(self, full_name: str) -> str | None:
        try:
            data = self.get(f"/repos/{full_name}/readme")
        except RepoNotFoundError:
            return None
        if isinstance(data, dict) and data.get("content"):
            return base64.b64decode(data["content"]).decode("utf-8", errors="replace")
        return None

    # ---------- 根目录文件列表 ----------
    def get_root_files(self, full_name: str, branch: str) -> list[str]:
        try:
            data = self.get(f"/repos/{full_name}/git/trees/{branch}", {"recursive": 0})
        except (RepoNotFoundError, FetchError):
            # 分支可能不叫 default_branch，退回 contents/
            try:
                data = self.get(f"/repos/{full_name}/contents")
                if isinstance(data, list):
                    return [item.get("name", "") for item in data]
            except Exception:
                pass
            return []
        if isinstance(data, dict) and isinstance(data.get("tree"), list):
            return [
                item.get("path", "")
                for item in data["tree"]
                if item.get("type") in ("blob", "tree") and "/" not in item.get("path", "")
            ]
        return []

    # ---------- Releases ----------
    def get_releases(self, full_name: str, per_page: int = 10) -> list[dict]:
        try:
            data = self.get(
                f"/repos/{full_name}/releases",
                {"per_page": per_page, "page": 1},
            )
        except (RepoNotFoundError, FetchError):
            return []
        if isinstance(data, list):
            return [
                {
                    "tag": r.get("tag_name"),
                    "name": r.get("name"),
                    "published_at": r.get("published_at"),
                    "body": (r.get("body") or "")[:500],
                }
                for r in data
            ]
        return []

    # ---------- 贡献者 ----------
    def get_contributors(self, full_name: str, per_page: int = 10) -> list[dict]:
        try:
            data = self.get(
                f"/repos/{full_name}/contributors",
                {"per_page": per_page, "page": 1},
            )
        except (RepoNotFoundError, FetchError):
            return []
        if isinstance(data, list):
            return [
                {"login": c.get("login"), "contributions": c.get("contributions")}
                for c in data
            ]
        return []
