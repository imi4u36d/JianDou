<p align="center">
  <a href="README.md">English</a> | <strong>简体中文</strong> | <a href="README_ja-JP.md">日本語</a>
</p>

<p align="center">
  <img src="static/web/brand/logo.svg" alt="JianDou Logo" width="360" />
</p>

<h1 align="center">JianDou（煎豆）</h1>

<p align="center">
  开源文本转视频工作站，基于可配置的多模型流水线。
</p>

<p align="center">
  <a href="https://github.com/imi4u36d/JianDou/blob/main/License"><img src="https://img.shields.io/badge/license-Apache--2.0-blue.svg" alt="License" /></a>
  <a href="https://github.com/imi4u36d/JianDou/releases"><img src="https://img.shields.io/badge/release-0.1.0-orange.svg" alt="Release" /></a>
  <a href="https://github.com/imi4u36d/JianDou"><img src="https://img.shields.io/badge/python-3.12%2B-green.svg" alt="Python" /></a>
  <a href="https://github.com/imi4u36d/JianDou"><img src="https://img.shields.io/badge/node-20%2B-brightgreen.svg" alt="Node" /></a>
</p>

---

上传小说章节、粘贴正文或输入提示词 — JianDou 通过一条可配置的 AI 模型链路（文本、视觉、关键帧、视频）将文字变成视频。每个阶段均可独立选择厂商和模型版本，完全掌控生成流水线。

## 项目截图

| 图片生成工作台 | 任务列表与轮询视图 | 管理后台概览 |
|---|---|---|
| ![煎豆图片生成工作台](docs/screenshots/jiandou-home.png) | ![煎豆任务列表](docs/screenshots/jiandou-tasks.png) | ![煎豆管理后台概览](docs/screenshots/jiandou-admin.png) |

## 核心特性

**灵活输入**
- 上传 `.txt` 文件或直接粘贴正文，自动提取内容用于提示词生成。
- 支持自定义提示词，完全自由控制生成方向。
- 可附加参考图作为关键帧的首帧或尾帧。

**多模型流水线**
- 四个独立可配阶段：文本模型（脚本/分镜）→ 视觉模型（参考图理解）→ 关键帧模型（首尾帧生成）→ 视频模型（视频合成）。
- 文本和图片生成统一使用 OpenAI 官方 GPT 模型；视频生成保留原有视频厂商。
- 输出参数（画幅、清晰度、时长、数量、Seed）根据所选模型能力自动过滤，避免无效配置。

**任务管理**
- 实时进度追踪，包含阶段状态、耗时统计和视频预览。
- 完整任务生命周期：创建、筛选、详情查看、重试、暂停、继续、终止、删除、评分。
- Seed 管理：自动汇总高评分可用 Seed，一键回填提升出片稳定性。

**管理后台**
- 独立管理门户，与用户前台分离。
- 基于角色的访问控制（管理员/用户），支持邀请码注册。
- 适合内容生产团队和运维分层协作。

**安全与部署**
- 认证接口限流、来源校验、API Key 加密存储。
- Docker Compose 部署，包含独立前端网关、后端 app、MySQL 8.0、Redis 7、自动迁移、初始化 seed 和健康检查。
- 通过环境变量和 YAML 文件进行全面配置。

## 架构

```
文本输入 --> 文本模型（脚本/分镜生成）
              --> 视觉模型（参考图理解）
                      --> 关键帧模型（首尾帧生成）
                              --> 视频模型（视频合成）
                                      --> 预览 / 下载 / 评分
```

每个流水线阶段均可独立配置厂商和模型版本。

## 快速开始

### 环境要求

