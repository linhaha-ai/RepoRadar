# linhaha-ai/RepoRadar · 仓库可发现性评分报告

**仓库**：`linhaha-ai/RepoRadar`（私有，默认分支 `main`）

## 总分：**16.5 / 100**

> 总分代表仓库的优化准备度，不代表真实搜索排名；静态审计 ≠ 真实曝光。

## 维度得分

| 维度 | 得分 | 满分 | 得分率 |
|---|---:|---:|---:|
| README 内容质量 | 0.0 | 25.0 | 0% |
| 仓库元数据 | 8.5 | 20.0 | 42% |
| AI 检索准备度 | 0.0 | 20.0 | 0% |
| 搜索可发现性 | 0.0 | 6.0（可评分 6） | 0% |
| 工程健康与可信度 | 2.0 | 10.0 | 20% |
| 项目活跃度 | 4.0 | 7.0（可评分 7） | 57% |

## 最优先修复的问题

1. **[P0] Topics**（metadata 维度，扣 6.0 分）
   - 证据：Topics 为空
   - 建议：添加 6~12 个精准标签（大类 + 技术栈 + 场景长尾）
2. **[P0] 项目定位与价值主张**（readme 维度，扣 5.0 分）
   - 证据：README 缺失或首段为空
   - 建议：在 H1 标题后补充一段：项目是什么 + 解决什么问题 + 目标用户
3. **[P0] 关键词与语义覆盖**（readme 维度，扣 5.0 分）
   - 证据：README 缺失
   - 建议：先创建 README

## 优化建议（AI 生成）

- **[P0] R01 · README 缺失，项目定位与价值主张无法传递**
  - 建议：立即创建 README.md，首段必须包含：项目名称 + 核心功能（GitHub 搜索 + AI 大模型检索）+ 解决什么问题（AEO 曝光不足）+ 目标用户（开源项目维护者、SEO 从业者）
  - 原因：R01 要求 README 首段 ≥60 字符且说明是什么+解决什么，当前 README 缺失导致所有 readme/aeo 检查项连锁失败
  - 示例：`# RepoRadar

RepoRadar 是开源项目的搜索引擎优化（AEO）体检与曝光优化工具。帮助开发者通过结构化 README 与 metadata 诊断，提升项目在 GitHub 搜索、Google Web Search 及 AI 大模型检索中的可见度。

## 适用场景
- 开源项目上架前的 SEO/AEO 自检
- 项目 README 内容审计与关键词覆盖优化
- 多语言（中文/英文）技术栈项目的公开化准备`
- **[P0] R02 · README 缺失，核心关键词（AEO、GitHub 搜索、AI 大模型检索）无法自然出现**
  - 建议：在创建的 README 中自然嵌入核心词 ≥3 次：'AEO'、'GitHub 搜索'、'AI 大模型检索'，避免堆砌，穿插在功能说明与使用场景中
  - 原因：R02 要求核心词自然出现 ≥3 次且无堆砌，SEO/AEO 项目的 README 必须明确技术关键词
  - 示例：`RepoRadar 专注于 **AEO**（Artificial Intelligence Engine Optimization）领域，解决开源项目在 GitHub 搜索与 AI 大模型检索中的曝光痛点。通过关键词覆盖、语义结构与快速开始示例的自动化审计，帮助项目从'可见'走向'可被发现'。`
- **[P0] R03 · README 缺失，无可复制安装命令与代码示例**
  - 建议：在 README 中添加 '快速开始' H2 章节，包含 pip/npm/go install 命令 + Python/TypeScript 示例代码块
  - 原因：R03 要求有可复制安装命令 + ≥1 个带语言代码示例，这是技术项目 README 的基础结构
  - 示例：`## 快速开始

```bash
# 使用 pip 安装
pip install reporadar

