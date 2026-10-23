"""本地工作区：把「一键优化」从建议升级为可审阅的文件修改。

流程：
1. 校验 GITHUB_TOKEN 对目标仓库是否有 push 权限（只允许操作自己的仓库）；
2. 通过 tarball 下载仓库快照（容器内无需安装 git），解压到本地工作区；
3. 应用 README 草稿 + 白名单内的安全文档文件（只新建、不覆盖已有文件）；
4. 生成 unified diff 供前端展示。

安全边界：
- 仓库名 / 文件名严格校验，拒绝路径穿越与绝对路径；
- 只写 README.md 与 ALLOWED_FILE_PATHS 内的文件，绝不执行仓库内容；
- 只修改本地副本，不 commit / 不 push（提交由用户自行完成）；
- 单仓库下载 200MB、解压 500MB、最多 20000 个文件。
"""

from __future__ import annotations

import difflib
import io
import json
import os
import re
import shutil
import tarfile
import tempfile
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

from ..fetcher.github_api import FetchError, GitHubAPI
from .optimize import OptimizePlan
from .readme_gen import strip_code_fence

DEFAULT_WORKSPACE_DIRNAME = ".repo-seo-workspaces"
README_NAME = "README.md"

# 仅允许自动新建这些文件；已存在的文件一律跳过，避免覆盖用户内容。
ALLOWED_FILE_PATHS: tuple[str, ...] = (
    "CONTRIBUTING.md",
    "SECURITY.md",
    "CODE_OF_CONDUCT.md",
    "SUPPORT.md",
    "CHANGELOG.md",
    ".gitignore",
    ".github/PULL_REQUEST_TEMPLATE.md",
    ".github/ISSUE_TEMPLATE.md",
)

MAX_EXTRACTED_BYTES = 500 * 1024 * 1024
MAX_EXTRACTED_FILES = 20_000
MAX_SINGLE_FILE_BYTES = 20 * 1024 * 1024
MAX_DIFF_CHARS = 200_000

_COMPONENT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")

_LOCKS: dict[str, threading.Lock] = {}
_LOCKS_GUARD = threading.Lock()


@dataclass
class RepoAccess:
    """Token 对目标仓库的写权限判定结果。"""

    full_name: str
    can_write: bool
    reason: str
    default_branch: str = "main"
    private: bool = False
    login: str | None = None


@dataclass
class ApplyOutcome:
    """一次本地应用的结果（供 API / 前端展示）。"""

    applied: list[dict] = field(default_factory=list)
    skipped: list[dict] = field(default_factory=list)
    manual: list[dict] = field(default_factory=list)
    diff: str = ""
    diff_truncated: bool = False


def _validate_component(value: str, label: str) -> str:
    if not value or not _COMPONENT_RE.match(value) or value in (".", ".."):
        raise ValueError(f"非法{label}：{value!r}")
    return value


def workspace_root() -> Path:
    """工作区根目录；容器内由 REPO_SEO_WORKSPACE_DIR 指向命名卷。"""
    raw = os.environ.get("REPO_SEO_WORKSPACE_DIR", "").strip()
    return Path(raw) if raw else Path.cwd() / DEFAULT_WORKSPACE_DIRNAME


def repo_path(owner: str, repo: str) -> Path:
    return workspace_root() / _validate_component(owner, "owner").lower() / _validate_component(
        repo, "repo"
    ).lower()


def _meta_path(owner: str, repo: str) -> Path:
    dest = repo_path(owner, repo)
    return dest.parent / f"{dest.name}.meta.json"


def repo_lock(owner: str, repo: str) -> threading.Lock:
    """同一仓库的下载 / 应用串行化，避免并发请求互相覆盖。"""
    key = f"{owner}/{repo}".lower()
    with _LOCKS_GUARD:
        lock = _LOCKS.get(key)
        if lock is None:
            lock = threading.Lock()
            _LOCKS[key] = lock
        return lock