- **Python** 3.12+
- **Node.js** 20+
- **npm**（随 Node.js 安装）
- **[uv](https://docs.astral.sh/uv/)**（Python 包管理器）

### 方式一：Docker（推荐）

```bash
# 1. 准备环境
cp .env.docker.example .env.docker

# 2. 构建并启动 frontend + backend + MySQL + Redis
docker compose up --build
```

Docker Compose 会启动：
- `frontend`：访问 http://localhost:8100，负责 Vue SPA 静态站点和 API/storage 反向代理
- `app`：仅在 Compose 内部网络通过 `app:8000` 提供后端服务
- `mysql:8.0`：数据库名 `jiandou`
- `redis:7-alpine`：用于共享限流和短 TTL API 缓存

app 容器启动时会自动执行 Alembic 迁移和 seed 初始化。设置 `JIANDOU_AUTO_MIGRATE=false` 可跳过自动迁移和 seed。

按服务重建：

```bash
docker compose up -d --build frontend  # 仅前端改动
docker compose up -d --build app       # 后端/API 改动
```

### 方式二：本地开发

运行一键启动：

```bash
./scripts/start.sh
```

该脚本会自动安装依赖、构建前端、初始化数据库并启动服务。启动后访问：

如需前后端分离开发（推荐），分别在两个终端运行：

```bash
# 终端 1：后端（热重载）
./scripts/dev-backend.sh

# 终端 2：前端（Vite HMR，http://localhost:5173）
./scripts/dev-frontend.sh
```

- **用户前台**：http://127.0.0.1:8100
- **管理后台**：http://127.0.0.1:8100/admin

使用模型功能前，请编辑 `config/model/providers.secrets.yml` 填入 API Key。

### 健康检查

- **存活检查**：`GET /api/v3/health`
- **就绪检查**：`GET /api/v3/ready`（验证数据库和存储可用性）

## 模型配置

模型配置集中在 `config/model/` 目录：

```
config/model/
├── models.yml                    # 可选模型定义
├── providers/                    # 厂商基础配置（base_url 等）
│   ├── volcengine.yml
│   ├── agnes.yml
│   └── openai.yml
├── providers.secrets.example.yml # API Key 模板（提交到仓库）
└── providers.secrets.yml         # 你的 API Key（本地文件，不提交）
```

支持的模型厂商：
- **OpenAI** — GPT 文本模型与 GPT Image，用于脚本/分镜和关键帧生成
- **原有视频厂商** — Seedance/Agnes 视频生成保持可用

## 配置说明

所有运行时设置通过环境变量控制。完整参考见 [docs/configuration.md](docs/configuration.md)。

关键变量：

| 变量 | 说明 | 默认值 |
|---|---|---|
| `JIANDOU_SERVER_PORT` | 后端监听端口 | `8100` |
| `JIANDOU_DATABASE_URL` | 数据库连接字符串 | `sqlite+aiosqlite:///./data/jiandou.db` |
| `JIANDOU_REDIS_URL` | Docker/生产环境 Redis 连接字符串 | — |
| `JIANDOU_CACHE_BACKEND` | API 缓存后端：`memory` 或 `redis` | `memory` |
| `JIANDOU_RATE_LIMIT_BACKEND` | 认证限流后端：`memory` 或 `redis` | `memory` |
| `JIANDOU_SECRET_KEY` | JWT 签名密钥 | （必须设置） |
| `JIANDOU_WEB_ORIGIN` | 前端来源（CORS） | `http://127.0.0.1:8100` |
| `JIANDOU_TRUSTED_ORIGINS` | 额外可信来源（逗号分隔） | — |
| `JIANDOU_COOKIE_SECURE` | 启用安全 Cookie + HSTS | `false` |
| `JIANDOU_WORKER_CONCURRENCY` | 异步工作线程数（最多 5） | `5` |
| `JIANDOU_DEFAULT_ASPECT_RATIO` | 默认视频画幅 | `16:9` |
| `JIANDOU_DEFAULT_DURATION_SECONDS` | 默认视频时长 | `8` |

认证接口内置限流。可通过 `JIANDOU_AUTH_LOGIN_RATE_LIMIT`、`JIANDOU_AUTH_INVITE_ACTIVATION_RATE_LIMIT` 和 `JIANDOU_AUTH_RATE_LIMIT_WINDOW_SECONDS` 调整。

## 开发指南

### 前端

前端使用 **Vue 3 + TypeScript + Element Plus + Tailwind CSS**，Vite 作为开发服务器并自动代理 API 请求。

```bash
# 一键启动前后端开发服务器
npm run dev:backend   # 后端热重载（端口 8100）
npm run dev:frontend  # 前端 Vite HMR（端口 5173）

# 类型检查
npm run web:typecheck

# 代码检查与格式化
npm run web:lint
npm run web:format

# 单元测试
npm run web:test

# 测试覆盖率
npx vitest run --coverage
```

详细架构见 [docs/frontend-architecture.md](docs/frontend-architecture.md)。

### 后端

后端使用 **FastAPI + SQLAlchemy + Alembic**。本地默认仍使用 SQLite + aiosqlite；Docker 和生产部署支持 MySQL + asyncmy。

```bash
# 代码检查（ruff）
uv run ruff check backend/

# 运行全部测试
uv run pytest

# 按分类运行
uv run pytest -m unit      # 快速单元测试（64 个）
uv run pytest -m api       # API 端点测试（90 个）
uv run pytest -m domain    # 领域层测试（33 个）
uv run pytest -m "not slow" # 跳过慢速测试

# 导出 OpenAPI 模式
uv run jiandou openapi --output docs/openapi.json
```

### 验证

```bash
# 完整测试套件（后端 lint + 测试 + 前端类型检查）
npm test

# 验证迁移在空白临时数据库上可用
TMP_DB=$(mktemp -t jiandou.XXXXXX.db) && \
  JIANDOU_DATABASE_URL="sqlite+aiosqlite:///$TMP_DB" uv run alembic upgrade head && \
  rm -f "$TMP_DB"

# 包类型检查
npm run packages:typecheck
npm run web:typecheck

# 发布预检（清理生成物）
npm run release:check
```

## 文档

| 文档 | 说明 |
|---|---|
| [配置参考](docs/configuration.md) | 完整环境变量说明 |
| [后端架构](docs/backend-architecture.md) | 模块职责和改动边界 |
| [前端架构](docs/frontend-architecture.md) | Monorepo 布局和组件规范 |
| [数据库设计](docs/database-design.md) | Schema 约束和迁移规则 |
| [发布流程](docs/release-process.md) | 版本管理和发布工作流 |
| [更新日志](CHANGELOG.md) | 项目更新日志 |
| [API 参考](docs/openapi.json) | OpenAPI 3.1 规范（自动生成） |

## 社区与支持

- **QQ 交流群**：`1090387362`
- [报告 Bug / 功能建议](https://github.com/imi4u36d/JianDou/issues)
- 安全问题请见 [SECURITY.md](SECURITY.md)
- 使用问题和贡献指南见 [SUPPORT.md](SUPPORT.md) 和 [CONTRIBUTING.md](CONTRIBUTING.md)

## Star 历史

<a href="https://www.star-history.com/?repos=imi4u36d%2FJianDou&type=date&legend=top-left">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/chart?repos=imi4u36d/JianDou&type=date&theme=dark&legend=top-left" />
    <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/chart?repos=imi4u36d/JianDou&type=date&legend=top-left" />
    <img alt="Star History Chart" src="https://api.star-history.com/chart?repos=imi4u36d/JianDou&type=date&legend=top-left" />
  </picture>
</a>

## 许可证

本项目基于 [Apache License 2.0](./License) 开源。