# 或使用 npm
npm install @reporadar/core
```

```python
from reporadar import audit
result = audit('your-repo')
print(f'AEO Score: {result.score}/100')
````
- **[P1] R04 · README 缺失，H1 唯一性、层级连续、代码块语言标注等结构规范无法验证**
  - 建议：创建 README 时确保：H1 只有一个（# RepoRadar）、H2 章节连续、所有代码块标注语言（python/bash/toml）
  - 原因：R04 要求 H1 唯一、层级连续、代码块有语言标注，这是结构化文档的基础
  - 示例：`# RepoRadar

## 功能
- README 体检
- metadata 诊断

## 安装
```bash
pip install reporadar
````
- **[P1] R05 · README 缺失，无法提供 FAQ/使用场景/限制说明等 AEO 友好内容**
  - 建议：在 README 末尾添加 FAQ 或 '已知限制' 章节，提升 AI 模型引用时的可回答性与可信度
  - 原因：R05 要求含 FAQ/使用场景/限制说明之一，这是 AEO 友好的重要标志
  - 示例：`## FAQ

**Q: RepoRadar 支持哪些语言？**
A: 目前支持 Python、TypeScript、Go 项目，未来将扩展至 Rust、Java。

**Q: 体检结果多久更新一次？**
A: 实时扫描，无缓存延迟。

## 已知限制
- 私有仓库需设置 `--private` 标志并传入 Token`
- **[P0] M02 · Description 核心词未前置，当前为'GitHub 项目搜索优化...'，'AEO'被埋没**
  - 建议：将 Description 重写为：'AEO 开源项目体检工具 — GitHub 搜索 + AI 大模型检索曝光优化'
  - 原因：M02 要求核心词前置且 ≤350 字符，当前'GitHub 项目搜索优化'未突出 AEO 这一核心技术词
  - 示例：`AEO 开源项目体检工具 — GitHub 搜索 + AI 大模型检索曝光优化，帮助开发者提升开源项目在搜索引擎与 LLM 中的可见度。`
- **[P0] M03 · Topics 为空，无法通过标签被搜索发现**
  - 建议：添加 6~12 个精准标签，覆盖大类（opensource、seo）、技术栈（python、typescript）、场景长尾（aeo、github-search）
  - 原因：M03 要求 1~20 个 Topics、≥6 最佳，与主题语义相关，当前为空导致零标签覆盖
  - 示例：`aeo, github-search, open-source, seo-tools, ai-models, python, typescript, developer-tools, metadata-audit, visibility-optimization, search-exposure, readme-audit`
- **[P2] M04 · 主语言未识别，仓库无代码提交导致 GitHub 无法判定**
  - 建议：提交至少一个代码文件（如 src/main.py 或 index.ts）让 GitHub 识别主语言
  - 原因：M04 要求 language 非空，当前仓库无代码文件，语言识别为 unknown
  - 示例：`创建 `src/main.py` 或 `index.ts` 等入口文件，即使只是空函数定义，也能让 GitHub 识别为 Python/TypeScript 项目。`
- **[P2] M05 · Homepage 未设置，无官网或演示链接**
  - 建议：在仓库 Settings 的 Website 填入 GitHub Pages 地址（https://linhaha-ai.github.io/reporadar）
  - 原因：M05 要求 Homepage 非空且为 http(s)，用于外部链接与文档站指向
  - 示例：`仓库 → Settings → Pages → Source: main branch /docs
Settings → About → Website: https://linhaha-ai.github.io/reporadar`
- **[P0] A01 · README 缺失，实体与项目身份清晰度为零**
  - 建议：创建 README 后，首段必须包含项目名 'RepoRadar' 且明确技术栈（Python/TypeScript + AI 大模型）
  - 原因：A01 要求 README 含项目名且首段明确技术栈，当前 README 缺失导致身份无法识别
  - 示例：`# RepoRadar

基于 Python 与 LLM API 的 AEO（Artificial Intelligence Engine Optimization）体检工具，专为开源项目设计。`
- **[P1] A02 · README 缺失，功能与适用场景无法表达**
  - 建议：在 README 中添加 'Use Cases' 或 '适用场景' H2 章节，说明项目解决的 3~5 个具体问题
  - 原因：A02 要求含 Use Cases/适用场景段落，这是 AEO 内容表达的核心
  - 示例：`## Use Cases

1. 开源项目上架前的 README 健康度自检
2. 提升项目在 Google 与 GitHub 搜索中的关键词排名
3. 为 AI 大模型（Claude/GPT）提供结构化、可引用的项目描述`
- **[P1] A03 · README 缺失，无可引用的事实与代码示例**
  - 建议：添加'功能清单'表格 + 至少一个带语言标注的代码示例
  - 原因：A03 要求有代码示例 + 功能清单，这是 AI 模型引用的核心素材
  - 示例：`| 功能 | 说明 |
|------|------|
| README 体检 | 扫描 R01-H05 共 23 项检查 |
| 关键词覆盖 | 自动检测核心词出现次数 |

```python
from reporadar import scan
result = scan('my-project')
````
- **[P1] A04 · README 缺失，无法提供结构化章节与列表/表格组织**
  - 建议：创建 README 时使用 H2 章节 ≥3 个，包含功能清单表格、安装步骤列表、FAQ 问答表
  - 原因：A04 要求 H2 章节 ≥3 且有列表/表格，这是结构化文档的标志
  - 示例：`## 功能
- 实时体检
- 自动生成建议

## 安装
- pip install
- npm install

## 对比
| 维度 | RepoRadar | 手动检查 |
|------|-----------|----------|
| 速度 | 5s | 30min |
| 覆盖 | 23 项 | 不确定 |`
- **[P1] A05 · README 缺失，无法提供信息一致性与限制说明**
  - 建议：在 README 末尾添加'已知限制'或'兼容性说明'章节，避免夸大词（如'最强大''唯一'）
  - 原因：A05 要求无夸大词且有限制/兼容说明，提升 AI 引用时的可信度
  - 示例：`## 已知限制
- 仅支持 GitHub 仓库，GitLab 暂不支持
- 私有仓库需要手动传入 Token

## 兼容性
- Python 3.8+
- Node.js 16+`
- **[P0] D01 · 仓库为私有，完全无法被外部搜索引擎抓取**
  - 建议：将仓库设为 Public；若为内部工具，用 Token 本地体检即可，无需公开
  - 原因：D01 要求公开且非归档，私有仓库对外曝光为零，任何 SEO/AEO 优化无效
  - 示例：`仓库 → Settings → Danger Zone → Change visibility → Public
（开发期可用 `--private` 模式本地运行体检，不影响结果）`
- **[P1] D05 · README 缺失，无有效内外部链接**
  - 建议：创建 README 后添加文档站链接（GitHub Pages）、示例仓库链接、Issue 模板链接
  - 原因：D05 要求 README 含有效 http(s) 链接，提升可跳转性与外部引用
  - 示例：`[文档](https://linhaha-ai.github.io/reporadar/docs)
[示例项目](https://github.com/linhaha-ai/reporadar-example)
[提交 Issue](https://github.com/linhaha-ai/reporadar/issues/new)`
- **[P1] H02 · 无 CI 配置，代码质量与发布流程缺乏自动化**
  - 建议：添加 `.github/workflows/ci.yml`，配置 lint + test 步骤，PR 时自动触发
  - 原因：H02 要求存在 CI 配置，GitHub Actions 是最常见的开源 CI 方案
  - 示例：`.github/workflows/ci.yml:
```yaml
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install -e .
      - run: pytest tests/ -v
