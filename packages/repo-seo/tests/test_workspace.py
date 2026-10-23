"""本地工作区 + 一键应用修改测试。"""

from __future__ import annotations

import io
import json
import tarfile
from pathlib import Path

import pytest

from repo_seo.advice.optimize import OptimizeAction, OptimizePlan
from repo_seo.advice.workspace import (
    ALLOWED_FILE_PATHS,
    _extract_tarball,
    apply_plan,
    check_write_access,
    ensure_repo_copy,
    normalize_file_target,
    repo_path,
)


class FakeAPI:
    def __init__(self, repo=None, user=None, archive: bytes = b"", fail_download=False):
        self.repo = repo
        self.user = user
        self.archive = archive
        self.fail_download = fail_download
        self.downloads: list[tuple[str, str | None]] = []

    def get_repo(self, full_name):
        return self.repo

    def get(self, path, params=None):
        assert path == "/user"
        return self.user

    def download_tarball(self, full_name, ref=None):
        if self.fail_download:
            raise AssertionError("不应触发下载")
        self.downloads.append((full_name, ref))
        return self.archive


def _make_action(type_: str, target: str, concrete: str = "content") -> OptimizeAction:
    return OptimizeAction(
        type=type_,
        target=target,
        what="做什么",
        why="为什么",
        concrete=concrete,
    )


def _make_plan(actions: list[OptimizeAction]) -> OptimizePlan:
    return OptimizePlan(summary="summary", actions=actions, estimated_gain=10)


def _tar_gz(entries: list[tuple[str, bytes]], extra: list[tarfile.TarInfo] | None = None) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for name, content in entries:
            info = tarfile.TarInfo(name)
            info.size = len(content)
            tar.addfile(info, io.BytesIO(content))
        for info in extra or []:
            tar.addfile(info)
    return buf.getvalue()


def test_normalize_file_target():
    assert normalize_file_target("新增 CONTRIBUTING.md 文件") == "CONTRIBUTING.md"
    assert normalize_file_target("`SECURITY.md`") == "SECURITY.md"
    assert normalize_file_target(".github/PULL_REQUEST_TEMPLATE.md") == (
        ".github/PULL_REQUEST_TEMPLATE.md"
    )
    assert normalize_file_target("LICENSE") is None
    assert normalize_file_target("../../evil.md") is None
    assert normalize_file_target("docs/CONTRIBUTING.md") == "CONTRIBUTING.md"
    assert all(p in ALLOWED_FILE_PATHS for p in ("CONTRIBUTING.md", "SECURITY.md"))


def test_apply_plan_readme_and_new_file(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "README.md").write_text("# Old\n", encoding="utf-8")
    (repo / "SECURITY.md").write_text("# Existing security\n", encoding="utf-8")

    plan = _make_plan(
        [
            _make_action("readme", "README.md", "不会使用这段"),
            _make_action("file", "新增 CONTRIBUTING.md", "```markdown\n# Contributing\n\nThanks!\n```"),
            _make_action("file", "SECURITY.md", "# New security"),
            _make_action("file", "LICENSE", "MIT License"),
            _make_action("file", "../../evil.md", "pwned"),
            _make_action("metadata", "仓库描述", "新的描述"),
        ]
    )
    outcome = apply_plan(repo, plan, readme_content="# New\n\nBetter README.\n")

    assert (repo / "README.md").read_text(encoding="utf-8") == "# New\n\nBetter README.\n"
    assert (repo / "CONTRIBUTING.md").read_text(encoding="utf-8") == "# Contributing\n\nThanks!\n"
    assert (repo / "SECURITY.md").read_text(encoding="utf-8") == "# Existing security\n"
    assert not (tmp_path / "evil.md").exists()

    applied = {item["path"]: item for item in outcome.applied}
    assert set(applied) == {"README.md", "CONTRIBUTING.md"}
    assert applied["README.md"]["action"] == "readme"
    assert applied["README.md"]["created"] is False
    assert applied["CONTRIBUTING.md"]["created"] is True

    skipped = {item["path"] for item in outcome.skipped}
    assert "SECURITY.md" in skipped
    manual_targets = {item["target"] for item in outcome.manual}
    assert {"LICENSE", "../../evil.md", "仓库描述"} <= manual_targets
    manual_by_target = {item["target"]: item for item in outcome.manual}
    assert manual_by_target["LICENSE"]["concrete"] == "MIT License"
    assert manual_by_target["仓库描述"]["concrete"] == "新的描述"
    assert manual_by_target["../../evil.md"]["concrete"] == "pwned"

    assert "--- a/README.md" in outcome.diff
    assert "+++ b/README.md" in outcome.diff
    assert "- # New" not in outcome.diff
    assert "+# New" in outcome.diff
    assert "--- /dev/null" in outcome.diff
    assert "+++ b/CONTRIBUTING.md" in outcome.diff
    assert "+# Contributing" in outcome.diff
    assert not outcome.diff_truncated


