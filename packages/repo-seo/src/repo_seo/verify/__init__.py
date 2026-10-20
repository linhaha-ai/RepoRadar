"""V2 外部验证层（DESIGN.md §9）。

- google.py    Google 收录检查（Custom Search JSON API；未配置 → UNKNOWN）
- aeo_probe.py 多模型 AEO 实测（复用 OpenAI 兼容 LLM，检测模型是否知道该仓库）
- orchestrator.py 汇总 VerificationResult

铁律（DESIGN.md §10.8）：外部验证是「Search Visibility Evidence」，
与静态评分（GitHub SEO Score / AEO Readiness）分开呈现，不混入总分。
"""

from .orchestrator import VerificationResult, run_external_verification

__all__ = ["VerificationResult", "run_external_verification"]