````
- **[P1] H03 · 无测试目录与测试配置**
  - 建议：创建 `tests/` 目录，添加至少 1 个最小单元测试（如测试关键词计数逻辑）
  - 原因：H03 要求存在 tests/spec 目录或测试配置，测试覆盖率反映项目成熟度
  - 示例：`tests/test_keywords.py:
```python
from reporadar.keywords import count

def test_count():
    assert count('AEO', 'AEO is great') == 1
````
- **[P2] H04 · 无 Release，版本管理缺失**
  - 建议：发布 v0.1.0 Release，写清语义化版本说明（Initial release with core audit）
  - 原因：H04 要求有 ≥1 个语义化 Release，Release 是外部引用的稳定锚点
  - 示例：`GitHub → Releases → Draft new release
Tag: v0.1.0
Title: Initial Release
Body: First release of RepoRadar with README audit and metadata diagnosis.`
- **[P2] H05 · 无包元信息文件，依赖与安装信息缺失**
  - 建议：根据主语言添加对应包文件：Python 用 pyproject.toml，Node.js 用 package.json
  - 原因：H05 要求存在包元信息文件，用于依赖管理与安装说明
  - 示例：`pyproject.toml:
```toml
[project]
name = 'reporadar'
version = '0.1.0'
description = 'AEO 开源项目体检工具'
keywords = ['aeo', 'seo', 'github']
````
- **[P2] AC03 · 180 天内无 Release，版本更新活动为零**
  - 建议：发布语义化版本 v0.1.0 并写 Release Notes，之后每 30 天推送一个小版本
  - 原因：AC03 要求 180 天内有 Release，体现项目活跃维护
  - 示例：`发布 v0.1.0，之后每周二推送 patch（v0.1.1、v0.1.2），保持月均 1~2 个 Release。`
- **[P2] AC04 · 贡献者仅 1 人且无 CONTRIBUTING 文件，协作门槛高**
  - 建议：添加 CONTRIBUTING.md 说明本地设置、PR 流程、代码规范，或邀请 1~2 名协作者
  - 原因：AC04 要求贡献者 ≥2 或有 CONTRIBUTING，当前仅 1 人且无协作指南
  - 示例：`CONTRIBUTING.md:
```
## 本地设置
pip install -e '.[dev]'

