"""D5 工程健康与可信度（10 分）：H01-H05。

工程健康只评价「项目是否可靠」，不宣称其能直接提高搜索排名（DESIGN.md §1.4）。
"""

from __future__ import annotations

from ..model import (
    CheckType,
    RepoSnapshot,
    Rule,
    result_fail,
    result_pass,
)

_PKG_FILES = ("package.json", "pyproject.toml", "setup.py", "setup.cfg",
              "requirements.txt", "Cargo.toml", "go.mod", "pom.xml", "build.gradle")


def _check_h01(snap: RepoSnapshot):
    if snap.has_license_file and snap.license_spdx:
        return result_pass(RULES[0], f"LICENSE 存在（SPDX: {snap.license_spdx}）", "许可清晰，AI 可放心推荐")
    if snap.has_license_file:
        return result_fail(
            RULES[0], 1.0, "LICENSE 文件存在但 SPDX 未识别",
            "许可标识不清会影响 AI 对可商用性的判断",
            "使用标准许可（MIT/Apache-2.0/GPL-3.0 等）", None,
        )
    return result_fail(
        RULES[0], 0.0, "无 LICENSE 文件",
        "AI 推荐开源项目时会过滤无许可仓库（法律风险）",
        "添加 LICENSE（MIT/Apache-2.0 常见），并确保 license 字段可被识别", None,
    )


def _check_h02(snap: RepoSnapshot):
    if snap.has_ci:
        return result_pass(RULES[1], "检测到 CI 配置（.github/workflows 等）", "自动化检查增强可信度")
    return result_fail(
        RULES[1], 0.0, "无 CI 配置",
        "无 CI 表明构建与测试未经自动验证，用户与 AI 信任度下降",
        "添加 GitHub Actions workflow（lint + test）", None,
    )


def _check_h03(snap: RepoSnapshot):
    if snap.has_tests:
        return result_pass(RULES[2], "检测到 tests/spec 目录或测试配置", "有质量保障信号")
    return result_fail(
        RULES[2], 0.0, "无测试目录/测试配置",
        "无测试的项目被判定为未验证，影响可信度",
        "创建 tests/ 目录并添加最小单元测试", None,
    )


def _check_h04(snap: RepoSnapshot):
    if not snap.releases:
        return result_fail(
            RULES[3], 0.0, "无 Release",
            "无版本发布说明项目尚未对外交付，AI 引用时缺乏版本锚点",
            "发布 v0.1.0 Release，写清版本说明（语义化版本）", None,
        )
    latest = snap.releases[0]
    tag = latest.get("tag") or ""
    if tag.startswith("v") or any(c.isdigit() for c in tag):
        return result_pass(RULES[3], f"最近 Release：{tag}", "版本管理规范")
    return result_fail(
        RULES[3], 1.0, f"Release tag 不规范：{tag}",
        "非语义化版本不利于依赖方与 AI 识别稳定性",
        "使用语义化版本 vX.Y.Z", None,
    )


def _check_h05(snap: RepoSnapshot):
    pkg = next((f for f in snap.root_files if f in _PKG_FILES), None)
    if pkg:
        return result_pass(RULES[4], f"检测到依赖/包声明：{pkg}", "依赖与安装信息存在（字段完整性 V2 读取内容）")
    return result_fail(
        RULES[4], 0.0, "无包元信息文件（package.json / pyproject.toml 等）",
        "缺少依赖/安装声明，用户无法标准安装，AI 无法解析技术信息",
        "添加包元信息文件并填写 description / keywords", None,
    )


RULES: list[Rule] = [
    Rule("H01", "health", "License 与开源许可说明", 2.0, CheckType.HARD, "P0",
         "LICENSE 文件存在且 SPDX 可识别", _check_h01),
    Rule("H02", "health", "CI 与自动化检查", 2.0, CheckType.HARD, "P1",
         "存在 CI 配置", _check_h02),
    Rule("H03", "health", "测试及质量保障", 2.0, CheckType.HARD, "P1",
         "存在 tests/spec 目录或测试配置", _check_h03),
    Rule("H04", "health", "Release 与版本管理", 2.0, CheckType.HARD, "P2",
         "有 ≥1 个语义化 Release", _check_h04),
    Rule("H05", "health", "依赖、安装及安全信息", 2.0, CheckType.HARD, "P2",
         "存在包元信息文件", _check_h05),
]
