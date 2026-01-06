# 基础镜像
FROM python:3.9-slim
# 设置工作目录
WORKDIR /app
# 复制依赖文件（如果有）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# 复制应用代码
COPY app.py .
# 暴露端口
EXPOSE 80
# 启动命令
CMD ["python", "app.py"]