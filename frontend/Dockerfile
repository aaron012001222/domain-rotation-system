# --- 阶段 1: 构建 (Builder) ---
# 使用 Node.js 20 镜像
FROM node:20 AS builder

WORKDIR /app

# 复制 package.json 并安装依赖
COPY package*.json ./
RUN npm install

# 复制所有代码并运行构建
COPY . .
RUN npm run build

# --- 阶段 2: 运行 (Server) ---
# 使用轻量级的 Nginx 镜像
FROM nginx:alpine

# 从 "builder" 阶段复制构建好的静态文件
COPY --from=builder /app/dist /usr/share/nginx/html

# 移除 Nginx 的默认配置
RUN rm /etc/nginx/conf.d/default.conf

# 复制我们自定义的 Nginx 配置文件
# (我们将在下一步创建这个文件)
COPY nginx.conf /etc/nginx/conf.d/

COPY .htpasswd /etc/nginx/.htpasswd

# 暴露 Nginx 的 80 端口
EXPOSE 80

# 启动 Nginx
CMD ["nginx", "-g", "daemon off;"]