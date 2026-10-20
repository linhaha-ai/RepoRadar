# RepoSEO Analyzer

GitHub 仓库可发现性体检工具：输入仓库 URL，输出可发现性评分与逐条优化建议（评分模型 2.0）。

**设计原则**：评价的不是"仓库做得是否规范"，而是"是否容易被发现、是否容易被理解、是否有机会被搜索和 AI 系统正确引用"。

## 快速开始

```bash
pip install -e ".[dev]"

# 公开仓库
repo-seo scan https://github.com/owner/repo

# 私有仓库（需要 Token）
repo-seo scan https://github.com/owner/private-repo --token ghp_xxx
# 或通过环境变量
$env:GITHUB_TOKEN = "ghp_xxx"
repo-seo scan owner/repo
```

## 当前状态（M1~M3 ✅）

- [x] URL 解析（https / git@ / owner-repo）
- [x] GitHub API 抓取（Token 支持、限流诊断、私有仓库）
- [x] README 抓取降级链：API → raw 兜底（带预算）→ 网页（公开仓库）
- [x] RepoSnapshot 数据模型（元数据 / README / 工程信号 / 活跃度）
- [x] CLI 端到端实测（私有仓库 + Token）
- [x] 规则引擎 29 条（6 维度：R/M/A/D/H/AC）+ 证据生成
- [x] 评分 2.0：加权聚合、三状态（N/A/UNKNOWN 剔除分母）、P0/P1/P2、Top3 修复问题
- [x] 终端评分报告（RepoRadar 实测 16.5/100）
- [x] AI 优化建议模块（M3.5）：OpenAI 兼容 LLM 客户端 + Prompt + schema 校验 + 模板降级；无 Key 时自动用规则模板
- [x] README 草稿生成（--readme-draft）
- [x] Markdown / HTML 报告导出（--report-md / --report-html，HTML 单文件自包含）
- [x] 规则可配置化（--config：启用/分值/优先级/阈值参数，维度满分动态计算）
- [x] 外部验证层 V2（--verify：Google 收录核验 + 多模型 AEO 实测）
- [x] 趋势监控 V2.2（monitor 定时体检 + trend 历史曲线，SVG/终端/MD/HTML）
- [x] Web 前端（FastAPI + 单页：输入 URL → 可视化报告）
- [ ] 更多 AEO 服务商接入

## AI 优化建议（M3.5）

```bash
# OpenAI 兼容端点（OpenAI / 火山方舟·豆包 / DeepSeek / agnes / Ollama 等）
$env:REPO_SEO_API_KEY = "sk-..."
$env:REPO_SEO_BASE_URL = "https://apihub.agnes-ai.com/v1"          # agnes 示例（需含版本路径 /v1）
$env:REPO_SEO_BASE_URL = "https://ark.cn-beijing.volces.com/api/v3" # 火山方舟示例
$env:REPO_SEO_MODEL = "agnes-2.5-flash"                             # 模型名/推理接入点
repo-seo scan owner/repo

# 或命令行指定
repo-seo scan owner/repo --model agnes-2.5-flash --base-url https://apihub.agnes-ai.com/v1
repo-seo scan owner/repo --no-ai      # 强制仅规则模板
```

- 评分由确定性规则引擎决定，AI 只生成建议文本，失败自动降级（DESIGN.md §10）；

## README 草稿生成（--readme-draft）

扫描后直接用 AI 建议生成英文 README 草稿（事实来自仓库快照，禁止模型编造命令/包名/分数）：

```bash
$env:REPO_SEO_API_KEY = "sk-..."            # 必须配置 LLM Key
repo-seo scan owner/repo --readme-draft                    # 输出 ./README.draft.md
repo-seo scan owner/repo --readme-draft --readme-out README.md   # 指定路径
```

- 落实 R01-R05 / A01-A05 / D05 共 11 条 README 相关建议；
- 无 LLM Key 时明确报错（不静默降级）；
- 对 RepoRadar 自身扫描时会注入真实 CLI/安装/环境变量事实（自举验证）。

## 报告导出（--report-md / --report-html）

```bash
repo-seo scan owner/repo --report-md report.md --report-html report.html
```

- Markdown：总分 / 维度得分表 / Top3 / AI 建议 / 证据清单 / 元信息，可直接贴 GitHub Issue 或飞书文档；
- HTML：单文件自包含（内联 CSS、零外部依赖），浏览器直接打开、可打印，含维度进度条与优先级标签；
- 与 `--json` 可同时导出，三种格式共享同一份评分数据。

## 规则可配置化（--config）

