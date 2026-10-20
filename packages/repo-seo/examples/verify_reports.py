"""验证导出的报告文件结构。"""

from pathlib import Path

EX = Path(__file__).parent

html = (EX / "reporadar_report.html").read_text(encoding="utf-8")
assert "<!DOCTYPE html>" in html and "<title>" in html
assert 'href="http' not in html and 'src="http' not in html
assert "<script" not in html
assert "维度得分" in html and "最优先修复的问题" in html and "扣分项证据清单" in html
print(f"HTML 自包含验证 OK（{len(html)} 字符）")

md = (EX / "reporadar_report.md").read_text(encoding="utf-8")
for k in [
    "# linhaha-ai/RepoRadar · 仓库可发现性评分报告",
    "总分",
    "维度得分",
    "最优先修复的问题",
    "优化建议（AI 生成）",
    "扣分项证据清单",
]:
    assert k in md, f"缺少章节：{k}"
print(f"Markdown 关键章节 OK（{len(md)} 字符）")
print("验证通过 ✅")
