"""RepoSnapshot：仓库统一数据模型。

抓取层负责把不同来源（GitHub API / raw / 网页 / 本地）的数据归一化到该结构，
规则引擎与评分只依赖此模型，不关心数据从哪来。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class Visibility(str, Enum):
    PUBLIC = "public"
    PRIVATE = "private"


@dataclass
class RepoSnapshot:
    # ---------- 基础元数据 ----------
    full_name: str                    # owner/name
    owner: str
    name: str
    description: str | None = None    # About 描述
    topics: list[str] = field(default_factory=list)
    language: str | None = None       # 主语言
    license_spdx: str | None = None   # SPDX 标识（如 MIT）
    visibility: Visibility = Visibility.PUBLIC
    default_branch: str = "main"
    homepage: str | None = None
    has_pages: bool = False
    archived: bool = False

    created_at: str | None = None
    pushed_at: str | None = None
    updated_at: str | None = None

    stars: int = 0
    forks: int = 0
    open_issues: int = 0
    watchers: int = 0

    # ---------- README ----------
    readme_text: str | None = None
    readme_source: str | None = None  # api / raw / web / local / none

    # ---------- 工程信号 ----------
    root_files: list[str] = field(default_factory=list)
    has_license_file: bool = False
    has_ci: bool = False
    has_tests: bool = False
    has_gitignore: bool = False
    has_contributing: bool = False
    has_code_of_conduct: bool = False
    package_meta: dict = field(default_factory=dict)  # package.json / pyproject.toml 关键字段

    # ---------- 活跃度 ----------
    releases: list[dict] = field(default_factory=list)
    contributors: list[dict] = field(default_factory=list)

    # ---------- 抓取过程信息 ----------
    fetch_errors: list[str] = field(default_factory=list)
    fetched_at: str = field(
        default_factory=lambda: datetime.now().isoformat(timespec="seconds")
    )

    # ---------- 便捷属性 ----------
    @property
    def has_readme(self) -> bool:
        return bool(self.readme_text and self.readme_text.strip())

    @property
    def is_private(self) -> bool:
        return self.visibility == Visibility.PRIVATE
