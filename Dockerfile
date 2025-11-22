# 使用多阶段构建减小镜像体积
FROM python:3.12-slim-bookworm AS builder

# 安装 uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# 安装系统依赖（如果需要编译某些库）
# RUN apt-get update && apt-get install -y --no-install-recommends build-essential && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY pyproject.toml uv.lock ./

# 安装依赖
# 使用 --no-dev 仅安装生产依赖
# 使用 --no-install-project 仅安装依赖包，不安装当前项目
RUN uv sync --frozen --no-dev --no-install-project

# ==========================================
# 运行时镜像
FROM python:3.12-slim-bookworm

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

# 安装运行时系统依赖 (如 curl 用于健康检查)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 从构建阶段复制虚拟环境
COPY --from=builder /app/.venv /app/.venv

# 复制源代码
COPY app /app/app
COPY alembic /app/alembic
COPY alembic.ini /app/alembic.ini
# COPY scripts /app/scripts
# COPY Makefile /app/Makefile

# 创建非 root 用户运行应用
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 启动命令
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
