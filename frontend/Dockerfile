# ============================================================
# 面向能源可信数据空间 - 前端服务 Dockerfile
# 多阶段构建：Node.js 构建阶段 + Nginx 运行阶段
# ============================================================

# 构建阶段
FROM node:20-alpine AS builder

# 设置工作目录
WORKDIR /app

# 安装依赖
COPY package*.json ./
RUN npm ci

# 复制源代码并构建
COPY . .
RUN npm run build

# 运行阶段
FROM nginx:alpine AS production

# 复制 Nginx 配置
COPY deploy/nginx/nginx.conf /etc/nginx/nginx.conf
COPY deploy/nginx/default.conf /etc/nginx/conf.d/default.conf

# 复制构建产物
COPY --from=builder /app/dist /usr/share/nginx/html

# 创建健康检查文件
RUN echo '{"status":"healthy"}' > /usr/share/nginx/html/health.json

# 暴露端口
EXPOSE 80

# 启动 Nginx
CMD ["nginx", "-g", "daemon off;"]
