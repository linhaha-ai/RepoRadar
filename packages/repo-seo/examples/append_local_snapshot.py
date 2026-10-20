"""演示趋势：追加一条「本地快照」记录（README 优化后规则引擎真实重评分 68.8）。

数据来自 examples/verify_readme_score.py 的真实计算结果（仅替换 README 后重评分），
source 标注为 local-snapshot 以示与 monitor 在线扫描区分。
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(ROOT / "packages" / "repo-seo" / "src"))

from datetime import datetime

from repo_seo.model import RepoSnapshot, Visibility
from repo_seo.scoring import score_snapshot
from repo_seo.trend import HistoryStore, SnapshotRecord
from repo_seo.trend.history import DimensionSnapshot

README = (ROOT / "README.md").read_text(encoding="utf-8")

snap = RepoSnapshot(
    full_name="linhaha-ai/RepoRadar",
    owner="linhaha-ai",
    name="RepoRadar",
    description="GitHub 项目搜索优化（原生搜索 + AI 大模型检索曝光，AEO）",
    topics=[],
    language=None,
    license_spdx="Apache-2.0",
    visibility=Visibility.PRIVATE,
    default_branch="main",
    homepage=None,
    has_pages=False,
    created_at="2026-10-01T00:00:00Z",
    pushed_at="2026-10-18T00:00:00Z",
    stars=0, forks=0, open_issues=0,
    readme_text=README,
    readme_source="local",
    root_files=["LICENSE"],
    has_license_file=True,
    has_ci=False, has_tests=False, has_gitignore=False,
    has_contributing=False, has_code_of_conduct=False,
    releases=[],
    contributors=[{"login": "lazyhunter9", "contributions": 1}],
    fetch_errors=[],
)

report = score_snapshot(snap)
store = HistoryStore()
store.append(
    SnapshotRecord(
        at=datetime.now().isoformat(timespec="seconds"),
        total=report.total,
        dimensions={
            dim: DimensionSnapshot(earned=d.earned, eligible=d.eligible, total=d.total)
            for dim, d in report.dimensions.items()
        },
        url="https://github.com/linhaha-ai/RepoRadar",
        source="local-snapshot",
        note="本地快照：仅替换 README（AI 生成版）后的规则引擎重评分",
    ),
    "linhaha-ai",
    "RepoRadar",
)
print(f"已追加本地快照记录：总分 {report.total:.1f}")
