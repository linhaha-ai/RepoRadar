# RepoRadar Web 前端 · Docker 镜像
FROM python:3.11-slim

LABEL org.opencontainers.image.title="RepoRadar" \
      org.opencontainers.image.description="GitHub 仓库可发现性体检：原生搜索 + AI 检索曝光（AEO）" \
      org.opencontainers.image.version="2.2"

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# 先复制构建清单（hatchling 需要 README.md），利用层缓存
COPY pyproject.toml README.md ./
COPY src ./src

# 安装包与 Web 依赖（非 editable，镜像内不可变）
RUN pip install --no-cache-dir ".[web]" \
    && rm -rf /root/.cache/pip

# 非 root 运行
RUN useradd -m -u 1000 reporadar \
    && mkdir -p /app/.repo-seo-history \
    && chown -R reporadar:reporadar /app
USER reporadar

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/', timeout=3)" || exit 1

# Token / API Key 一律从环境变量注入（见 docker-compose.yml / .env）
CMD ["uvicorn", "repo_seo.web.app:app", "--host", "0.0.0.0", "--port", "8000"]