def check_write_access(api: GitHubAPI, full_name: str) -> RepoAccess:
    """判断 Token 是否可写目标仓库。

    优先使用 GitHub 返回的 permissions.push；若字段缺失，则退化为
    「Token 所属用户 == 仓库 owner」判定（仓库所有者一定可写）。
    """
    data = api.get_repo(full_name)
    if not isinstance(data, dict):
        raise FetchError(f"仓库元数据格式异常：{full_name}")

    owner = ""
    owner_info = data.get("owner")
    if isinstance(owner_info, dict):
        owner = str(owner_info.get("login") or "")

    perms = data.get("permissions") if isinstance(data.get("permissions"), dict) else {}
    default_branch = str(data.get("default_branch") or "main")
    private = bool(data.get("private"))

    login: str | None = None
    try:
        me = api.get("/user")
        if isinstance(me, dict):
            login = str(me.get("login") or "") or None
    except FetchError:
        # 只读 Token 或网络异常时仍可用 permissions.push 判定
        login = None

    if perms.get("push"):
        return RepoAccess(
            full_name=full_name,
            can_write=True,
            reason="Token 对仓库有 push 权限",
            default_branch=default_branch,
            private=private,
            login=login,
        )

    if login and owner and login.lower() == owner.lower():
        return RepoAccess(
            full_name=full_name,
            can_write=True,
            reason="Token 所属用户是仓库所有者",
            default_branch=default_branch,
            private=private,
            login=login,
        )

    return RepoAccess(
        full_name=full_name,
        can_write=False,
        reason=(
            f"当前 GITHUB_TOKEN 对 {full_name} 没有 push 权限。"
            "一键应用只允许修改自己的仓库（仓库所有者或协作者）；"
            "公开仓库仍可使用「生成修改清单」查看只读建议。"
        ),
        default_branch=default_branch,
        private=private,
        login=login,
    )


