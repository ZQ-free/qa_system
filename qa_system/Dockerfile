# ============================================================
# Dockerfile — Python 后端
#
# 使用多阶段构建，减小镜像体积
# 构建: docker build -t qa-backend:latest -f Dockerfile .
# 运行: docker run -p 8000:8000 --env-file .env qa-backend:latest
# ============================================================

# ── 第一阶段：依赖安装 ────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /app

# 安装编译依赖（aiomysql 需要）
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libmariadb-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# 复制 requirements 并安装
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt


# ── 第二阶段：运行镜像 ──────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# 安装运行时依赖（不需要编译的）
RUN apt-get update && apt-get install -y --no-install-recommends \
    libmariadb3 \
    && rm -rf /var/lib/apt/lists/*

# 从 builder 复制已安装的包
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# 复制应用代码
COPY . .

# 环境变量（运行时可覆盖）
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# 启动命令
# 默认使用 uvicorn，可通过 CMD 覆盖
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
