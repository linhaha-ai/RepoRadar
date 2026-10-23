"""RepoRadar Web 前端后端（FastAPI）。

启动：uvicorn repo_seo.web.app:app --port 8000
访问：http://localhost:8000

复用 repo_seo 全部能力（抓取/评分/AI 建议/外部验证/趋势），
API Key / Token 一律从环境变量读取，不从前端传入。
"""

from __future__ import annotations

import dataclasses
import os
import re
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from ..advice import generate_advice
from ..advice.llm import DEFAULT_BASE_URL, DEFAULT_MODEL, LLMClient, LLMError
from ..advice.optimize import generate_optimize_plan, optimize_plan_to_dict
from ..advice.readme_gen import generate_readme_draft
from ..advice.workspace import apply_plan, check_write_access, ensure_repo_copy, repo_lock
from ..fetcher import (
    FetchError,
    GitHubAPI,
    RateLimitError,
    RepoNotFoundError,
    fetch_snapshot,
    parse_github_url,
)
from ..model import EvidenceStatus
from ..scoring import score_snapshot
from ..trend import DimensionSnapshot, HistoryStore, SnapshotRecord, analyze_trend
from ..verify import run_external_verification

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(
    title="RepoRadar",
    description="GitHub 仓库可发现性体检：原生搜索优化 + AI 检索曝光（AEO）",
    version="2.2",
)


class ScanRequest(BaseModel):
    url: str
    ai: bool = True
    verify: bool = False


class OptimizeRequest(BaseModel):
    url: str


class ApplyRequest(BaseModel):
    url: str
    refresh: bool = False


def _make_llm() -> LLMClient | None:
    key = os.environ.get("REPO_SEO_API_KEY")
    if not key:
        return None
    return LLMClient(
        api_key=key,
        base_url=os.environ.get("REPO_SEO_BASE_URL") or DEFAULT_BASE_URL,
        model=os.environ.get("REPO_SEO_MODEL") or DEFAULT_MODEL,
    )


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.post("/api/scan")
def api_scan(req: ScanRequest) -> JSONResponse:
    try:
        owner, repo = parse_github_url(req.url)
    except ValueError as e:
        return JSONResponse({"error": f"URL 解析失败：{e}"}, status_code=400)

    try:
        snap = fetch_snapshot(owner, repo, token=os.environ.get("GITHUB_TOKEN"))
    except RepoNotFoundError as e:
        return JSONResponse({"error": str(e)}, status_code=404)
    except RateLimitError as e:
        return JSONResponse({"error": str(e)}, status_code=429)
    except Exception as e:
        return JSONResponse({"error": f"{type(e).__name__}: {e}"}, status_code=500)

    report = score_snapshot(snap)

    llm = _make_llm() if req.ai else None
    adv = generate_advice(snap, report.results, llm)

    verification = None
    if req.verify:
        probes = os.environ.get("REPO_SEO_PROBE_MODELS")
        probe_models_list = (
            [m.strip() for m in probes.split(",") if m.strip()] if probes else None
        )
        verification = run_external_verification(
            snap,
            llm=llm,
            google_key=os.environ.get("GOOGLE_CSE_API_KEY"),
            google_cse=os.environ.get("GOOGLE_CSE_ID"),
            probe_models_list=probe_models_list,
        )

    store = HistoryStore()
    diff = analyze_trend(store.load(owner, repo))

    payload = {
        "snapshot": dataclasses.asdict(snap),
        "llm_configured": _make_llm() is not None,
        "score": {
            "total": report.total,
            "dimensions": {
                dim: {
                    "label": d.label,
                    "earned": d.earned,
                    "eligible": d.eligible,
                    "total": d.total,
                }
                for dim, d in report.dimensions.items()
            },
            "results": [r.to_dict() for r in report.results],
            "top_issues": [r.to_dict() for r in report.top_issues],
            "n_na_unknown": report.n_na_unknown,
            "warnings": report.warnings,
        },
        "advice": {
            "source": adv.source.value,
            "note": adv.note,
            "items": [dataclasses.asdict(a) for a in adv.advices],
        },
        "verification": verification.to_dict() if verification else None,
        "trend": {
            "records": [{"at": r.at, "total": r.total} for r in diff.records],
            "n_records": diff.n_records,
            "span_days": diff.span_days,
        },
    }

    # 保存完整评分报告为历史版本（可追溯回看）
    store.append(
        SnapshotRecord(
            at=snap.fetched_at,
            total=report.total,
            dimensions={
                dim: DimensionSnapshot(d.earned, d.eligible, d.total)
                for dim, d in report.dimensions.items()
            },
            url=req.url,
            source="scan",
            report=payload,
        ),
        owner,
        repo,
    )

    return JSONResponse(payload)