def test_apply_plan_skips_identical_readme(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "README.md").write_text("# Same\n", encoding="utf-8")

    outcome = apply_plan(repo, _make_plan([]), readme_content="# Same\n")

    assert outcome.applied == []
    assert outcome.diff == ""
    assert outcome.skipped == [
        {"path": "README.md", "reason": "生成的 README 与当前内容一致，无需修改"}
    ]


def test_apply_plan_readme_action_without_draft_is_manual(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()

    outcome = apply_plan(repo, _make_plan([_make_action("readme", "README.md")]))

    assert outcome.applied == []
    assert outcome.manual[0]["type"] == "readme"
    assert "README 自动生成失败" in outcome.manual[0]["reason"]


def test_check_write_access_push_permission():
    api = FakeAPI(repo={"permissions": {"push": True}, "default_branch": "dev", "owner": {"login": "alice"}})
    access = check_write_access(api, "alice/repo")
    assert access.can_write is True
    assert access.default_branch == "dev"


def test_check_write_access_owner_fallback():
    api = FakeAPI(
        repo={"permissions": {"push": False}, "default_branch": "main", "owner": {"login": "Alice"}},
        user={"login": "alice"},
    )
    access = check_write_access(api, "Alice/repo")
    assert access.can_write is True
    assert access.reason == "Token 所属用户是仓库所有者"


def test_check_write_access_denied():
    api = FakeAPI(
        repo={"permissions": {"push": False}, "default_branch": "main", "owner": {"login": "alice"}},
        user={"login": "bob"},
    )
    access = check_write_access(api, "alice/repo")
    assert access.can_write is False
    assert "没有 push 权限" in access.reason


def test_extract_tarball_skips_links_and_traversal(tmp_path):
    link = tarfile.TarInfo("owner-repo-abc/link")
    link.type = tarfile.SYMTYPE
    link.linkname = "../../etc/passwd"

    archive = _tar_gz(
        [
            ("owner-repo-abc/README.md", b"# Repo\n"),
            ("owner-repo-abc/src/main.py", b"print('hi')\n"),
            ("owner-repo-abc/../../evil.txt", b"pwned"),
        ],
        extra=[link],
    )
    dest = tmp_path / "out"
    dest.mkdir()
    _extract_tarball(archive, dest)

    assert (dest / "README.md").read_text(encoding="utf-8") == "# Repo\n"
    assert (dest / "src" / "main.py").is_file()
    assert not (dest / "link").exists()
    assert not (tmp_path / "evil.txt").exists()


def test_ensure_repo_copy_downloads_reuses_and_refreshes(tmp_path, monkeypatch):
    monkeypatch.setenv("REPO_SEO_WORKSPACE_DIR", str(tmp_path / "workspaces"))
    archive_v1 = _tar_gz([("owner-repo-abc/README.md", b"# v1\n")])
    archive_v2 = _tar_gz([("owner-repo-abc/README.md", b"# v2\n")])

    api = FakeAPI(archive=archive_v1)
    repo_dir, reused = ensure_repo_copy(api, "owner", "repo", "main")
    assert reused is False
    assert (repo_dir / "README.md").read_text(encoding="utf-8") == "# v1\n"
    assert api.downloads == [("owner/repo", "main")]

    # 已存在且分支一致：不再下载
    api_no_download = FakeAPI(fail_download=True)
    repo_dir2, reused2 = ensure_repo_copy(api_no_download, "owner", "repo", "main")
    assert repo_dir2 == repo_dir
    assert reused2 is True

    # refresh：重新下载并覆盖
    api_v2 = FakeAPI(archive=archive_v2)
    repo_dir3, reused3 = ensure_repo_copy(api_v2, "owner", "repo", "main", refresh=True)
    assert repo_dir3 == repo_dir
    assert reused3 is False
    assert (repo_dir / "README.md").read_text(encoding="utf-8") == "# v2\n"

    meta = json.loads((repo_path("owner", "repo").parent / "repo.meta.json").read_text("utf-8"))
    assert meta["branch"] == "main"
    assert meta["source"] == "tarball"


def test_repo_path_rejects_traversal(monkeypatch, tmp_path):
    monkeypatch.setenv("REPO_SEO_WORKSPACE_DIR", str(tmp_path))
    with pytest.raises(ValueError):
        repo_path("..", "repo")
    with pytest.raises(ValueError):
        repo_path("owner", "../../etc")
