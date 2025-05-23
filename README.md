# translate


# 1.镜像的方式

## 进入项目目录
cd translate-api

## 构建镜像
docker build -t translate-api .

## 运行容器，映射端口到宿主机 9005
docker run -d -p 9005:5050 --name translate-web-api translate-api

# 2.docker-compose.yml 和 Dockerfile 方式

#  目录结构
```
project-root/
├── docker-compose.yml         👈 在这里运行 docker-compose
└── translate-api/             👈 Dockerfile 和源码都放在这里
    ├── Dockerfile
    ├── app.py
    ├── requirements.txt
```


# docker-compose.yml

````
version: "3.9"
services:
  translate:
    build:
      context: ./translate-api         # 构建上下文：包含 Dockerfile 和源码
      dockerfile: Dockerfile           # Dockerfile 就在这个目录下
    container_name: translate-api
    ports:
      - "8887:5050"
    volumes:
      - ./translate-api/models:/app/models  # 如果你有持久化模型的需要
    restart: unless-stopped
    
```
    
# 运行
    
`docker-compose up -d --build`
