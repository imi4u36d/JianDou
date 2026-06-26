FROM node:20-slim AS builder

WORKDIR /app

COPY package.json package-lock.json ./
COPY packages/ packages/
COPY frontends/web/ frontends/web/

RUN npm ci
RUN npm --workspace @jiandou/web run build

FROM nginx:1.27-alpine

COPY frontends/web/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /app/frontends/web/dist/ /usr/share/nginx/html/

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD wget -q -O /dev/null http://127.0.0.1/ || exit 1
