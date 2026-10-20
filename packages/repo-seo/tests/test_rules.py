"""规则引擎 + 六维度规则测试。"""

import pytest

from repo_seo.model import EvidenceStatus
from repo_seo.rules.engine import ALL_RULES, DIMENSION_TOTAL, run_rules, validate_dimensions
from repo_seo.scoring import score_snapshot

from .fixtures import GOOD_README, MINIMAL_README, make_snapshot


def find(results, rule_id):
    return next(r for r in results if r.rule_id == rule_id)


# ---------- 配置校验 ----------

def test_all_rules_count():
    assert len(ALL_RULES) >= 29


def test_dimension_totals_match_weights():
    warnings = validate_dimensions()
    assert warnings == [], warnings


# ---------- D1 README ----------

def test_r01_pass():
    s = make_snapshot()
    r = find(run_rules(s), "R01")
    assert r.status == EvidenceStatus.PASS
    assert r.score_earned == 5.0


def test_r01_fail_short_first_paragraph():
    s = make_snapshot(readme_text=MINIMAL_README)
    r = find(run_rules(s), "R01")
    assert r.status == EvidenceStatus.FAIL
    assert r.score_earned < 5.0


def test_r01_fail_no_readme():
    s = make_snapshot(readme_text=None)
    r = find(run_rules(s), "R01")
    assert r.status == EvidenceStatus.FAIL
    assert r.score_earned == 0.0


def test_r03_pass_install_and_code():
    s = make_snapshot()
    r = find(run_rules(s), "R03")
    assert r.status == EvidenceStatus.PASS
    assert r.score_earned == 5.0


def test_r03_partial_no_install():
    s = make_snapshot(readme_text=GOOD_README.replace("pip install repo-seo", "download from github"))
    r = find(run_rules(s), "R03")
    assert r.status == EvidenceStatus.FAIL
    assert 0 < r.score_earned < 5.0


def test_r05_pass_with_faq():
    s = make_snapshot()
    r = find(run_rules(s), "R05")
    assert r.status == EvidenceStatus.PASS


def test_r05_fail_no_aeo():
    s = make_snapshot(readme_text="""# X\n\nJust a library. Nothing else here at all. No faq, no use case, no limitation, no definition, no requirement.\n""")
    r = find(run_rules(s), "R05")
    assert r.status == EvidenceStatus.FAIL


# ---------- D2 元数据 ----------

def test_m01_pass():
    s = make_snapshot(name="repo-radar")
    r = find(run_rules(s), "M01")
    assert r.status == EvidenceStatus.PASS


def test_m01_fail_generic():
    s = make_snapshot(name="my-demo")
    r = find(run_rules(s), "M01")
    assert r.status == EvidenceStatus.FAIL


def test_m02_pass():
    s = make_snapshot(description="RepoRadar CLI tool that monitors GitHub repositories for search and AI discoverability")
    r = find(run_rules(s), "M02")
    assert r.status == EvidenceStatus.PASS
    assert r.score_earned == 6.0


def test_m02_fail_empty():
    s = make_snapshot(description=None)
    r = find(run_rules(s), "M02")
    assert r.status == EvidenceStatus.FAIL
    assert r.score_earned == 0.0


def test_m03_pass():
    s = make_snapshot(topics=["cli", "github", "seo", "discoverability", "monitoring", "ai"])
    r = find(run_rules(s), "M03")
    assert r.status == EvidenceStatus.PASS


def test_m03_fail_empty():
    s = make_snapshot(topics=[])
    r = find(run_rules(s), "M03")
    assert r.status == EvidenceStatus.FAIL


def test_m03_penalize_irrelevant():
    s = make_snapshot(topics=["javascript", "react", "vue", "angular", "css", "html"])
    r = find(run_rules(s), "M03")
    assert r.status == EvidenceStatus.FAIL  # 与描述无关 → 相关度扣分


def test_m04_pass():
    s = make_snapshot(language="Python")
    assert find(run_rules(s), "M04").status == EvidenceStatus.PASS


# ---------- D3 AEO ----------

def test_a01_pass():
    s = make_snapshot()
    r = find(run_rules(s), "A01")
    assert r.status == EvidenceStatus.PASS


def test_a02_pass():
    s = make_snapshot()
    assert find(run_rules(s), "A02").status == EvidenceStatus.PASS


def test_a03_pass():
    s = make_snapshot()
    assert find(run_rules(s), "A03").status == EvidenceStatus.PASS


