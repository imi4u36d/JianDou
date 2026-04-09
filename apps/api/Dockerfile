# 允许在 CI 或本地镜像环境中覆盖 Python 基础镜像。
ARG PYTHON_IMAGE=docker.m.daocloud.io/library/python:3.12-slim-bookworm
FROM ${PYTHON_IMAGE}

# 减少镜像冗余，并让 pip 走配置好的镜像源。
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/

WORKDIR /app

# 复制本地可编辑安装的 Python 包，供 pip 安装。
COPY packages/backend_core /app/packages/backend_core
COPY packages/shared /app/packages/shared
COPY packages/db /app/packages/db
COPY packages/storage /app/packages/storage
COPY packages/media /app/packages/media
COPY packages/ai /app/packages/ai
COPY packages/pipeline /app/packages/pipeline
COPY apps/api /app/apps/api
COPY apps/worker /app/apps/worker

# 将 Debian 源切换到阿里云镜像，并安装媒体处理所需的 ffmpeg。
RUN if [ -f /etc/apt/sources.list.d/debian.sources ]; then \
        sed -i 's|http://deb.debian.org/debian|https://mirrors.aliyun.com/debian|g; s|http://deb.debian.org/debian-security|https://mirrors.aliyun.com/debian-security|g' /etc/apt/sources.list.d/debian.sources; \
    fi \
    && if [ -f /etc/apt/sources.list ]; then \
        sed -i 's|http://deb.debian.org/debian|https://mirrors.aliyun.com/debian|g; s|http://deb.debian.org/debian-security|https://mirrors.aliyun.com/debian-security|g' /etc/apt/sources.list; \
    fi \
    && apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# 以 editable 模式安装后端包，便于开发容器内实时生效。
RUN pip install --upgrade pip \
    && pip install -e /app/packages/shared \
    -e /app/packages/db \
    -e /app/packages/storage \
    -e /app/packages/media \
    -e /app/packages/ai \
    -e /app/packages/pipeline \
    -e /app/packages/backend_core \
    -e /app/apps/api \
    -e /app/apps/worker

WORKDIR /app/apps/api

# 默认启动命令与本地开发入口保持一致。
CMD ["uvicorn", "app.main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"]
