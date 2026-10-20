"""RepoRadar Web 前端后端（FastAPI）。

启动：uvicorn repo_seo.web.app:app --port 8000
访问：http://localhost:8000

复用 repo_seo 全部能力（抓取/评分/AI 建议/外部验证/趋势），
API Key / Token 一律从环境变量读取，不从前端传入。
"""

from __future__ import annotations

import dataclasses
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from ..advice import generate_advice
from ..advice.llm import DEFAULT_BASE_URL, DEFAULT_MODEL, LLMClient, LLMError
from ..advice.optimize import generate_optimize_plan, optimize_plan_to_dict
from ..fetcher import RateLimitError, RepoNotFoundError, fetch_snapshot, parse_github_url
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
