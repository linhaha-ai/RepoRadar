"""外部验证编排（V2，DESIGN.md §9）。

汇总 Google 收录检查 + 多模型 AEO 实测 → VerificationResult。
所有结果均标注「已验证 / 未发现证据 / 无法检测」，不混入静态总分。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from ..advice.llm import LLMClient
from ..model import RepoSnapshot
from .aeo_probe import AeoProbe, probe_models
from .google import GoogleIndexCheck, check_google_index


@dataclass
class VerificationResult:
    google: GoogleIndexCheck
    probes: list[AeoProbe]
    ran_at: str
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "google": {
                "status": self.google.status,
                "total_results": self.google.total_results,
                "top_url": self.google.top_url,
                "evidence": self.google.evidence,
                "error": self.google.error,
            },
            "aeo_probes": [
                {
                    "model": p.model,
                    "mentioned": p.mentioned,
                    "snippet": p.snippet,
                    "status": p.status,
                    "error": p.error,
                }
                for p in self.probes
            ],
            "ran_at": self.ran_at,
            "notes": self.notes,
        }


def run_external_verification(
    snap: RepoSnapshot,
    llm: LLMClient | None = None,
    google_key: str | None = None,
    google_cse: str | None = None,
    probe_models_list: list[str] | None = None,
) -> VerificationResult:
    notes: list[str] = []
    google = check_google_index(snap.owner, snap.name, google_key, google_cse)

    probes: list[AeoProbe] = []
    if llm is None:
        notes.append("未配置 LLM（REPO_SEO_API_KEY），跳过 AEO 模型探测")
    else:
        models = probe_models_list or [llm.model]
        probes = probe_models(llm, snap.owner, snap.name, snap.description, models)
        notes.append(
            "AEO 探测为「模型训练知识采样」，非实时检索；单次回答存在随机性，"
            "不代表真实曝光度"
        )

    if google.status == "unknown":
        notes.append(google.evidence)

    return VerificationResult(
        google=google,
        probes=probes,
        ran_at=datetime.now().isoformat(timespec="seconds"),
        notes=notes,
    )
