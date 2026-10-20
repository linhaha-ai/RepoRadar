"""测试 fixtures：构造 RepoSnapshot 与 README 样例。"""

from __future__ import annotations

from repo_seo.model import RepoSnapshot, Visibility

GOOD_README = """# RepoRadar

RepoRadar is a CLI tool that monitors your GitHub repositories and reports search & AI discoverability issues with actionable fixes. It helps open-source maintainers improve ranking in GitHub search and AI assistants like ChatGPT, Perplexity and Gemini.

## Features

- Scan any public GitHub repo
- Detect weak README structure
- Score metadata and topics
- Generate optimization report

## Installation

pip install repo-seo

## Quick Start

```python
import reposeo
reposeo.scan("owner/repo")
```

## Use Cases

- OSS maintainers preparing a launch
- Marketing teams auditing repo visibility
- AI content teams checking AEO readiness

## FAQ

### Does it support Windows?
Yes, it works on Windows, macOS and Linux.

## Limitations

Requires Python 3.11+. Network access to api.github.com.

## License

MIT
"""

MINIMAL_README = """# My Project

A small test.
"""


def make_snapshot(**overrides) -> RepoSnapshot:
    defaults: dict = {
        "full_name": "owner/repo",
        "owner": "owner",
        "name": "repo",
        "description": "A CLI tool that monitors GitHub repositories for search and AI discoverability",
        "topics": ["cli", "github", "seo", "discoverability", "monitoring", "ai"],
        "language": "Python",
        "license_spdx": "MIT",
        "visibility": Visibility.PUBLIC,
        "default_branch": "main",
        "homepage": None,
        "has_pages": False,
        "archived": False,
        "created_at": "2026-10-01T00:00:00Z",
        "pushed_at": "2026-10-15T00:00:00Z",
        "stars": 10,
        "forks": 2,
        "open_issues": 2,
        "watchers": 5,
        "readme_text": GOOD_README,
        "readme_source": "api",
        "root_files": ["LICENSE", "README.md", ".gitignore", "src/main.py", "tests/test_main.py", ".github/workflows/ci.yml"],
        "has_license_file": True,
        "has_ci": True,
        "has_tests": True,
        "has_gitignore": True,
        "has_contributing": False,
        "has_code_of_conduct": False,
        "releases": [{"tag": "v0.1.0", "published_at": "2026-10-10T00:00:00Z"}],
        "contributors": [{"login": "a", "contributions": 10}, {"login": "b", "contributions": 5}],
        "fetch_errors": [],
    }
    defaults.update(overrides)
    return RepoSnapshot(**defaults)
