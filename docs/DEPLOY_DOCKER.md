# Docker 服务器部署

这份部署方案面向服务器环境，和仓库根目录现有的 `docker-compose.yml` 开发编排分开使用。

## 部署结构

- `mysql`：MySQL 8.4，负责持久化业务数据
- `api`：Spring Boot 3 后端，生产模式下打包成 jar 运行
- `web`：Vue 构建后的静态站点，由 Nginx 提供页面并反代 `/api/v2`、`/storage`

访问入口只有 `web` 容器暴露到宿主机。浏览器始终走同域访问，能避开开发模式下的 Vite 代理和跨域细节。

## 前置条件

- 服务器已安装 Docker
- 服务器已安装 Docker Compose Plugin，命令为 `docker compose`
- 服务器能访问外网拉取 Maven、npm 和 Docker 镜像依赖

## 首次部署

1. 克隆仓库并进入项目目录。
2. 复制环境变量模板：

```bash
cp .env.prod.example .env.prod
```

3. 修改 `.env.prod`，至少设置这些值：

- `MYSQL_ROOT_PASSWORD`
- `MYSQL_PASSWORD`
- `JIANDOU_AUTH_BOOTSTRAP_INITIAL_ADMIN_PASSWORD`
- `JIANDOU_WEB_ORIGIN`

当前生产版前端 Nginx 已内置域名规则：

- `jiandou.org`：官网首页和工作台入口
- `www.jiandou.org`：301 跳转到 `jiandou.org`

如果你后续更换域名，需要同步修改 `apps/web/nginx.prod.conf`。

4. 检查 `config/model/providers.secrets.yml`，把示例 Key 换成你自己的可用配置。
5. 启动生产编排：

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d --build
```

6. 查看状态：

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml ps
```

7. 查看日志：

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml logs -f
```

## 目录与持久化

- `./config:/app/config`：模型、提示词、运行配置
- `./storage:/app/storage`：上传文件、生成产物、运行临时文件
- `mysql_data`：MySQL 数据卷

如果你要迁移服务器，至少需要保留 `config`、`storage` 和 MySQL 数据卷。

## 镜像拉取说明

`.env.prod.example` 里已经给生产构建预置了基础镜像地址，默认使用 Daocloud Mirror：

- `JIANDOU_MAVEN_IMAGE`
- `JIANDOU_JAVA_IMAGE`
- `JIANDOU_NODE_IMAGE`
- `JIANDOU_NGINX_IMAGE`

如果你的服务器可以稳定访问 Docker Hub，也可以把这些值改回官方镜像名。

## 更新版本

拉取新代码后执行：

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d --build
```

## 停止服务

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml down
```

如果要连同数据库卷一起删除：

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml down -v
```

## HTTPS 建议

当前编排默认暴露宿主机 `80` 端口。如果你要正式对外提供服务，建议在服务器上再加一层 HTTPS 入口：

- 用宿主机 Nginx/Caddy 做 TLS 终止，然后反代到 `127.0.0.1:${JIANDOU_WEB_PORT}`
- 或者直接把 `web` 容器放到现有网关后面

启用 HTTPS 后，把 `.env.prod` 中的 `JIANDOU_WEB_ORIGIN` 改成 `https://你的域名`，并把 `JIANDOU_COOKIE_SECURE=true`。
