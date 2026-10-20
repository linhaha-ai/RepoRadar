"""URL 解析与健康信号检测的单元测试（M1 冒烟）。"""

from repo_seo.fetcher.fetch import _detect_health_flags
from repo_seo.fetcher.url_parser import parse_github_url
import pytest


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("https://github.com/linhaha-ai/RepoRadar", ("linhaha-ai", "RepoRadar")),
        ("https://github.com/linhaha-ai/RepoRadar.git", ("linhaha-ai", "RepoRadar")),
        ("https://github.com/linhaha-ai/RepoRadar/", ("linhaha-ai", "RepoRadar")),
        ("git@github.com:linhaha-ai/RepoRadar.git", ("linhaha-ai", "RepoRadar")),
        ("linhaha-ai/RepoRadar", ("linhaha-ai", "RepoRadar")),
    ],
)
def test_parse_github_url_ok(raw: str, expected: tuple[str, str]):
    assert parse_github_url(raw) == expected


@pytest.mark.parametrize("bad", ["", "   ", "not-a-url", "https://example.com/x/y"])
def test_parse_github_url_bad(bad: str):
    with pytest.raises(ValueError):
        parse_github_url(bad)


def test_detect_health_flags():
    files = [
        "LICENSE",
        "README.md",
        ".gitignore",
        "src/main.py",
        "tests/test_main.py",
        ".github/workflows/ci.yml",
    ]
    flags = _detect_health_flags(files)
    assert flags["has_license_file"] is True
    assert flags["has_ci"] is True
    assert flags["has_tests"] is True
    assert flags["has_gitignore"] is True
    assert flags["has_contributing"] is False
    assert flags["has_code_of_conduct"] is False