```bash
repo-seo rules                          # 列出 29 条规则与可配参数
repo-seo rules --export-config rules.toml   # 导出默认配置模板
repo-seo scan owner/repo --config rules.toml
```

```toml
[rules.R01]                 # 启用/禁用 + 分值 + 优先级
enabled = true
score = 6.0
priority = "P0"
params = { min_chars = 80 } # 阈值参数（R01 首段最小字符）

[rules.R04]                 # 禁用规则（不计分）
enabled = false
```

- 可配阈值：R01 min_chars / R02 min_hits·max_hits / M02 max_desc_chars / M03 min_topics·max_topics / AC01 活跃度窗口；
- 自定义配置下维度满分按启用规则分值**动态计算**（默认 = 权重），报告会标注「自定义配置」；
- 未知规则 / 非法参数启动即报错（退出码 2），不静默忽略；默认配置与基线评分完全一致。

## 外部验证层（--verify · V2）

```bash
$env:GOOGLE_CSE_API_KEY = "..."        # Google Custom Search JSON API Key
$env:GOOGLE_CSE_ID = "..."             # Custom Search Engine ID
$env:REPO_SEO_PROBE_MODELS = "agnes-2.5-flash,other-model"   # 可选：多模型探测
repo-seo scan owner/repo --verify
```

- **Google 收录检查**：`site:github.com/owner/repo` 查询核验；未配置凭据 → UNKNOWN（不误判"未收录"）；
- **多模型 AEO 实测**：对配置的模型问「是否了解该仓库」，输出 提及/未提及 + 回答摘录；
- 外部验证是「Search Visibility Evidence」，与静态评分分开呈现，**不混入总分**；
- 三状态：已验证 / 未发现证据 / 无法检测，报告如实标注。

## 趋势监控（V2.2）

```bash
repo-seo monitor owner/repo          # 定时体检：扫描 → 评分 → 追加历史 → 输出趋势
repo-seo monitor owner/repo --html trend.html
repo-seo trend owner/repo --html trend.html   # 只读历史出曲线（无网络）
```

- 历史存储：`.repo-seo-history/{owner}__{repo}.json`（时间戳升序，同刻去重，损坏自愈）；
- 趋势输出：终端 / Markdown / HTML（零依赖 SVG 折线：总分 + 6 维度，Y 轴 0~100）；
- **定时能力**：工具是无守护进程 CLI，「定时体检」由系统 cron / CI / 豆包定时任务周期调用
  `repo-seo monitor <url>` 实现——每次调用只做一次体检并追加历史，幂等可重入。
  示例（每 7 天一次）：
  ```bash
  # cron：0 9 * * 1  cd /path/repo-seo && repo-seo monitor linhaha-ai/RepoRadar --html trend.html
  ```

## Web 前端

```bash
pip install -e ".[web]"
$env:GITHUB_TOKEN = "ghp_xxx"        # 可选：扫描私有仓库
uvicorn repo_seo.web.app:app --port 8000 --host 127.0.0.1
# 浏览器打开 http://127.0.0.1:8000
```

- 单页应用（零外部依赖，纯 CSS/SVG）：输入仓库 URL → 总分 + 六维度条形图 + Top3 修复 + 证据表 + AI 建议 + 外部验证 + 历史趋势；
- API：`POST /api/scan`（`{url, ai, verify}`）、`GET /`；Token / API Key 一律从环境变量读取，不经过前端。

## Docker 部署

```bash
# 1.（可选）配置密钥：复制 .env.example 为 .env 并填写
# 2. 构建并启动（首次构建需拉取 python:3.11-slim 镜像）
docker compose up -d --build
# 3. 打开 http://localhost:8000
# 其他：docker compose logs -f / docker compose down
```

- `Dockerfile`：python:3.11-slim，非 root 用户运行，HEALTHCHECK 健康检查；
- `docker-compose.yml`：端口 8000，环境变量从宿主 / `.env` 注入（GITHUB_TOKEN / AGNES / Google CSE），趋势历史存命名卷 `repo-seo-history`（重建容器不丢失）；
- `.env.example`：密钥模板（**不要提交真实密钥到 git**）。

## 开发

```bash
pytest                      # 运行测试
python -m repo_seo.cli parse owner/repo   # 调试 URL 解析
```

## 路线图

M1 抓取层 → M2 规则库（6 维度 × 检查项）→ M3 评分 2.0 + 终端报告 → M3.5 AI 优化建议（LLM 生成 + 模板兜底）→ M4 端到端验证 → M5 Markdown/HTML 报告导出 → V2 收录检查 / 多模型 AEO 实测。

详见项目根目录 `PROJECT_OUTLINE.md` 与 `docs/DESIGN.md`（§10 AI 优化建议模块）。
