# RepoRadar

**Languages / 语言：** [English](README.md) | [简体中文](README_zh-CN.md)

RepoRadar is a Python CLI tool that scores any GitHub repository's discoverability (0–100) across GitHub native search and LLM retrieval pipelines, then delivers evidence-backed remediation guidance so open-source projects become easier to find, understand, and correctly cited. Designed for maintainers who want measurable **GitHub search optimization** without hiring an SEO agency, it applies 29 deterministic rules across six dimensions—README quality, metadata, AI retrieval readiness, search discoverability, engineering health, and project activity—so you get exactly what's missing and why. Whether you are launching a new package or reviving a dormant repo, RepoRadar gives you a clear **AEO** (Answer Engine Optimization) roadmap: score, diagnose, fix, and verify. Built on Python 3.11+ with httpx-based three-tier fetching (REST API / raw / web fallback), optional OpenAI-compatible LLM recommendation generation, and comprehensive unit test coverage, it runs entirely locally and integrates naturally into CI or developer workflows. This repository itself is currently scored at 73.3/100 by RepoRadar, reflecting the tool's diagnostic honesty.
## Overview

RepoRadar addresses a critical but under-metricized problem: most open-source projects are invisible to both traditional search engines and modern AI answer engines because their READMEs, metadata, and documentation signals are incomplete or misstructured. Unlike generic SEO audits, RepoRadar is purpose-built for repository discoverability—treating README content, code structure, topics, license, and activity as ranked signals that both human searchers and LLM retrieval systems depend on.

The tool outputs a **score + evidence report** where every deduction includes the rule violated, the exact gap, a corrective explanation, and copy-paste-ready template text. Priority tiers (P0 / P1 / P2) surface the three most impactful fixes first. An optional `--ai` flag invokes any OpenAI-compatible LLM endpoint (Agnes, Doubao/Volcano Ark, DeepSeek, OpenAI, etc.) to generate context-aware narrative suggestions tailored to the scanned repository's actual content; LLM failures fall back to rule-based template suggestions automatically. Structured JSON export via `--json` makes results machine-readable for dashboards and automation.

**Keywords tracked**: GitHub search optimization · AEO · LLM retrieval · repository discoverability · SEO score

## Features

- **29-rule diagnostic engine** covering six scoring dimensions for a balanced, explainable 0–100 score
- **Three-state evidence model**: each rule reports `PASS` / `FAIL` / `N/A·UNDETECTABLE`; N/A items are excluded from the denominator (no penalty)
- **P0/P1/P2 priority triage** with Top 3 must-fix problems highlighted at the top of every report
- **`--ai` LLM-powered recommendations** against any OpenAI-compatible endpoint with automatic fallback to rule templates
- **`--json` structured export** containing per-rule evidence, scores, and fix suggestions for programmatic consumption
- **Three-tier fetcher**: GitHub REST API → raw content → HTML page fallback, maximising coverage when endpoints are unavailable
- **Private repo support** via `GITHUB_TOKEN` environment variable
- **One-click apply (Web UI)**: downloads your repository into a local workspace, rewrites the README, creates missing safe docs, and returns a reviewable unified diff — no commit or push
- **Shareable deep links**: opening `http://localhost:8000/owner/repo` loads that repository's most recent saved report instantly (auto-scans on first visit); after each scan the address bar syncs to `/owner/repo`
- **Last optimize plan persisted per repo**: the 一键优化 tab instantly re-displays the most recent generated plan (timestamped, no LLM re-call); a fresh generation overwrites the stored one
- **124 passing tests** across fetcher, rule, scoring, AI-suggestion, report, config, verification, workspace, trend, and web-routing modules

## Installation

Install from source (PyPI release is planned but not yet published):

```bash
git clone https://github.com/linhaha-ai/RepoRadar.git
cd RepoRadar
pip install -e ".[dev]"
```

After installation the `repo-seo` command becomes available on your PATH.

**Required environment variables:**

| Variable | Purpose |
|---|---|
| `GITHUB_TOKEN` | Access private repositories |
| `REPO_SEO_API_KEY` | OpenAI-compatible LLM API key (optional, used only with `--ai`) |
| `REPO_SEO_BASE_URL` | Custom LLM base URL (optional) |
| `REPO_SEO_MODEL` | Target LLM model name (optional) |

## Docker Deployment (Docker Compose)

The fastest way to try RepoRadar end to end is the one-command Docker Compose deployment, which starts the Web UI (the CLI is included in the same image):

```bash
git clone https://github.com/linhaha-ai/RepoRadar.git
cd RepoRadar
docker compose up -d --build
```

Then open <http://localhost:8000> in your browser and scan any repository.

Optional: copy `.env.example` to `.env` and fill in the keys (the compose file reads them automatically):

| Variable | Purpose |
|---|---|
| `GITHUB_TOKEN` | Access private repositories / higher API rate limits (optional) |
| `REPO_SEO_API_KEY` | OpenAI-compatible LLM API key for AI suggestions, README drafts, AEO probes (optional) |
| `REPO_SEO_BASE_URL` | Custom LLM base URL |
| `REPO_SEO_MODEL` | Target LLM model name |
| `REPO_SEO_PROBE_MODELS` | Comma-separated models for multi-model AEO probes (optional) |
| `GOOGLE_CSE_API_KEY` / `GOOGLE_CSE_ID` | Google indexing verification (optional) |

Notes:

- Scan history persists in the named volume `repo-seo-history`, so container rebuilds do not lose data.
- Local one-click apply workspaces persist in the named volume `repo-seo-workspaces`.
- Stop and remove the container with `docker compose down` (the volume is kept by default).
- Environment variable precedence: host shell > `.env` > compose defaults.

## Usage

