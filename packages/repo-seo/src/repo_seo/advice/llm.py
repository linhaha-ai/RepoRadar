"""OpenAI 兼容 LLM 客户端（httpx 实现，DESIGN.md §10.5）。

支持任意 OpenAI 兼容端点：OpenAI / 火山方舟（豆包）/ DeepSeek / Ollama 等，
通过 base_url 切换。设计约束：
- 单次超时 60s，AI 阶段总预算 90s（由编排层控制）；
- 失败抛 LLMError，由编排层降级模板建议；
- 不落盘、不打印 API Key。
"""

from __future__ import annotations

import json

import httpx


class LLMError(Exception):
    """LLM 调用失败（网络/HTTP/解析）。"""


DEFAULT_BASE_URL = "https://api.openai.com/v1"
DEFAULT_MODEL = "gpt-4o-mini"


class LLMClient:
    def __init__(
        self,
        api_key: str,
        base_url: str = DEFAULT_BASE_URL,
        model: str = DEFAULT_MODEL,
        timeout: float = 60.0,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def chat_json(
        self,
        system: str,
        user: str,
        temperature: float = 0.3,
    ) -> dict:
        """请求 chat/completions，返回解析后的 JSON 对象。

        要求模型以 JSON 输出（response_format=json_object，部分端点忽略）。
        """
        content = self._chat(system, user, temperature, response_format={"type": "json_object"})
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            raise LLMError(f"LLM 响应非 JSON：{e}") from e

    def chat_text(
        self,
        system: str,
        user: str,
        temperature: float = 0.4,
    ) -> str:
        """请求 chat/completions，返回纯文本内容（不强制 JSON）。"""
        return self._chat(system, user, temperature, response_format=None)

    def _chat(
        self,
        system: str,
        user: str,
        temperature: float,
        response_format: dict | None,
    ) -> str:
        url = self.base_url
        if not url.endswith("/chat/completions"):
            url = f"{url}/chat/completions"
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
        }
        if response_format is not None:
            payload["response_format"] = response_format
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        try:
            resp = httpx.post(
                url, json=payload, headers=headers, timeout=self.timeout
            )
        except httpx.HTTPError as e:
            raise LLMError(f"LLM 网络请求失败：{e}") from e

        if resp.status_code != 200:
            raise LLMError(f"LLM 返回 {resp.status_code}: {resp.text[:200]}")

        try:
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, json.JSONDecodeError) as e:
            raise LLMError(f"LLM 响应解析失败：{e}") from e
