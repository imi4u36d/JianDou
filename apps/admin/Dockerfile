ARG NODE_IMAGE=node:20-bookworm
FROM ${NODE_IMAGE}

WORKDIR /app

# 先复制根级和 workspace 包描述文件，便于缓存依赖安装层。
COPY package.json package-lock.json ./
COPY apps/admin/.npmrc apps/admin/.npmrc
COPY packages/api-client/package.json packages/api-client/package.json
COPY packages/frontend-domain/package.json packages/frontend-domain/package.json
COPY packages/frontend-ui/package.json packages/frontend-ui/package.json
COPY apps/admin/package.json apps/admin/package.json

# 从公共 npm 仓库安装前端依赖（仅 admin workspace）。
RUN npm ci --registry=https://registry.npmjs.org -w apps/admin

# 在依赖安装完成后再复制完整前端源码。
COPY apps/admin apps/admin
COPY packages packages

WORKDIR /app/apps/admin

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5174"]
