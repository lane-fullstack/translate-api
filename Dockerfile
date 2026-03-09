FROM python:3.10-slim

# 设置 UTF-8 编码环境
ENV LANG=C.UTF-8 LC_ALL=C.UTF-8
ENV ARGOS_PACKAGES_DIR=/app/models
# 安装系统依赖
RUN apt-get update && apt-get install -y \
    curl \
    git \
    build-essential \
    python3-dev \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --upgrade pip setuptools wheel \
    && rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /app

# 拷贝文件
COPY . .

# 安装依赖
RUN pip install --no-cache-dir -r requirements.txt

expose 5050

# 启动时自动下载语言包
CMD ["python", "app.py"]
