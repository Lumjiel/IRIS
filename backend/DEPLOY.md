# IRIS 部署指南

## 2核2G 服务器部署

### 内存预算

| 组件 | 内存 |
|------|------|
| OS + 系统 | ~300MB |
| Python + FastAPI | ~200MB |
| ChromaDB（向量库） | ~100-200MB |
| DashScope Embeddings | ~50MB（API 调用） |
| **总计（不开 reranker）** | **~650MB** |
| CrossEncoder reranker | +400MB ❌ |

> ⚠️ 2G 服务器 **不要开** `ENABLE_RERANKER`，会 OOM。

### 快速部署（Docker）

```bash
# 1. 上传代码到服务器
scp -r backend/ user@server:/opt/iris/

# 2. 在服务器上
cd /opt/iris
cp .env.example .env
vim .env  # 填入 API Key

# 3. 构建并运行
docker build -t iris-backend .
docker run -d \
  --name iris \
  --restart unless-stopped \
  -p 8000:8000 \
  --memory=1g \
  --cpus=2 \
  -v $(pwd)/data:/app/app/rag \
  -v $(pwd)/.env:/app/.env \
  iris-backend
```

### 快速部署（无 Docker）

```bash
# 1. 安装依赖
cd /opt/iris
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. 配置环境变量
cp .env.example .env
vim .env

# 3. 启动（systemd 管理）
sudo cp iris.service /etc/systemd/system/
sudo systemctl enable iris
sudo systemctl start iris
```

### systemd 服务文件

```ini
[Unit]
Description=IRIS Backend API
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/iris
Environment="PATH=/opt/iris/venv/bin"
ExecStart=/opt/iris/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### Nginx 反向代理

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # 前端静态文件
    location / {
        root /opt/iris-frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    # 后端 API
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;

        # SSE 流式响应
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 300s;
    }
}
```

### 环境变量说明

| 变量 | 说明 | 必填 | 默认值 |
|------|------|------|--------|
| `OPENAI_API_KEY` | DashScope API Key | ✅ | - |
| `OPENAI_API_BASE` | API 端点 | ✅ | - |
| `TAVILY_API_KEY` | Tavily 搜索 Key | ✅ | - |
| `DASHSCOPE_API_KEY` | Embedding API Key | ✅ | - |
| `CORS_ORIGINS` | 允许的域名 | ✅（生产） | `*` |
| `ENABLE_RERANKER` | 精排模型 | ❌ | `false` |
| `WORKERS` | uvicorn worker 数 | ❌ | `1` |
| `LOG_LEVEL` | 日志级别 | ❌ | `info` |

### 内存监控

```bash
# 查看容器内存
docker stats iris

# 查看进程内存
ps aux | grep uvicorn
```
