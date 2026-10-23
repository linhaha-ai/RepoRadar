# RepoRadar

**语言 / Languages：** [简体中文](README_zh-CN.md) | [English](README.md)

RepoRadar 是一个 Python CLI 工具，用于对任意 GitHub 仓库的可发现性进行 0–100 分评分，覆盖 GitHub 原生搜索和 LLM 检索管线，并输出基于证据的修复建议，帮助开源项目更容易被发现、理解和被正确引用。RepoRadar 专为希望获得可衡量的 **GitHub 搜索优化**、又不想聘请 SEO 机构维护者设计：它跨六个维度应用 29 条确定性规则——README 质量、仓库元数据、AI 检索就绪度、搜索可发现性、工程健康度、项目活跃度——让你准确知道缺什么、为什么缺。无论是发布新包还是重振休眠仓库，RepoRadar 都能给你一条清晰的 **AEO**（答案引擎优化）路线图：评分、诊断、修复、验证。基于 Python 3.11+，采用 httpx 三层抓取（REST API / raw / 网页兜底），可选兼容 OpenAI 的 LLM 建议生成，并具备完善的单元测试覆盖；完全本地运行，可自然集成到 CI 或开发者工作流。本仓库自身当前被 RepoRadar 评分为 73.3/100，这体现了工具诊断的诚实性。

## 概览

RepoRadar 解决的是一个关键但缺乏量化指标的问题：大多数开源项目对传统搜索引擎和现代 AI 答案引擎都不可见，因为它们的 README、元数据和文档信号不完整或结构不佳。与通用 SEO 审计不同，RepoRadar 专门面向仓库可发现性——把 README 内容、代码结构、topics、许可证和活跃度视为人类搜索者与 LLM 检索系统都依赖的排序信号。

工具输出一份 **评分 + 证据报告**，每条扣分都包含：违反的规则、具体缺口、修复说明，以及可直接复制粘贴的模板文本。优先级分层（P0 / P1 / P2）会优先呈现影响最大的三项修复。可选的 `--ai` 参数可调用任意兼容 OpenAI 的 LLM 端点（Agnes、豆包/火山方舟、DeepSeek、OpenAI 等），根据被扫描仓库的实际内容生成上下文相关的叙述性建议；LLM 调用失败时自动回退到基于规则的模板建议。通过 `--json` 导出结构化 JSON，结果可被仪表盘和自动化流程直接消费。

**追踪关键词**：GitHub 搜索优化 · AEO · LLM 检索 · 仓库可发现性 · SEO 评分

## 功能特性

- **29 条规则诊断引擎**，覆盖六个评分维度，提供均衡、可解释的 0–100 评分
- **三态证据模型**：每条规则报告 `PASS` / `FAIL` / `N/A·UNDETECTABLE`；N/A 项不计入分母（不扣分）
- **P0/P1/P2 优先级分诊**，每份报告顶部高亮 Top 3 必修复问题
- **`--ai` LLM 建议**：可对接任意兼容 OpenAI 的端点，失败时自动回退到规则模板
- **`--json` 结构化导出**：包含逐条规则的证据、评分和修复建议，供程序化消费
- **三层抓取器**：GitHub REST API → raw 内容 → HTML 页面兜底，在端点不可用时最大化覆盖
- **私有仓库支持**：通过 `GITHUB_TOKEN` 环境变量
- **一键应用修改（Web UI）**：自动下载仓库到本地工作区、重写 README、创建缺失的安全文档，并返回可审阅的 unified diff——不 commit、不 push
- **124 个通过的测试**，覆盖抓取、规则、评分、AI 建议、报告、配置、验证、工作区、趋势和 Web 路由模块

## 安装

从源码安装（PyPI 发布已规划但尚未发布）：

```bash
git clone https://github.com/linhaha-ai/RepoRadar.git
cd RepoRadar
pip install -e ".[dev]"
```

安装完成后，`repo-seo` 命令即可在 PATH 中使用。

**必需的环境变量：**

| 变量 | 用途 |
|---|---|
| `GITHUB_TOKEN` | 访问私有仓库 |
| `REPO_SEO_API_KEY` | 兼容 OpenAI 的 LLM API 密钥（可选，仅 `--ai` 时使用） |
| `REPO_SEO_BASE_URL` | 自定义 LLM base URL（可选） |
| `REPO_SEO_MODEL` | 目标 LLM 模型名（可选） |

