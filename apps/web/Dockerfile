# 允许在 CI 或本地镜像环境中覆盖 Node 基础镜像。
ARG NODE_IMAGE=node:20-bookworm
FROM ${NODE_IMAGE}

WORKDIR /app

# 先复制根级和 workspace 包描述文件，便于缓存依赖安装层。
COPY package.json package-lock.json ./
COPY apps/web/.npmrc apps/web/.npmrc
COPY packages/api-client/package.json packages/api-client/package.json
COPY packages/frontend-domain/package.json packages/frontend-domain/package.json
COPY packages/frontend-ui/package.json packages/frontend-ui/package.json
COPY apps/web/package.json apps/web/package.json

# 从公共 npm 仓库安装前端依赖（仅 web workspace）。
RUN npm ci --registry=https://registry.npmjs.org -w apps/web

# 在依赖安装完成后再复制完整前端源码。
COPY apps/web apps/web
COPY packages packages

WORKDIR /app/apps/web

# 启动 Vite 开发服务，并暴露给 Docker 网络访问。
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"]
