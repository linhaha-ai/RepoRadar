# RepoRadar

RepoRadar is an open-source GitHub repository SEO and AEO auditing tool designed to help developers optimize their projects for both traditional search engines and large language model retrieval systems. It scans a repository, scores its discoverability across six key dimensions, and—when AI analysis is enabled—generates actionable recommendations to improve how the project appears in GitHub search results and LLM-based Q&A contexts. The tool is built for maintainers, open-source contributors, and AI-first teams who want structured, evidence-based guidance on making their repositories more visible, better understood by search algorithms, and more attractive to both human visitors and AI retrieval pipelines.

---

## Features

- **Multi-channel search optimization** — Evaluates how a repository performs under native GitHub search (GitHub search optimization) and AI-driven retrieval (AEO, LLM retrieval).
- **Structured scoring model** — Six weighted dimensions covering README quality, metadata completeness, AI readiness, search discoverability, engineering health, and project activity.
- **AI-enhanced recommendations** — Optional LLM-powered analysis that produces concrete, copy-paste suggestions for improving documentation, keywords, and semantic coverage.
- **CLI-first design** — Fast, scriptable interface powered by Typer; supports JSON output for integration with CI/CD pipelines and internal dashboards.
- **Graceful degradation** — Uses `httpx` to fetch repository data via GitHub REST API first, then falls back to raw content fetching and HTML page scraping when API access is limited.
- **Private repository support** — Works with private repos when a `GITHUB_TOKEN` with appropriate permissions is provided.
- **README draft generation** — Produces a structured README draft based on the audit results, helping teams iterate quickly on their documentation.

---

## Installation

RepoRadar is currently distributed via source; a PyPI package release is planned. Install from source with:

```bash
git clone https://github.com/linhaha-ai/RepoRadar.git
cd RepoRadar
pip install -e ".[dev]"
```

After installation, the `repo-seo` command-line entry point becomes available.

> **Note:** The PyPI package has not been published yet. Once released, the installation command will be updated accordingly.

### Environment variables

| Variable | Purpose |
|---|---|
| `GITHUB_TOKEN` | Required for private repository access |
| `REPO_SEO_API_KEY` | OpenAI-compatible LLM API key (optional; needed only for AI mode) |
| `REPO_SEO_BASE_URL` | Custom LLM base URL (optional) |
| `REPO_SEO_MODEL` | LLM model identifier (optional) |

---

## Usage

Scan a public or private repository:

```bash
repo-seo scan <repository-url>
```

Equivalent invocation via the Python module:

```bash
python -m repo_seo.cli scan <repository-url>
```

### Common options

```bash
# Run with AI-powered recommendations
repo-seo scan <repository-url> --ai

# Disable AI analysis
repo-seo scan <repository-url> --no-ai

# Export the report as JSON
repo-seo scan <repository-url> --json

# Generate a README draft based on audit results
repo-seo scan <repository-url> --readme-draft

# Specify a custom LLM model and base URL
repo-seo scan <repository-url> --ai --model gpt-4o --base-url https://api.example.com/v1
```

### Example output

The tool prints a score breakdown by dimension and, when `--ai` is enabled, appends a list of actionable recommendations. The `--json` flag writes the same structured data to stdout for programmatic consumption.

---

## Scoring Model

RepoRadar evaluates repositories across six dimensions totaling 100 points:

| Dimension | Max Points |
|---|---|
| README Content Quality | 25 |
| Repository Metadata | 20 |
| AI Retrieval Readiness | 20 |
| Search Discoverability | 15 |
| Engineering Health & Credibility | 10 |
| Project Activity | 10 |

A higher score indicates stronger alignment with both GitHub search indexing signals and AI retrieval best practices. Scores are computed deterministically from static analysis; the AI module adds qualitative recommendations on top but does not modify the numerical score.

---

## Limitations

- **Static audit, not a ranking system** — The score reflects document quality and signal completeness against a curated checklist. It does not predict actual GitHub search position or LLM citation frequency.
- **Private repository constraints** — Scanning private repos requires a valid `GITHUB_TOKEN` with at least `repo` scope. Repositories without token access will skip private-data checks.
- **AI recommendations require an LLM key** — The `--ai` flag is optional. Without `REPO_SEO_API_KEY` (or a configured compatible endpoint), AI mode is silently skipped and only the deterministic score is produced.
- **English-first semantics** — While the tool processes repositories in any language, keyword extraction, AI retrieval scoring, and README recommendation quality are optimized for English-language documentation. Non-English repos may receive lower AI-readiness scores due to terminology gaps rather than actual quality deficiencies.
- **No real-time engagement metrics** — The scoring model does not consume stars, forks, or issue counts beyond activity heuristics (e.g., recent commit timestamps). Social proof signals are outside the tool's scope.

---

## FAQ

**Q: Does the score represent the repository's actual ranking on GitHub?**

No. The score is a static audit metric measuring structural quality, metadata completeness, and AI retrieval readiness against a defined rubric. It does not incorporate live search rankings, engagement data, or algorithmic visibility predictions.

**Q: How do I scan a private repository?**

Set the `GITHUB_TOKEN` environment variable to a personal access token with `repo` scope before running the scan command. The tool will use the token to authenticate API and raw content requests.

**Q: How do I enable AI-powered recommendations?**

Add the `--ai` flag to the scan command and ensure one of the following is configured: set `REPO_SEO_API_KEY` to a valid OpenAI-compatible API key, or provide both `REPO_SEO_BASE_URL` and `REPO_SEO_MODEL`. Without these, `--ai` will produce a score only with no generated recommendations.

**Q: Does RepoRadar support repositories written in languages other than English?**

Yes. The tool scans any GitHub repository regardless of language. However, the AI-readiness and search-discoverability dimensions are calibrated toward English-language SEO and AEO practices. Non-English projects may receive lower scores in those dimensions because the detection heuristics are primarily trained on English documentation patterns.

**Q: Is there a pip-installable package?**

Not yet. The project is currently installed from source using `pip install -e ".[dev]"`. A PyPI release is planned; once published, an installation command such as `pip install repo-seo` will be added to this document.

---

*RepoRadar · Apache-2.0 · GitHub: linhaha-ai/RepoRadar*
