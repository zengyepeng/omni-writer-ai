# Omni-Writer AI - Docker 部署
FROM python:3.11-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制代码
COPY . .

# 数据目录（挂载卷用）
VOLUME ["/app/data"]

# Web 控制台端口
EXPOSE 7860

# 默认启动 Web UI
CMD ["python", "web_ui.py"]