def _scan_for(url: str) -> tuple:
    """抓取 + 评分（供 /api/scan 与 /api/optimize 复用）。"""
    owner, repo = parse_github_url(url)
    snap = fetch_snapshot(owner, repo, token=os.environ.get("GITHUB_TOKEN"))
    report = score_snapshot(snap)
    return snap, report


@app.get("/api/history/{owner}/{repo}")
def api_history(owner: str, repo: str) -> JSONResponse:
    """历史版本列表：每次体检一条记录（含是否保存了完整报告）。"""
    store = HistoryStore()
    records = store.load(owner, repo)
    return JSONResponse(
        {
            "owner": owner,
            "repo": repo,
            "records": [
                {
                    "index": i,
                    "at": r.at,
                    "total": r.total,
                    "source": r.source,
                    "has_report": r.report is not None,
                    "url": r.url,
                    "dimensions": {
                        k: {
                            "earned": v.earned,
                            "eligible": v.eligible,
                            "total": v.total,
                        }
                        for k, v in r.dimensions.items()
                    },
                }
                for i, r in enumerate(records)
            ],
        }
    )


@app.get("/api/history/{owner}/{repo}/{index}")
def api_history_detail(owner: str, repo: str, index: int) -> JSONResponse:
    """单个历史版本详情：返回该次体检的完整评分报告。"""
    store = HistoryStore()
    records = store.load(owner, repo)
    if index < 0 or index >= len(records):
        return JSONResponse(
            {"error": f"历史版本不存在（共 {len(records)} 条）"}, status_code=404
        )
    rec = records[index]
    if not rec.report:
        return JSONResponse(
            {"error": "该历史版本未保存完整报告（旧版本数据）"}, status_code=404
        )
    return JSONResponse(rec.report)


@app.post("/api/optimize")
def api_optimize(req: OptimizeRequest) -> JSONResponse:
    """一键优化：把报告 + 提示词交给 LLM，产出可落地的具体修改清单。"""
    try:
        snap, report = _scan_for(req.url)
    except ValueError as e:
        return JSONResponse({"error": f"URL 解析失败：{e}"}, status_code=400)
    except RepoNotFoundError as e:
        return JSONResponse({"error": str(e)}, status_code=404)
    except RateLimitError as e:
        return JSONResponse({"error": str(e)}, status_code=429)
    except Exception as e:
        return JSONResponse({"error": f"{type(e).__name__}: {e}"}, status_code=500)

    llm = _make_llm()
    if llm is None:
        return JSONResponse(
            {
                "error": (
                    "未配置 REPO_SEO_API_KEY。一键优化需要调用 LLM，"
                    "请先在 .env / 环境变量中配置 REPO_SEO_API_KEY（可配合 REPO_SEO_BASE_URL、REPO_SEO_MODEL）。"
                )
            },
            status_code=400,
        )

    try:
        plan = generate_optimize_plan(snap, report, llm)
    except LLMError as e:
        return JSONResponse({"error": str(e)}, status_code=502)

    return JSONResponse(optimize_plan_to_dict(plan))