## 提交 PR
1. Fork 本仓库
2. 创建 feature 分支
3. 运行 pytest tests/ 通过
4. 提交 Pull Request
````

## 扣分项证据清单

- **[R01] 项目定位与价值主张**：0.0/5
  - 证据：README 缺失或首段为空
  - 原因：AI 与 GitHub 搜索把 README 首段当作项目定位的第一信息源
  - 示例：`RepoRadar is a CLI tool that scans any GitHub repo and reports its search & AI discoverability issues with actionable fixes.`
- **[R02] 关键词与语义覆盖**：0.0/5
  - 证据：README 缺失
  - 原因：无内容可供关键词匹配
- **[R03] 快速开始与使用示例**：0.0/5
  - 证据：README 缺失
  - 原因：无安装/示例内容
- **[R04] 内容结构与链接完整性**：0.0/5
  - 证据：README 缺失
  - 原因：无结构可言
- **[R05] AEO 友好内容**：0.0/5
  - 证据：README 缺失
  - 原因：无 AEO 内容
- **[M02] Description**：4.5/6
  - 证据：非空✅；≤350✅；核心词未前置❌；英文为主✅
  - 原因：Description 是 GitHub 搜索摘要、Google 标题与 AI 读取的第一信息来源
  - 示例：`Lightweight TypeScript ORM for SQLite, zero dependencies, supports migration and batch insert.`
- **[M03] Topics**：0.0/6
  - 证据：Topics 为空
  - 原因：无 Topics 时 GitHub 与 AI 无法进行主题归类与相关搜索匹配
  - 示例：`typescript, sqlite, orm, database, nodejs, migration, zero-dependency`
- **[M04] 主语言与分类定位**：0.0/2
  - 证据：language 未识别（仓库无代码提交）
  - 原因：无主语言时项目类别定位缺失，相关技术栈搜索无法命中
- **[M05] 官网/文档/演示链接**：0.0/2
  - 证据：未设置 Homepage
  - 原因：缺少官网/文档/演示入口，用户与 AI 少一个信任与理解通道
- **[A01] 实体与项目身份清晰度**：0.0/4
  - 证据：README 缺失
  - 原因：AI 无内容可提取身份信息
- **[A02] 功能与适用场景表达**：0.0/4
  - 证据：README 缺失
  - 原因：无场景表达
- **[A03] 可引用的事实与示例**：0.0/4
  - 证据：README 缺失
  - 原因：无可引用内容
- **[A04] 结构化文档与语义组织**：0.0/4
  - 证据：README 缺失
  - 原因：无结构可评估
- **[A05] 信息一致性与限制说明**：0.0/4
  - 证据：README 缺失
  - 原因：无法评估一致性
- **[D01] 仓库页面可访问性**：0.0/3
  - 证据：仓库为私有（visibility=private）
  - 原因：私有仓库无法被 GitHub 搜索、Google、AI 爬虫访问，可发现性为 0
  - 示例：`Settings → General → Danger Zone → Change visibility → Public`
- **[D05] 内外部链接完整性**：0.0/3
  - 证据：README 缺失
  - 原因：无链接可指引用例/文档，AI 无法通过链接扩展信息
- **[H02] CI 与自动化检查**：0.0/2
  - 证据：无 CI 配置
  - 原因：无 CI 表明构建与测试未经自动验证，用户与 AI 信任度下降
- **[H03] 测试及质量保障**：0.0/2
  - 证据：无测试目录/测试配置
  - 原因：无测试的项目被判定为未验证，影响可信度
- **[H04] Release 与版本管理**：0.0/2
  - 证据：无 Release
  - 原因：无版本发布说明项目尚未对外交付，AI 引用时缺乏版本锚点
- **[H05] 依赖、安装及安全信息**：0.0/2
  - 证据：无包元信息文件（package.json / pyproject.toml 等）
  - 原因：缺少依赖/安装声明，用户无法标准安装，AI 无法解析技术信息
- **[AC03] Release 与版本更新**：0.0/2
  - 证据：无 Release
  - 原因：无版本发布节奏，AI 与用户难以确认项目在演进
- **[AC04] 贡献活动与协作**：1.0/2
  - 证据：贡献者 ×1 且无 CONTRIBUTING
  - 原因：单人项目缺乏协作入口，社区参与度低

> 注：4 项为不适用/无法检测，已从分母剔除；D02 收录证据需 V2 外部核验。

---

*生成时间：2026-10-19T22:16:06 · 抓取时间：2026-10-19T22:15:06 · RepoRadar（repo-seo）*
