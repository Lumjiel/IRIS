# === 前端构建阶段 ===
FROM node:20-alpine AS frontend-build
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install --prefer-offline
COPY frontend/ ./
RUN npm run build

# === Nginx 生产镜像 ===
FROM nginx:alpine
# 复制 Nginx 配置
COPY deploy/nginx.conf /etc/nginx/conf.d/default.conf
# 复制前端构建产物
COPY --from=frontend-build /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
