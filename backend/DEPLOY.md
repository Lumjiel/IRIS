# IRIS 部署指南

## 2核2G 服务器部署

### 内存预算

| 组件 | 内存 |
|------|------|
| OS + 系统 | ~300MB |
| Python + FastAPI | ~200MB |
| ChromaDB（向量库） | ~100-200MB |
| DashScope Embeddings | ~50MB（API 调用） |
| Nginx（前端静态） | ~5MB |
| **总计（不开 reranker）** | **~650MB** |
| CrossEncoder reranker | +400MB ❌ |

> ⚠️ 2G 服务器 **不要开** `ENABLE_RERANKER`，会 OOM。

---

## Docker Compose 部署（推荐）

一键部署前端 + 后端 + Nginx 反向代理。

### 1. 上传代码到服务器

```bash
# 整个项目目录
scp -r . user@server:/opt/iris/
```

### 2. 配置环境变量

```bash
cd /opt/iris
cp backend/.env.example backend/.env
vim backend/.env  # 填入 API Key
```

### 3. 一键启动

```bash
docker compose up -d --build
```

首次构建约 3-5 分钟（拉取基础镜像 + 安装依赖 + 构建前端）。

### 4. 验证

```bash
# 查看状态
docker compose ps

# 查看日志
docker compose logs -f

# 访问 http://your-server-ip
```

### 架构

```
用户浏览器 → :80 (Nginx)
              ├── /           → 前端静态文件（Vue 构建产物）
              └── /api/*      → proxy_pass → backend:8000
```

- **前端**: Nginx 容器，多阶段构建（node 编译 → nginx 托管）
- **后端**: Python 容器，FastAPI + LangGraph
- **数据卷**: `iris-data` 挂载到 `/data`，持久化 checkpoint、素材库

### 常用操作

```bash
# 重启
docker compose restart

# 重建（代码更新后）
docker compose up -d --build

# 停止并清理
docker compose down

# 查看内存
docker stats

# 进入后端容器调试
docker compose exec backend bash
```

### 环境变量覆盖

在 `docker-compose.yml` 的 `backend.environment` 中覆盖，或在 `backend/.env` 中设置：

```yaml
environment:
  - WORKERS=2           # 多 worker（注意限流器内存共享问题）
  - LOG_LEVEL=debug     # 调试日志
  - ENABLE_RERANKER=true # ⚠️ 2G 不要开
```

---

## 无 Docker 部署

### 后端

```bash
cd /opt/iris/backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
vim .env

# 启动（systemd 管理）
sudo cp iris.service /etc/systemd/system/
sudo systemctl enable iris
sudo systemctl start iris
```

### 前端

```bash
cd /opt/iris/frontend
npm install
npm run build  # 产物在 dist/

# 将 dist/ 拷贝到 Nginx 目录
sudo cp -r dist/* /var/www/iris/
```

### systemd 服务文件

```ini
[Unit]
Description=IRIS Backend API
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/iris/backend
Environment="PATH=/opt/iris/backend/venv/bin"
ExecStart=/opt/iris/backend/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### Nginx 配置

参考 `deploy/nginx.conf`，修改 `server_name` 和路径后：

```bash
sudo cp deploy/nginx.conf /etc/nginx/sites-available/iris
sudo ln -s /etc/nginx/sites-available/iris /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

---

## 环境变量说明

| 变量 | 说明 | 必填 | 默认值 |
|------|------|------|--------|
| `OPENAI_API_KEY` | DashScope API Key | ✅ | - |
| `OPENAI_API_BASE` | API 端点 | ✅ | - |
| `DASHSCOPE_API_KEY` | Embedding API Key | ✅ | - |
| `TAVILY_API_KEY` | Tavily 搜索 Key | ✅ | - |
| `LLM_MODEL_PRIMARY` | 主模型 | ❌ | `qwen3.7-plus` |
| `LLM_MODEL_FALLBACK` | 备用模型 | ❌ | `deepseek-v4-flash` |
| `CORS_ORIGINS` | 允许的域名 | ✅（生产） | `*` |
| `ENABLE_RERANKER` | 精排模型（2G 不要开） | ❌ | `false` |
| `CREATION_DIR` | 报告保存目录 | ❌ | `/data/creation` |
| `CHECKPOINT_DB` | SQLite 路径 | ❌ | `checkpoints.db`（相对于 DATA_DIR） |
| `DATA_DIR` | 数据根目录 | ❌ | `backend/` 目录 |
| `WORKERS` | uvicorn worker 数 | ❌ | `1` |
| `LOG_LEVEL` | 日志级别 | ❌ | `info` |

## 文件结构

```
IRIS/
├── docker-compose.yml          # 一键部署编排
├── deploy/
│   └── nginx.conf              # Nginx 反向代理配置
├── backend/
│   ├── Dockerfile              # 后端容器镜像
│   ├── .env.example            # 环境变量模板
│   ├── requirements.txt        # 生产依赖
│   ├── requirements-dev.txt    # 开发/测试依赖
│   └── DEPLOY.md               # 本文档
├── frontend/
│   ├── Dockerfile              # 前端多阶段构建（node → nginx）
│   ├── package.json
│   └── vite.config.js
└── .dockerignore               # Docker 构建排除
```

## 内存监控

```bash
# Docker
docker stats iris-backend

# 裸机
ps aux | grep uvicorn
free -h
```