def ensure_repo_copy(
    api: GitHubAPI,
    owner: str,
    repo: str,
    branch: str,
    refresh: bool = False,
) -> tuple[Path, bool]:
    """确保本地有仓库副本；返回 (目录, 是否复用已有副本)。

    下载失败时保留旧副本（先下载、后替换），避免把工作区清空。
    """
    dest = repo_path(owner, repo)
    meta_path = _meta_path(owner, repo)
    meta: dict = {}
    if meta_path.is_file():
        try:
            loaded = json.loads(meta_path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                meta = loaded
        except (OSError, ValueError):
            meta = {}

    if not refresh and dest.is_dir() and meta.get("branch") == branch:
        if any(dest.iterdir()):
            return dest, True

    data = api.download_tarball(f"{owner}/{repo}", branch or "HEAD")
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(dir=str(dest.parent), prefix=f".{dest.name}-"))

    try:
        _extract_tarball(data, tmp)
        entries = list(tmp.iterdir())
        src = entries[0] if len(entries) == 1 and entries[0].is_dir() else tmp

        if dest.exists():
            shutil.rmtree(dest)

        if src == tmp:
            shutil.move(str(tmp), str(dest))
        else:
            shutil.move(str(src), str(dest))
            shutil.rmtree(tmp, ignore_errors=True)
    except Exception:
        shutil.rmtree(tmp, ignore_errors=True)
        raise

    meta_path.write_text(
        json.dumps(
            {
                "full_name": f"{owner}/{repo}",
                "branch": branch,
                "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "source": "tarball",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return dest, False


def _extract_tarball(data: bytes, dest: Path) -> None:
    """安全解压：跳过链接/设备文件，拒绝穿越，限制总体积与文件数。"""
    dest_resolved = dest.resolve()
    total = 0
    count = 0

    try:
        tar = tarfile.open(fileobj=io.BytesIO(data), mode="r:gz")
    except tarfile.TarError as e:
        raise FetchError(f"仓库快照解压失败：{e}") from e

    with tar:
        for member in tar:
            if not member.isfile():
                continue

            count += 1
            if count > MAX_EXTRACTED_FILES:
                raise FetchError(f"仓库快照文件数超过 {MAX_EXTRACTED_FILES} 上限。")

            parts = PurePosixPath(member.name).parts
            # tarball 顶层目录为 owner-repo-sha，剥掉它
            if len(parts) < 2 or ".." in parts:
                continue
            rel = PurePosixPath(*parts[1:])
            if rel.is_absolute() or not rel.parts:
                continue

            out = (dest / Path(*rel.parts)).resolve()
            if dest_resolved not in out.parents:
                continue

            total += member.size
            if total > MAX_EXTRACTED_BYTES:
                raise FetchError("仓库快照解压后超过 500MB 上限。")
            if member.size > MAX_SINGLE_FILE_BYTES:
                continue

            source = tar.extractfile(member)
            if source is None:
                continue

            out.parent.mkdir(parents=True, exist_ok=True)
            with source, open(out, "wb") as target:
                shutil.copyfileobj(source, target)


def normalize_file_target(target: str) -> str | None:
    """把 LLM 的自由文本 target 归一化为白名单路径。

    LLM 常见写法：「新增 CONTRIBUTING.md」「CONTRIBUTING.md（贡献指南）」
    「.github/PULL_REQUEST_TEMPLATE.md」。只接受白名单内的文件。
    """
    text = target.strip().strip("`").replace("\\", "/")
    if not text:
        return None

    lowered = text.lower()
    for allowed in ALLOWED_FILE_PATHS:
        if allowed.lower() in lowered:
            return allowed

    cleaned = text.strip(" ./")
    return cleaned if cleaned in ALLOWED_FILE_PATHS else None


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _normalize_text(text: str) -> str:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").strip("\n")
    return f"{normalized}\n" if normalized else ""


def _unified_diff(path: str, old: str | None, new: str, created: bool) -> str:
    fromfile = "/dev/null" if created else f"a/{path}"
    old_lines = [] if old is None else old.splitlines(keepends=True)
    new_lines = new.splitlines(keepends=True)
    return "".join(
        difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile=fromfile,
            tofile=f"b/{path}",
            n=3,
        )
    )


def apply_plan(
    repo_dir: Path,
    plan: OptimizePlan,
    readme_content: str | None = None,
) -> ApplyOutcome:
    """把优化清单应用到本地副本，返回应用结果与 unified diff。

    只写 README.md 与 ALLOWED_FILE_PATHS；已存在文件跳过；不 commit / push。
    """
    if not repo_dir.is_dir():
        raise FetchError(f"工作区仓库目录不存在：{repo_dir}")

    outcome = ApplyOutcome()
    changes: list[tuple[str, str | None, str, str]] = []
    seen: set[str] = set()

    readme_path = repo_dir / README_NAME
    readme_old = _read_text(readme_path) if readme_path.is_file() else None

    if readme_content is not None:
        new_readme = _normalize_text(readme_content)
        if not new_readme:
            outcome.skipped.append({"path": README_NAME, "reason": "README 草稿为空，已跳过"})
        elif readme_old == new_readme:
            outcome.skipped.append(
                {"path": README_NAME, "reason": "生成的 README 与当前内容一致，无需修改"}
            )
        else:
            created = readme_old is None
            changes.append((README_NAME, readme_old, new_readme, "readme"))
            outcome.applied.append(
                {
                    "path": README_NAME,
                    "action": "readme",
                    "created": created,
                    "bytes": len(new_readme.encode("utf-8")),
                }
            )
            seen.add(README_NAME)

    for action in plan.actions:
        if action.type == "readme":
            if readme_content is None:
                outcome.manual.append(
                    {
                        "type": action.type,
                        "target": action.target,
                        "what": action.what,
                        "concrete": action.concrete,
                        "reason": "README 自动生成失败，请手动应用该修改",
                    }
                )
            continue

        if action.type != "file":
            outcome.manual.append(
                {
                    "type": action.type,
                    "target": action.target,
                    "what": action.what,
                    "concrete": action.concrete,
                    "reason": "该类型（元数据 / 仓库设置）需在 GitHub 后台手动修改",
                }
            )
            continue

        target = normalize_file_target(action.target)
        if target is None:
            outcome.manual.append(
                {
                    "type": action.type,
                    "target": action.target,
                    "what": action.what,
                    "concrete": action.concrete,
                    "reason": "目标文件不在自动修改白名单内，请手动创建",
                }
            )
            continue

        if target in seen:
            outcome.skipped.append({"path": target, "reason": "清单中存在重复目标，已跳过"})
            continue

        path = repo_dir / target
        if path.exists():
            outcome.skipped.append(
                {"path": target, "reason": "文件已存在，为避免覆盖用户内容已跳过"}
            )
            seen.add(target)
            continue

        content = _normalize_text(strip_code_fence(action.concrete))
        if not content:
            outcome.skipped.append({"path": target, "reason": "生成内容为空，已跳过"})
            seen.add(target)
            continue

        changes.append((target, None, content, "file"))
        outcome.applied.append(
            {
                "path": target,
                "action": "file",
                "created": True,
                "bytes": len(content.encode("utf-8")),
            }
        )
        seen.add(target)

    diffs: list[str] = []
    for rel_path, old, new, _action in changes:
        diffs.append(_unified_diff(rel_path, old, new, created=old is None))

    diff_text = "".join(diffs)
    if len(diff_text) > MAX_DIFF_CHARS:
        outcome.diff = (
            diff_text[:MAX_DIFF_CHARS]
            + f"\n…（diff 已截断，共 {len(diff_text)} 字符）\n"
        )
        outcome.diff_truncated = True
    else:
        outcome.diff = diff_text

    # 先计算 diff 再落盘，保证返回内容与写入内容严格一致
    for rel_path, _old, new, _action in changes:
        path = repo_dir / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(new, encoding="utf-8")

    return outcome
