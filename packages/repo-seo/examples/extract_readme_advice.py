"""提取 RepoRadar AI 建议中 README 相关项（R 系列 + A 系列 + D05）。"""

import json

with open(
    r"E:\code-workspace\ai-code\github-seo\packages\repo-seo\examples\reporadar_ai_score.json",
    encoding="utf-8",
) as f:
    d = json.load(f)

targets = {"R01", "R02", "R03", "R04", "R05", "A01", "A02", "A03", "A04", "A05", "D05"}
for a in d["advice"]["items"]:
    if a["rule_id"] in targets:
        print(f"[{a['rule_id']}] {a['problem']}")
        print(f"  建议: {a['suggestion']}")
        if a.get("example"):
            print(f"  示例: {a['example'][:300]}")