@app.post("/api/optimize/apply")
def api_optimize_apply(req: ApplyRequest) -> JSONResponse:
    """一键优化并应用：只改本地工作区副本，不 commit / 不 push。

    仅允许 Token 有 push 权限的仓库（自己的仓库）；其他仓库返回 403，
    前端回退到只读「生成修改清单」。
    """
    try:
        owner, repo = parse_github_url(req.url)
    except ValueError as e:
        return JSONResponse({"error": f"URL 解析失败：{e}"}, status_code=400)

    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        return JSONResponse(
            {
                "error": (
                    "未配置 GITHUB_TOKEN，无法验证仓库写权限。"
                    "请配置一个对目标仓库有 push 权限的 Token 后重试；"
                    "或使用「生成修改清单」查看只读建议。"
                ),
                "read_only": True,
            },
            status_code=403,
        )

    api = GitHubAPI(token=token)
    try:
        access = check_write_access(api, f"{owner}/{repo}")
    except RepoNotFoundError as e:
        return JSONResponse({"error": str(e)}, status_code=404)
    except RateLimitError as e:
        return JSONResponse({"error": str(e)}, status_code=429)
    except FetchError as e:
        return JSONResponse({"error": str(e)}, status_code=502)

    if not access.can_write:
        return JSONResponse(
            {
                "error": access.reason,
                "read_only": True,
                "repository": {
                    "owner": owner,
                    "repo": repo,
                    "full_name": f"{owner}/{repo}",
                    "branch": access.default_branch,
                },
            },
            status_code=403,
        )

    llm = _make_llm()
    if llm is None:
        return JSONResponse(
            {
                "error": (
                    "未配置 REPO_SEO_API_KEY。一键应用需要调用 LLM 生成修改内容，"
                    "请先在 .env / 环境变量中配置 REPO_SEO_API_KEY（可配合 REPO_SEO_BASE_URL、REPO_SEO_MODEL）。"
                )
            },
            status_code=400,
        )

    try:
        snap, report = _scan_for(req.url)
        plan = generate_optimize_plan(snap, report, llm)
        adv = generate_advice(snap, report.results, llm)

        # README 影响 readme 与 aeo 两个维度；只要相关规则有失分或清单要求改 README，
        # 就重新生成一份（事实来自快照，禁止编造）。
        needs_readme = any(a.type == "readme" for a in plan.actions) or any(
            r.status == EvidenceStatus.FAIL and r.dimension in ("readme", "aeo")
            for r in report.results
        )
        readme_content: str | None = None
        readme_error: str | None = None
        if needs_readme:
            try:
                readme_content = generate_readme_draft(
                    snap, report.results, adv.advices, llm
                ).content
            except LLMError as e:
                readme_error = str(e)

        with repo_lock(owner, repo):
            repo_dir, reused = ensure_repo_copy(
                api,
                owner,
                repo,
                access.default_branch,
                refresh=req.refresh,
            )
            outcome = apply_plan(repo_dir, plan, readme_content=readme_content)
    except RepoNotFoundError as e:
        return JSONResponse({"error": str(e)}, status_code=404)
    except RateLimitError as e:
        return JSONResponse({"error": str(e)}, status_code=429)
    except LLMError as e:
        return JSONResponse({"error": str(e)}, status_code=502)
    except FetchError as e:
        return JSONResponse({"error": str(e)}, status_code=502)
    except Exception as e:
        return JSONResponse({"error": f"{type(e).__name__}: {e}"}, status_code=500)

    return JSONResponse(
        {
            "repository": {
                "owner": owner,
                "repo": repo,
                "full_name": snap.full_name,
                "branch": access.default_branch,
                "workspace": str(repo_dir),
                "reused": reused,
            },
            "read_only": False,
            "readme_generated": readme_content is not None,
            "readme_error": readme_error,
            "plan": optimize_plan_to_dict(plan),
            "applied": outcome.applied,
            "skipped": outcome.skipped,
            "manual": outcome.manual,
            "diff": outcome.diff,
            "diff_truncated": outcome.diff_truncated,
        }
    )


# ---- 深链 SPA 路由（必须放在所有具体路由之后） ----
# 访问 /{owner}/{repo} 返回单页应用，前端据此直接浏览该仓库最近一次体检报告。
_SPA_SEGMENT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_SPA_RESERVED_OWNERS = frozenset({"api", "static", "docs", "redoc", "openapi.json"})


@app.get("/{owner}/{repo}", response_model=None)
def spa_repo(owner: str, repo: str) -> FileResponse | JSONResponse:
    """深链入口：/owner/repo 返回单页应用（不匹配的保留前缀 / 非法字符给 404 JSON）。"""
    if (
        owner.lower() in _SPA_RESERVED_OWNERS
        or not _SPA_SEGMENT_RE.match(owner)
        or not _SPA_SEGMENT_RE.match(repo)
    ):
        return JSONResponse({"error": "Not Found"}, status_code=404)
    return FileResponse(STATIC_DIR / "index.html")
