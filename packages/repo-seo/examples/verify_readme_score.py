"""验证：给「写完新 README 的 RepoRadar」重新评分（本地快照 + 规则引擎）。

口径：只替换 README（其余元数据保持 GitHub 现状：描述/空 topics/无语言/私有/仅 LICENSE），
证明 README 优化本身带来的得分提升。
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent.parent  # github-seo
sys.path.insert(0, str(ROOT / "packages" / "repo-seo" / "src"))

from repo_seo.model import RepoSnapshot, Visibility
from repo_seo.scoring import score_snapshot

README = (ROOT / "README.md").read_text(encoding="utf-8")

snap = RepoSnapshot(
    full_name="linhaha-ai/RepoRadar",
    owner="linhaha-ai",
    name="RepoRadar",
    description="GitHub 项目搜索优化（原生搜索 + AI 大模型检索曝光，AEO）",
    topics=[],
    language=None,
    license_spdx="Apache-2.0",
    visibility=Visibility.PRIVATE,      # 保持现状：私有
    default_branch="main",
    homepage=None,
    has_pages=False,
    created_at="2026-10-01T00:00:00Z",
    pushed_at="2026-10-18T00:00:00Z",
    stars=0,
    forks=0,
    open_issues=0,
    readme_text=README,
    readme_source="local",
    root_files=["LICENSE"],
    has_license_file=True,
    has_ci=False,
    has_tests=False,
    has_gitignore=False,
    has_contributing=False,
    has_code_of_conduct=False,
    releases=[],
    contributors=[{"login": "lazyhunter9", "contributions": 1}],
    fetch_errors=[],
)

report = score_snapshot(snap)

print(f"仓库：{snap.full_name}（本地快照验证：仅替换 README）")
print(f"总分：{report.total:.1f} / 100（优化前 16.5）")
print()
print("维度得分（优化前 → 优化后）：")
baseline = {
    "readme": (0.0, 25.0),
    "metadata": (8.5, 20.0),
    "aeo": (0.0, 20.0),
    "discoverability": (0.0, 6.0),
    "health": (2.0, 10.0),
    "activity": (4.0, 7.0),
}
for dim, d in report.dimensions.items():
    before, _ = baseline[dim]
    delta = d.earned - before
    flag = "▲" if delta > 0 else ("—" if abs(delta) < 0.05 else "▼")
    print(f"  {d.label:<14} {before:>5.1f} → {d.earned:>5.1f}  {flag} {delta:+.1f}")

print()
print("README 维度明细：")
for r in report.results:
    if r.dimension == "readme":
        print(f"  [{r.status.value.upper():<8}] {r.rule_id} {r.name}: {r.score_earned:.1f}/{r.score:.0f}")

print()
print("AEO 维度明细：")
for r in report.results:
    if r.dimension == "aeo":
        print(f"  [{r.status.value.upper():<8}] {r.rule_id} {r.name}: {r.score_earned:.1f}/{r.score:.0f}")
