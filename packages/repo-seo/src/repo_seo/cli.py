"""RepoSEO CLI 入口。

用法：
  repo-seo https://github.com/owner/repo
  repo-seo owner/repo --token ghp_xxx
  repo-seo https://github.com/owner/repo --json out.json
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

import typer

from .advice import generate_advice
from .advice.llm import DEFAULT_BASE_URL, DEFAULT_MODEL, LLMClient, LLMError
from .advice.readme_gen import generate_readme_draft
from .fetcher import RepoNotFoundError, RateLimitError, fetch_snapshot, parse_github_url
from .report import render_html, render_markdown, render_terminal
from .rules.config import ConfigError, default_config_toml, load_config
from .rules.engine import ALL_RULES
from .scoring import score_snapshot
from .trend import (
    HistoryStore,
    SnapshotRecord,
    analyze_trend,
    render_trend_html,
    render_trend_markdown,
    render_trend_terminal,
)
from .trend.history import DimensionSnapshot
from .verify import run_external_verification

app = typer.Typer(
    name="repo-seo",
    help="GitHub 仓库可发现性体检：输入仓库 URL，抓取并输出优化报告。",
    add_completion=False,
)


@app.command("scan")
def scan(
    url: str = typer.Argument(..., help="GitHub 仓库 URL / owner/repo"),
    token: str | None = typer.Option(
        None, "--token", "-t", envvar="GITHUB_TOKEN", help="GitHub Token（私有仓库或更高限流）"
    ),
    json_out: Path | None = typer.Option(
        None, "--json", help="将抓取结果导出为 JSON 文件（M1 阶段便于检查数据）"
    ),
    use_ai: bool = typer.Option(
        None, "--ai", help="强制启用 AI 优化建议（默认：检测到 REPO_SEO_API_KEY 时启用）"
    ),
    no_ai: bool = typer.Option(
        None, "--no-ai", help="强制关闭 AI 优化建议，仅用规则模板"
    ),
    model: str | None = typer.Option(None, "--model", help="LLM 模型名"),
    base_url: str | None = typer.Option(None, "--base-url", help="OpenAI 兼容 base_url"),
    readme_draft: bool = typer.Option(
        False, "--readme-draft", help="用 AI 建议生成英文 README 草稿（需配置 LLM API Key）"
    ),
    readme_out: Path | None = typer.Option(
        None, "--readme-out", help="README 草稿输出路径（默认 ./README.draft.md）"
    ),
    report_md: Path | None = typer.Option(
        None, "--report-md", help="导出 Markdown 报告到该路径"
    ),
    report_html: Path | None = typer.Option(
        None, "--report-html", help="导出 HTML 报告到该路径"
    ),
    config_path: Path | None = typer.Option(
        None, "--config", help="规则配置 TOML（启用/分值/优先级/阈值参数）"
    ),
    verify: bool = typer.Option(
        False, "--verify", help="运行外部验证层（Google 收录 + 多模型 AEO 实测）"
    ),
) -> None:
    try:
        owner, repo = parse_github_url(url)
    except ValueError as e:
        typer.echo(f"[错误] {e}", err=True)
        raise typer.Exit(code=1)

    typer.echo(f"正在抓取 {owner}/{repo} ...")

    try:
        snap = fetch_snapshot(owner, repo, token=token)
    except RateLimitError as e:
        typer.echo(f"[限流] {e}", err=True)
        raise typer.Exit(code=1)
    except RepoNotFoundError as e:
        typer.echo(f"[未找到] {e}", err=True)
        raise typer.Exit(code=1)
    except Exception as e:
        typer.echo(f"[抓取失败] {type(e).__name__}: {e}", err=True)
        raise typer.Exit(code=1)

    # ---- 摘要输出（M1：抓取验证；评分在 M3 接入） ----
    vis = "私有" if snap.is_private else "公开"
    typer.echo("")
    typer.echo(f"仓库：{snap.full_name}  [{vis}]  默认分支：{snap.default_branch}")
    typer.echo(f"描述：{snap.description or '（空）'}")
    typer.echo(
        f"Topics：{', '.join(snap.topics) if snap.topics else '（空）'}  "
        f"语言：{snap.language or '（未识别）'}  许可：{snap.license_spdx or '（无）'}"
    )
    typer.echo(f"Stars：{snap.stars}  Forks：{snap.forks}  OpenIssues：{snap.open_issues}")
    typer.echo(
        f"README：{'存在（' + snap.readme_source + '）' if snap.has_readme else '缺失'}"
        f"（{len(snap.readme_text or '')} 字符）"
    )
    typer.echo(f"根文件：{', '.join(snap.root_files) if snap.root_files else '（空）'}")
    typer.echo(
        "工程信号："
        + " ".join(
            f"{k}={v}"
            for k, v in {
                "LICENSE": snap.has_license_file,
                "CI": snap.has_ci,
                "tests": snap.has_tests,
                ".gitignore": snap.has_gitignore,
                "CONTRIBUTING": snap.has_contributing,
                "CoC": snap.has_code_of_conduct,
            }.items()
        )
    )
    typer.echo(f"Releases：{len(snap.releases)}  贡献者：{len(snap.contributors)}")
    if snap.fetch_errors:
        typer.echo("")
        typer.echo("[抓取告警]")
        for err in snap.fetch_errors:
            typer.echo(f"  - {err}")

    # ---- 规则配置（--config） ----
    config = None
    if config_path:
        try:
            config = load_config(config_path, {r.id for r in ALL_RULES})
            typer.echo(f"已加载规则配置：{config_path}（{len(config)} 条规则被自定义）")
        except ConfigError as e:
            typer.echo(f"[配置错误] {e}", err=True)
            raise typer.Exit(code=2)

    # ---- 评分 + 报告（M3） ----
    report = score_snapshot(snap, config)

    # ---- AI 优化建议（M3.5） ----
    api_key = os.environ.get("REPO_SEO_API_KEY")
    llm: LLMClient | None = None
    if no_ai:
        llm = None
    elif use_ai and not api_key:
        typer.echo("[提示] --ai 已指定但未配置 REPO_SEO_API_KEY，本次使用规则模板建议", err=True)
    elif api_key:
        llm = LLMClient(
            api_key=api_key,
            base_url=base_url or os.environ.get("REPO_SEO_BASE_URL") or DEFAULT_BASE_URL,
            model=model or os.environ.get("REPO_SEO_MODEL") or DEFAULT_MODEL,
        )
    adv_result = generate_advice(snap, report.results, llm)

    # ---- 外部验证层（V2：--verify） ----
    verification = None
    if verify:
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

    typer.echo(
        render_terminal(report, snap, adv_result.advices, adv_result.source, verification)
    )

    # ---- README 草稿生成（M5 扩展：--readme-draft） ----
    if readme_draft:
        if llm is None:
            typer.echo(
                "[错误] --readme-draft 需要 LLM API Key：请设置 REPO_SEO_API_KEY"
                "（或用 --ai 确认已配置）",
                err=True,
            )
            raise typer.Exit(2)
        try:
            draft = generate_readme_draft(
                snap, report.results, adv_result.advices, llm
            )
        except LLMError as e:
            typer.echo(f"[错误] README 草稿生成失败：{e}", err=True)
            raise typer.Exit(1)
        out = readme_out or Path("README.draft.md")
        out.write_text(draft.content.rstrip() + "\n", encoding="utf-8")
        typer.echo(f"\nREADME 草稿已生成：{out}（落实 {len(draft.rule_ids_used)} 条建议）")

    # ---- 报告导出（M5） ----
    if report_md:
        md = render_markdown(report, snap, adv_result.advices, adv_result.source, verification)
        report_md.write_text(md, encoding="utf-8")
        typer.echo(f"Markdown 报告已导出：{report_md}")
    if report_html:
        html = render_html(report, snap, adv_result.advices, adv_result.source, verification)
        report_html.write_text(html, encoding="utf-8")
        typer.echo(f"HTML 报告已导出：{report_html}")

    if json_out:
        import dataclasses

        data = {
            "snapshot": dataclasses.asdict(snap),
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
                "source": adv_result.source.value,
                "note": adv_result.note,
                "items": [dataclasses.asdict(a) for a in adv_result.advices],
            },
            "verification": verification.to_dict() if verification else None,
        }
        json_out.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        typer.echo(f"\nJSON 已导出：{json_out}")


@app.command("parse")
def parse(url: str = typer.Argument(..., help="GitHub 仓库 URL / owner/repo")) -> None:
    """调试用：仅解析 URL，输出 owner/repo。"""
    try:
        owner, repo = parse_github_url(url)
        typer.echo(f"{owner}/{repo}")
    except ValueError as e:
        typer.echo(f"[错误] {e}", err=True)
        raise typer.Exit(code=1)


@app.command("rules")
def rules_cmd(
    export_config: Path | None = typer.Option(
        None, "--export-config", help="导出默认规则配置模板（TOML）到该路径"
    ),
) -> None:
    """列出 29 条规则与可配参数；或导出配置模板。"""
    if export_config:
        toml = default_config_toml([r.id for r in ALL_RULES], ALL_RULES)
        export_config.write_text(toml, encoding="utf-8")
        typer.echo(f"配置模板已导出：{export_config}（编辑后通过 --config 使用）")
        return

    from .rules.config import DEFAULT_PARAMS

    header = f"{'规则':<6}{'维度':<15}{'检查项':<22}{'分值':<7}{'优先级':<5}{'类型':<9}可配参数"
    typer.echo(header)
    typer.echo("-" * len(header))
    for r in ALL_RULES:
        params = DEFAULT_PARAMS.get(r.id)
        pdesc = ", ".join(params.keys()) if params else "—"
        typer.echo(
            f"{r.id:<6}{r.dimension:<15}{r.name:<22}{r.score:<7.1f}{r.priority:<5}"
            f"{r.check_type.value:<9}{pdesc}"
        )
    typer.echo("")
    typer.echo("维度权重：README 25 / 元数据 20 / AEO 20 / 可发现性 15 / 工程健康 10 / 活跃度 10")
    typer.echo("自定义配置下维度满分按启用规则分值动态计算；可用 repo-seo rules --export-config 生成模板")


@app.command("monitor")
def monitor(
    url: str = typer.Argument(..., help="GitHub 仓库 URL / owner/repo"),
    token: str | None = typer.Option(
        None, "--token", "-t", envvar="GITHUB_TOKEN", help="GitHub Token（私有仓库或更高限流）"
    ),
    config_path: Path | None = typer.Option(None, "--config", help="规则配置 TOML"),
    history_dir: Path | None = typer.Option(
        None, "--history-dir", help="历史记录目录（默认 ./.repo-seo-history）"
    ),
    md: Path | None = typer.Option(None, "--md", help="导出趋势 Markdown 报告"),
    html: Path | None = typer.Option(None, "--html", help="导出趋势 HTML 报告（含 SVG 曲线）"),
) -> None:
    """定时体检：扫描 → 评分 → 追加历史 → 输出趋势（可被 cron/CI 定时调用）。"""
    try:
        owner, repo = parse_github_url(url)
    except ValueError as e:
        typer.echo(f"[错误] {e}", err=True)
        raise typer.Exit(code=1)

    config = None
    if config_path:
        try:
            config = load_config(config_path, {r.id for r in ALL_RULES})
        except ConfigError as e:
            typer.echo(f"[配置错误] {e}", err=True)
            raise typer.Exit(code=2)

    try:
        snap = fetch_snapshot(owner, repo, token=token)
    except (RateLimitError, RepoNotFoundError) as e:
        typer.echo(f"[失败] {e}", err=True)
        raise typer.Exit(code=1)
    except Exception as e:
        typer.echo(f"[抓取失败] {type(e).__name__}: {e}", err=True)
        raise typer.Exit(code=1)

    report = score_snapshot(snap, config)
    store = HistoryStore(history_dir)
    record = SnapshotRecord(
        at=datetime.now().isoformat(timespec="seconds"),
        total=report.total,
        dimensions={
            dim: DimensionSnapshot(earned=d.earned, eligible=d.eligible, total=d.total)
            for dim, d in report.dimensions.items()
        },
        url=url,
        source="monitor",
        note="自定义规则配置" if config else None,
    )
    store.append(record, owner, repo)
    diff = analyze_trend(store.load(owner, repo))

    typer.echo(render_trend_terminal(owner, repo, diff))
    if md:
        md.write_text(render_trend_markdown(owner, repo, diff), encoding="utf-8")
        typer.echo(f"趋势 Markdown 已导出：{md}")
    if html:
        html.write_text(render_trend_html(owner, repo, diff), encoding="utf-8")
        typer.echo(f"趋势 HTML 已导出：{html}")


@app.command("trend")
def trend(
    url: str = typer.Argument(..., help="GitHub 仓库 URL / owner/repo"),
    history_dir: Path | None = typer.Option(
        None, "--history-dir", help="历史记录目录（默认 ./.repo-seo-history）"
    ),
    md: Path | None = typer.Option(None, "--md", help="导出趋势 Markdown 报告"),
    html: Path | None = typer.Option(None, "--html", help="导出趋势 HTML 报告（含 SVG 曲线）"),
) -> None:
    """读取历史记录，输出趋势曲线（不发起网络请求）。"""
    try:
        owner, repo = parse_github_url(url)
    except ValueError as e:
        typer.echo(f"[错误] {e}", err=True)
        raise typer.Exit(code=1)
    store = HistoryStore(history_dir)
    diff = analyze_trend(store.load(owner, repo))
    typer.echo(render_trend_terminal(owner, repo, diff))
    if md:
        md.write_text(render_trend_markdown(owner, repo, diff), encoding="utf-8")
        typer.echo(f"趋势 Markdown 已导出：{md}")
    if html:
        html.write_text(render_trend_html(owner, repo, diff), encoding="utf-8")
        typer.echo(f"趋势 HTML 已导出：{html}")


if __name__ == "__main__":
    app()