def test_a05_pass_no_overclaim():
    s = make_snapshot()
    assert find(run_rules(s), "A05").status == EvidenceStatus.PASS


def test_a05_fail_overclaim():
    s = make_snapshot(readme_text=GOOD_README.replace("It helps", "It is the best tool ever and #1 in the world. It helps"))
    r = find(run_rules(s), "A05")
    assert r.status == EvidenceStatus.FAIL


# ---------- D4 可发现性 ----------

def test_d01_fail_private():
    from repo_seo.model import Visibility
    s = make_snapshot(visibility=Visibility.PRIVATE)
    r = find(run_rules(s), "D01")
    assert r.status == EvidenceStatus.FAIL
    assert r.score_earned == 0.0
    assert r.priority == "P0"


def test_d02_unknown():
    s = make_snapshot()
    r = find(run_rules(s), "D02")
    assert r.status == EvidenceStatus.UNKNOWN


def test_d03_n_a_no_docsite():
    s = make_snapshot(homepage=None, has_pages=False)
    assert find(run_rules(s), "D03").status == EvidenceStatus.N_A
    assert find(run_rules(s), "D04").status == EvidenceStatus.N_A


def test_d03_pass_with_homepage():
    s = make_snapshot(homepage="https://repo-radar.dev")
    assert find(run_rules(s), "D03").status == EvidenceStatus.PASS


def test_d05_pass_links():
    s = make_snapshot(readme_text=GOOD_README + "\nSee [docs](https://example.com/docs).")
    assert find(run_rules(s), "D05").status == EvidenceStatus.PASS


# ---------- D5 工程健康 ----------

def test_h01_pass():
    s = make_snapshot(has_license_file=True, license_spdx="MIT")
    assert find(run_rules(s), "H01").status == EvidenceStatus.PASS


def test_h01_fail_no_license():
    s = make_snapshot(has_license_file=False, license_spdx=None)
    r = find(run_rules(s), "H01")
    assert r.status == EvidenceStatus.FAIL
    assert r.priority == "P0"


def test_h04_pass_release():
    s = make_snapshot(releases=[{"tag": "v0.1.0", "published_at": "2026-10-10T00:00:00Z"}])
    assert find(run_rules(s), "H04").status == EvidenceStatus.PASS


def test_h04_fail_no_release():
    s = make_snapshot(releases=[])
    assert find(run_rules(s), "H04").status == EvidenceStatus.FAIL


# ---------- D6 活跃度 ----------

def test_ac01_pass_recent():
    s = make_snapshot(pushed_at="2026-10-15T00:00:00Z")
    assert find(run_rules(s), "AC01").status == EvidenceStatus.PASS


def test_ac01_fail_stale():
    s = make_snapshot(pushed_at="2026-01-01T00:00:00Z")
    r = find(run_rules(s), "AC01")
    assert r.status == EvidenceStatus.FAIL


def test_ac02_unknown_zero_issues():
    s = make_snapshot(open_issues=0)
    assert find(run_rules(s), "AC02").status == EvidenceStatus.UNKNOWN


def test_ac04_pass_multiple_contributors():
    s = make_snapshot(contributors=[{"login": "a"}, {"login": "b"}])
    assert find(run_rules(s), "AC04").status == EvidenceStatus.PASS


# ---------- 评分聚合 ----------

def test_score_total_range():
    report = score_snapshot(make_snapshot())
    assert 0 <= report.total <= 100
    # 优质 fixture 应该高分
    assert report.total >= 60


def test_score_na_unknown_excluded():
    s = make_snapshot(homepage=None, has_pages=False, open_issues=0)
    report = score_snapshot(s)
    d = report.dimensions["discoverability"]
    # D02 UNKNOWN(4) + D03 N/A(3) + D04 N/A(2) 剔除：15 - 9 = 6
    assert d.eligible == pytest.approx(6.0)
    act = report.dimensions["activity"]
    # AC02 UNKNOWN：10 - 3 = 7
    assert act.eligible == pytest.approx(7.0)


def test_top_issues_p0_first():
    s = make_snapshot(readme_text=None, description=None, topics=[])
    report = score_snapshot(s)
    assert report.top_issues
    assert report.top_issues[0].priority == "P0"


def test_evidence_present_on_fail():
    s = make_snapshot(readme_text=None)
    report = score_snapshot(s)
    for r in report.results:
        if r.status == EvidenceStatus.FAIL:
            assert r.evidence and r.suggestion, f"{r.rule_id} 缺少证据或建议"
