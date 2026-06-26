# syntax=docker/dockerfile:1.7

FROM node:20-slim AS builder

WORKDIR /app

COPY package.json package-lock.json ./
COPY frontends/web/package.json frontends/web/package.json
COPY packages/api/package.json packages/api/package.json
COPY packages/domain/package.json packages/domain/package.json
COPY packages/ui/package.json packages/ui/package.json

RUN --mount=type=cache,target=/root/.npm \
    npm ci

COPY packages/ packages/
COPY frontends/web/ frontends/web/
RUN npm --workspace @jiandou/web run build

FROM nginx:1.27-alpine

COPY frontends/web/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /app/frontends/web/dist/ /usr/share/nginx/html/

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD wget -q -O /dev/null http://127.0.0.1/ || exit 1