## Docker 部署（Docker Compose）

体验 RepoRadar 全流程最快的方式是 Docker Compose 一条命令部署，启动 Web UI（镜像内同时包含 CLI）：

```bash
git clone https://github.com/linhaha-ai/RepoRadar.git
cd RepoRadar
docker compose up -d --build
```

然后在浏览器打开 <http://localhost:8000>，即可扫描任意仓库。

可选：复制 `.env.example` 为 `.env` 并填写密钥（compose 会自动读取）：

| 变量 | 用途 |
|---|---|
| `GITHUB_TOKEN` | 访问私有仓库 / 提升 API 限流（可选） |
| `REPO_SEO_API_KEY` | 兼容 OpenAI 的 LLM API 密钥：AI 建议 / README 草稿 / AEO 探测（可选） |
| `REPO_SEO_BASE_URL` | 自定义 LLM base URL |
| `REPO_SEO_MODEL` | 目标 LLM 模型名 |
| `REPO_SEO_PROBE_MODELS` | 多模型 AEO 探测模型列表（逗号分隔，可选） |
| `GOOGLE_CSE_API_KEY` / `GOOGLE_CSE_ID` | Google 收录核验（可选） |

说明：

- 扫描历史保存在命名卷 `repo-seo-history` 中，重建容器不丢失。
- 一键应用修改的本地工作区保存在命名卷 `repo-seo-workspaces` 中，重建容器不丢失。
- 停止并移除容器：`docker compose down`（默认保留数据卷）。
- 环境变量优先级：宿主 shell > `.env` > compose 默认值。

## 使用方法

### 基础扫描（公开仓库，无需 token）

```bash
repo-seo scan https://github.com/linhaha-ai/RepoRadar
```

### 生成 AI 建议

```bash
repo-seo scan owner/repo --ai
```

### 禁用 AI（仅规则模板模式）

```bash
repo-seo scan owner/repo --no-ai
```

### 导出结构化 JSON 报告

```bash
repo-seo scan owner/repo --json report.json
```

### 使用自定义 LLM 端点

```bash
REPO_SEO_API_KEY=sk-xxx REPO_SEO_BASE_URL=https://api.example.com/v1 REPO_SEO_MODEL=example-model \
repo-seo scan owner/repo --ai
```

### 一键优化并应用（Web UI）

打开 Web 界面扫描自己的仓库，点击 **一键优化并应用**：

1. 校验 `GITHUB_TOKEN` 对目标仓库是否有 push 权限（仅自己的仓库；否则回退为只读清单）；
2. 通过 tarball 下载仓库副本到 `REPO_SEO_WORKSPACE_DIR`（容器内无需 git），默认复用已有副本；
3. 写入 AI 生成的 README，并新建白名单内的缺失文件（`CONTRIBUTING.md`、`SECURITY.md`、`.gitignore`、`.github/*` 等）；
4. 返回 `applied / skipped / manual` 列表与 **unified diff**，在浏览器中按 `+` / `-` 着色展示。

安全边界：**只改本地副本，不 commit / 不 push**；README 会被重写，已存在的白名单文件跳过；不自动生成 LICENSE；解压阶段拒绝路径穿越与符号链接；元数据 / 仓库设置列入 `manual` 由人工修改。

API：`POST /api/optimize/apply`，请求 `{"url": "owner/repo", "refresh": false}`；`refresh=true` 强制重新下载副本。

深链直达：浏览器直接访问 `http://localhost:8000/owner/repo` 可浏览该仓库最近一次体检报告（无历史记录则自动发起体检）；体检成功后地址栏同步为 `/owner/repo`，便于分享与收藏。「一键优化」标签页会秒级回显该仓库最近一次生成的修改清单（标注生成时间，不重新调用 AI）。

## 评分模型

0–100 分分布在六个确定性维度上：

