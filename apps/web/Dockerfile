# 允许在 CI 或本地镜像环境中覆盖 Node 基础镜像。
ARG NODE_IMAGE=docker.m.daocloud.io/library/node:20-bookworm
FROM ${NODE_IMAGE}

WORKDIR /app/apps/web

# 先复制锁文件，便于缓存依赖安装层。
COPY apps/web/package.json /app/apps/web/package.json
COPY apps/web/package-lock.json /app/apps/web/package-lock.json

# 从公共 npm 仓库安装前端依赖。
RUN npm install --registry=https://registry.npmjs.org

# 在依赖安装完成后再复制完整前端源码。
COPY apps/web /app/apps/web

# 启动 Vite 开发服务，并暴露给 Docker 网络访问。
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"]
