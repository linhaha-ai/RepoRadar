"""降级通道：网页抓取（GitHub 页面）解析 description / topics。

仅在 API 与 raw 均不可用时启用。M1 实现最小版，解析失败返回 None 并记录原因。
"""

from __future__ import annotations

import httpx
from bs4 import BeautifulSoup

_WEB_TIMEOUT = httpx.Timeout(connect=5.0, read=10.0, write=10.0, pool=5.0)


def fetch_via_web(
    owner: str,
    repo: str,
    timeout: httpx.Timeout | None = None,
) -> dict | None:
    """抓取 https://github.com/owner/repo 页面，提取 description 与 topics。

    返回 {"description": str | None, "topics": list[str]}；失败返回 None。
    """
    url = f"https://github.com/{owner}/{repo}"
    try:
        resp = httpx.get(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept-Language": "en-US,en;q=0.9",
            },
            timeout=_WEB_TIMEOUT if timeout is None else timeout,
            follow_redirects=True,
        )
    except httpx.HTTPError:
        return None
    if resp.status_code != 200:
        return None

    soup = BeautifulSoup(resp.text, "html.parser")
    result: dict = {"description": None, "topics": []}

    meta = soup.find("meta", {"name": "description"})
    if meta and meta.get("content"):
        result["description"] = meta["content"].strip()

    for a in soup.select("a.topic-tag"):
        text = a.get_text(strip=True)
        if text:
            result["topics"].append(text)

    return result