| 维度 | 满分 | 衡量内容 |
|---|---|---|
| README 内容质量 | 25 | 价值主张与定位、关键词/语义覆盖、快速开始与使用示例、结构与链接完整性、AEO 友好内容 |
| 仓库元数据 | 20 | 仓库名、描述、topics、主要语言、主页/文档链接 |
| AI 检索就绪度 | 20 | 实体与身份清晰度、功能与使用场景表达、可引用事实与示例、结构化文档、信息一致性与局限性 |
| 搜索可发现性 | 15 | 页面可访问性、索引证据、文档可爬取性、sitemap 与 canonical URL、内外部链接完整性 |
| 工程健康度与可信度 | 10 | 许可证、CI、测试、发布/版本管理、依赖与安全信息 |
| 项目活跃度 | 10 | 近期维护、Issue 处理、发布节奏、贡献活跃度 |

29 条规则中的每一条都会评估为以下三种状态之一：

- **PASS** — 规则满足，获得满分
- **FAIL** — 规则违反，扣除分数并附证据与修复建议
- **N/A · UNDETECTABLE** — 规则不适用或数据不可用；从评分分母中排除，避免隐式扣分

结果包含 **Top 3 高优先级修复** 和完整的优先级分层修复清单（P0 → P1 → P2）。

## 常见问题

**RepoRadar 的评分等于我的实际 GitHub 或 Google 排名吗？**

不等于。评分衡量的是*优化就绪度*——仓库的静态内容为被发现做好了多充分的准备——而非实时搜索排名。排名取决于动态信号（外链、star、流量），静态审计无法捕捉这些信号。

**如何扫描私有仓库？**

在运行 `repo-seo scan` 前，将 `GITHUB_TOKEN` 环境变量设置为具有 `repo` 权限的 GitHub Personal Access Token。没有它，私有仓库将返回受限数据并获得较低的可发现性评分。

**不付费给 OpenAI 也能启用 AI 建议吗？**

可以。通过 `REPO_SEO_API_KEY`、`REPO_SEO_BASE_URL` 和 `REPO_SEO_MODEL` 配置任意兼容 OpenAI 的端点（Agnes、豆包/火山方舟、DeepSeek、本地 Ollama 等）。如果这些均未设置，或 LLM 调用失败，工具会自动回退到规则模板建议。

**RepoRadar 支持任何编程语言的仓库吗？**

支持。扫描逻辑基于仓库元数据、README 结构、文件拓扑和关键词——而非针对特定语言的代码分析。语言仅作为元数据信号参与元数据与可发现性维度的评估。

**如何安装 RepoRadar 并开始扫描？**

参见上文的 [安装](#安装) 和 [使用方法](#使用方法) 章节。克隆仓库，执行 `pip install -e ".[dev]"`，然后运行 `repo-seo scan <url>`。

## 局限性

- **仅静态审计**：评分反映内容优化就绪度，而非实时搜索或排名位置。可通过 `--verify` 提供外部验证（Google 索引检查 + 多模型 AEO 探测）。
- **私有仓库天然在可发现性上受限**：即使扫描成功，GitHub 搜索和 AI 爬虫也无法索引私有内容，因此可发现性评分在设计上会更低。
- **AI 建议需要 API 密钥**：`--ai` 参数需要配置兼容 OpenAI 的密钥。没有密钥时，工具仍能产出准确的基于规则的评分和模板建议——只是没有 LLM 生成的叙述性文本。
- **一键应用仅修改本地副本**：不会 commit / push，只新建白名单文件，且需要具有目标仓库 push 权限的 `GITHUB_TOKEN`。
- **PyPI 可用性**：目前通过源码方式分发；正式的 `pip install repo-seo` 发布已在路线图中，但尚未发布。
- **外部爬取覆盖**：三层抓取器（REST API → raw → web）尽量扩大覆盖面，但某些仓库可能存在限流或受限端点，导致部分数据缺失。

## 使用场景

- **新开源项目发布**：发布前先运行 RepoRadar，发现基础的 README 和元数据缺口。
- **项目维护与重启**：诊断活跃度下降的仓库为什么可见度降低，并按优先级修复。
- **CI/CD 集成**：在 PR 检查中嵌入 `repo-seo scan --json`，为团队仓库强制执行最低可发现性标准。

---

*RepoRadar 采用 Apache-2.0 许可证。本 README 本身即使用 RepoRadar 自己的 `--ai` 优化管线生成。*