### Basic scan (public repository, no token needed)

```bash
repo-seo scan https://github.com/linhaha-ai/RepoRadar
```

### Generate AI-powered recommendations

```bash
repo-seo scan owner/repo --ai
```

### Disable AI (rule-template mode only)

```bash
repo-seo scan owner/repo --no-ai
```

### Export structured JSON report

```bash
repo-seo scan owner/repo --json report.json
```

### Use a custom LLM endpoint

```bash
REPO_SEO_API_KEY=sk-xxx REPO_SEO_BASE_URL=https://api.example.com/v1 REPO_SEO_MODEL=example-model \
repo-seo scan owner/repo --ai
```

### Apply fixes locally (Web UI)

Open the Web UI, scan your repository, then click **一键优化并应用** (One-click optimize & apply). RepoRadar:

1. verifies that `GITHUB_TOKEN` has push access to the repository (own repos only; otherwise it falls back to a read-only plan);
2. downloads a tarball snapshot into `REPO_SEO_WORKSPACE_DIR` (no local git required) and reuses the existing copy unless `refresh` is requested;
3. writes an AI-generated README and creates missing allow-listed files (`CONTRIBUTING.md`, `SECURITY.md`, `.gitignore`, `.github/*`, etc.);
4. returns `applied / skipped / manual` lists plus a **unified diff** rendered in the browser.

Safety: **local files only — never commit or push**; the README is rewritten, while existing allow-listed files are skipped; LICENSE is never auto-generated; path traversal and symlinks are rejected during extraction.

API: `POST /api/optimize/apply` with `{"url": "owner/repo", "refresh": false}`.

## Scoring Model

The 0–100 score is distributed across six deterministic dimensions:

| Dimension | Max Points | What It Measures |
|---|---|---|
| README Content Quality | 25 | Value proposition & positioning, keyword/semantic coverage, quick-start & usage examples, structure & link integrity, AEO-friendly content |
| Repository Metadata | 20 | Repo name, description, topics, primary language, homepage/docs links |
| AI Retrieval Readiness | 20 | Entity & identity clarity, function & use-case expression, citable facts & examples, structured documentation, information consistency & limitations |
| Search Discoverability | 15 | Page accessibility, indexing evidence, docs crawlablity, sitemap & canonical URLs, internal/external link integrity |
| Engineering Health & Credibility | 10 | License, CI, tests, releases/versioning, dependency & security info |
| Project Activity | 10 | Recent maintenance, issue handling, release cadence, contribution activity |

Each of the 29 rules evaluates to one of three states:

- **PASS** — rule satisfied, full points awarded
- **FAIL** — rule violated, points deducted with evidence and suggested fix
- **N/A · UNDETECTABLE** — rule inapplicable or data unavailable; excluded from scoring denominator so no implicit penalty is applied

Results include **Top 3 highest-priority fixes** and a full priority-laddered remediation list (P0 → P1 → P2).

## FAQ

**Does the RepoRadar score equal my actual GitHub or Google ranking?**

No. The score measures *optimization readiness*—how well the repository's static content is prepared for discovery—not live search position. Rankings depend on dynamic signals (backlinks, stars, traffic) that a static audit cannot capture.

**How do I scan a private repository?**

Set the `GITHUB_TOKEN` environment variable to a GitHub Personal Access Token with `repo` scope before running `repo-seo scan`. Without it, private repositories will return restricted data and receive lower discoverability scores.

**Can I enable AI suggestions without paying for OpenAI?**

Yes. Configure any OpenAI-compatible endpoint (Agnes, Doubao/火山方舟, DeepSeek, local Ollama, etc.) via `REPO_SEO_API_KEY`, `REPO_SEO_BASE_URL`, and `REPO_SEO_MODEL`. If none of these are set, or if the LLM call fails, the tool falls back automatically to rule-template suggestions.

**Does RepoRadar support repositories written in any programming language?**

Yes. The scanning logic operates on repository metadata, README structure, file topology, and keywords—not on language-specific code analysis. Languages are treated as metadata signals within the metadata and discoverability dimensions.

**How do I install RepoRadar and start scanning?**

See the [Installation](#installation) and [Usage](#usage) sections above. Clone the repo, install with `pip install -e ".[dev]"`, then run `repo-seo scan <url>`.

## Limitations

- **Static audit only**: scores reflect content optimization readiness, not live search or ranking positions. External verification is provided via `--verify` (Google indexing check + multi-model AEO probes).
- **Private repositories are inherently limited in discoverability**: even with a valid scan, GitHub search and AI crawlers cannot index private content, so discoverability scores will be lower by design.
- **AI suggestions require an API key**: the `--ai` flag needs a configured OpenAI-compatible key. Without one, the tool still produces accurate rule-based scores and template recommendations—just without LLM-generated narrative text.
- **One-click apply is local-only**: it modifies a workspace copy, does not commit or push, only creates allow-listed files, and requires a `GITHUB_TOKEN` with push access to the target repository.
- **PyPI availability**: the package is distributed via source installation at present; a formal `pip install repo-seo` release is on the roadmap but not yet published.
- **External crawling coverage**: the three-tier fetcher (REST API → raw → web) maximises reach, but some repositories may have rate-limited or restricted endpoints that cause partial data loss.

## Use Cases

- **New open-source launches**: run RepoRadar before publishing to catch foundational README and metadata gaps.
- **Project maintenance & revival**: diagnose why a previously active repository has dropped in visibility and prioritize fixes.
- **CI/CD integration**: embed `repo-seo scan --json` in pull-request checks to enforce minimum discoverability standards across team repositories.

---

*RepoRadar is licensed under Apache-2.0. This README was itself generated using RepoRadar's own `--ai` optimization pipeline.*
