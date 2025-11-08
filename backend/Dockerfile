# 1. 使用官方 Python 3.11 镜像 (非 slim 版，更稳定)
FROM python:3.11

# 2. 设置工作目录
WORKDIR /app

# 3. [重要] 升级 pip, setuptools, wheel (这是最佳实践)
RUN pip install --upgrade pip setuptools wheel

# 4. 复制我们新的、干净的 requirements.txt
COPY requirements.txt .

# 5. 安装依赖 (现在它会正常工作)
RUN pip install --no-cache-dir -r requirements.txt

# 6. 复制后端的所有代码
COPY . .

# 7. 自动运行数据库迁移
RUN flask db upgrade

# 8. 暴露 Gunicorn 运行的端口
EXPOSE 5001

# 9. 定义容器启动时运行的命令
CMD ["gunicorn", "--workers", "4", "--bind", "0.0.0.0:5001", "app:app"]