FROM python:3.11-slim

WORKDIR /app

# 系统依赖（chromadb 需要 build-essential）
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Python 依赖（利用 Docker 层缓存，requirements 不变则不重装）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 应用代码
COPY . .

# 数据目录（/data 挂载卷，容器内统一路径）
RUN mkdir -p /data/iris/creation

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/')" || exit 1

# 生产启动：默认单 worker，可通过 WORKERS 环境变量调整
ENV WORKERS=1
CMD uvicorn main:app --host 0.0.0.0 --port 8000 --workers $WORKERS --log-level info
