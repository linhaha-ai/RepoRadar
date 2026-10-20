"""AI 优化建议模块（DESIGN.md §10）。

- llm.py     OpenAI 兼容客户端
- prompts.py Prompt 组装
- schema.py  AIAdvice 数据模型 + 校验
- templates.py 规则模板建议（兜底）
- orchestrator.py 编排与降级
"""

from .orchestrator import AdviceSource, generate_advice

__all__ = ["AdviceSource", "generate_advice"]
