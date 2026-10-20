"""Google 收录检查（V2，DESIGN.md §9）。

使用 Google Custom Search JSON API（免费额度 100 次/天）执行
`site:github.com/{owner}/{repo}` 查询，核验仓库页面是否被 Google 收录。

- 未配置 GOOGLE_CSE_API_KEY / GOOGLE_CSE_ID → UNKNOWN（沿用 D02 语义，不误判）
- 查询成功：total_results > 0 → indexed；= 0 → not_indexed
- API 调用失败 → error（附错误信息，报告如实展示）
"""

from __future__ import annotations

from dataclasses import dataclass

import httpx

CSE_URL = "https://www.googleapis.com/customsearch/v1"


@dataclass
class GoogleIndexCheck:
    status: str            # indexed / not_indexed / unknown / error
    total_results: int | None = None
    top_url: str | None = None
    evidence: str = ""
    error: str | None = None


def check_google_index(
    owner: str,
    repo: str,
    api_key: str | None = None,
    cse_id: str | None = None,
    timeout: float = 15.0,
) -> GoogleIndexCheck:
    if not (api_key and cse_id):
        return GoogleIndexCheck(
            status="unknown",
            evidence=(
                "未配置 GOOGLE_CSE_API_KEY / GOOGLE_CSE_ID，无法核验收录（保持 UNKNOWN，"
                "不将「未检测」误判为「未收录」）"
            ),
        )
    query = f"site:github.com/{owner}/{repo}"
    try:
        resp = httpx.get(
            CSE_URL,
            params={"key": api_key, "cx": cse_id, "q": query, "num": 3},
            timeout=timeout,
        )
    except httpx.HTTPError as e:
        return GoogleIndexCheck(status="error", evidence=f"Google API 请求失败：{e}")

    if resp.status_code != 200:
        return GoogleIndexCheck(
            status="error",
            evidence=f"Google API 返回 {resp.status_code}: {resp.text[:200]}",
        )

    try:
        data = resp.json()
        total = int(data.get("searchInformation", {}).get("totalResults", 0))
        items = data.get("items", [])
        top = items[0].get("link") if items else None
    except (ValueError, KeyError) as e:
        return GoogleIndexCheck(status="error", evidence=f"Google API 响应解析失败：{e}")

    if total > 0:
        return GoogleIndexCheck(
            status="indexed",
            total_results=total,
            top_url=top,
            evidence=f"site: 查询命中 {total} 个结果（{query}）",
        )
    return GoogleIndexCheck(
        status="not_indexed",
        total_results=0,
        evidence=f"site: 查询无结果（{query}）——注意：未收录判定仅基于本次查询，可能受索引延迟影响",
    )
