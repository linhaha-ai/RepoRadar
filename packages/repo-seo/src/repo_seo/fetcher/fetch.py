"""抓取编排：把多来源数据归一化为 RepoSnapshot。

优先级链：GitHub API（元数据）→ API readme → raw readme → 网页降级。
任何单点失败不阻断整体，错误记录进 fetch_errors。
"""

from __future__ import annotations

from ..model import RepoSnapshot, Visibility
from .fallback import fetch_via_web
from .github_api import GitHubAPI
from .raw_reader import fetch_raw_readme


def _to_visibility(private: bool) -> Visibility:
    return Visibility.PRIVATE if private else Visibility.PUBLIC


def _detect_health_flags(root_files: list[str]) -> dict:
    lowered = {f.lower() for f in root_files}
    ci_patterns = (
        ".github/workflows",
        "azure-pipelines.yml",
        "azure-pipelines.yaml",
        ".gitlab-ci.yml",
        ".circleci",
        "jenkinsfile",
        "appveyor.yml",
        "buildspec.yml",
    )
    test_patterns = (
        "test",
        "tests",
        "__tests__",
        "spec",
        "specs",
        "jest.config",
        "pytest.ini",
        "tox.ini",
        "coverage.xml",
    )
    return {
        "has_license_file": any(f.lower().startswith("license") for f in root_files),
        "has_ci": any(any(p in f for p in ci_patterns) for f in root_files),
        "has_tests": any(any(t in f for t in test_patterns) for f in root_files),
        "has_gitignore": ".gitignore" in lowered,
        "has_contributing": any(f.lower().startswith("contributing") for f in root_files),
        "has_code_of_conduct": any(
            "code_of_conduct" in f.lower() for f in root_files
        ),
    }


def fetch_snapshot(
    owner: str,
    repo: str,
    token: str | None = None,
    timeout: float = 30.0,
) -> RepoSnapshot:
    api = GitHubAPI(token=token, timeout=timeout)
    full_name = f"{owner}/{repo}"
    errors: list[str] = []

    # 1. 元数据（必须成功；失败则无法继续）
    meta = api.get_repo(full_name)
    branch = meta.get("default_branch") or "main"

    # 2. README：API → raw → 网页降级
    readme_text: str | None = None
    readme_source: str | None = None
    try:
        readme_text = api.get_readme_via_api(full_name)
        if readme_text:
            readme_source = "api"
    except Exception as e:
        errors.append(f"README(api): {e}")

    if not readme_text:
        try:
            # raw 兜底：自带总预算（10s），避免 raw 域名连接黑洞拖垮整体
            text, source = fetch_raw_readme(owner, repo, branch)
            if text:
                readme_text, readme_source = text, source
        except Exception as e:
            errors.append(f"README(raw): {e}")

    # 3. 根文件列表 + 工程健康信号
    root_files: list[str] = []
    try:
        root_files = api.get_root_files(full_name, branch)
    except Exception as e:
        errors.append(f"root_files: {e}")
    health = _detect_health_flags(root_files)

    # 4. 活跃度信号（轻量，失败不阻断）
    releases: list[dict] = []
    contributors: list[dict] = []
    try:
        releases = api.get_releases(full_name)
    except Exception as e:
        errors.append(f"releases: {e}")
    try:
        contributors = api.get_contributors(full_name)
    except Exception as e:
        errors.append(f"contributors: {e}")

    snapshot = RepoSnapshot(
        full_name=full_name,
        owner=owner,
        name=repo,
        description=meta.get("description"),
        topics=list(meta.get("topics") or []),
        language=meta.get("language"),
        license_spdx=(meta.get("license") or {}).get("spdx_id"),
        visibility=_to_visibility(bool(meta.get("private"))),
        default_branch=branch,
        homepage=meta.get("homepage"),
        has_pages=bool(meta.get("has_pages")),
        archived=bool(meta.get("archived")),
        created_at=meta.get("created_at"),
        pushed_at=meta.get("pushed_at"),
        updated_at=meta.get("updated_at"),
        stars=int(meta.get("stargazers_count") or 0),
        forks=int(meta.get("forks_count") or 0),
        open_issues=int(meta.get("open_issues_count") or 0),
        watchers=int(meta.get("subscribers_count") or 0),
        readme_text=readme_text,
        readme_source=readme_source,
        root_files=root_files,
        has_license_file=health["has_license_file"],
        has_ci=health["has_ci"],
        has_tests=health["has_tests"],
        has_gitignore=health["has_gitignore"],
        has_contributing=health["has_contributing"],
        has_code_of_conduct=health["has_code_of_conduct"],
        releases=releases,
        contributors=contributors,
        fetch_errors=errors,
    )

    # 5. 网页降级（仅当公开仓库且元数据关键字段缺失时补信息；
    #    私有仓库网页需登录，匿名抓取必然失败且浪费超时时间，直接跳过）
    if not snapshot.is_private and (not snapshot.description or not snapshot.topics):
        try:
            web = fetch_via_web(owner, repo)
            if web:
                if not snapshot.description and web.get("description"):
                    snapshot.description = web["description"]
                if not snapshot.topics and web.get("topics"):
                    snapshot.topics = web["topics"]
        except Exception as e:
            errors.append(f"web_fallback: {e}")

    return snapshot
