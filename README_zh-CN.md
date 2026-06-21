<p align="center">
  <a href="README.md">English</a> | <strong>简体中文</strong> | <a href="README_ja-JP.md">日本語</a>
</p>

<p align="center">
  <img src="static/web/brand/logo.png" alt="JianDou Logo" width="120" />
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

## 核心特性

**灵活输入**
- 上传 `.txt` 文件或直接粘贴正文，自动提取内容用于提示词生成。
- 支持自定义提示词，完全自由控制生成方向。
- 可附加参考图作为关键帧的首帧或尾帧。

**多模型流水线**
- 四个独立可配阶段：文本模型（脚本/分镜）→ 视觉模型（参考图理解）→ 关键帧模型（首尾帧生成）→ 视频模型（视频合成）。
- 厂商自由组合：阿里云（通义千问/万相）、火山引擎（豆包/Seedream/Seedance）以及任意 OpenAI 兼容接口。
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
- Docker 优先部署，自动数据库迁移和健康检查。
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

# 2. 构建并运行
docker build -t jiandou .
docker run -d -p 8100:8000 \
  --env-file .env.docker \
  -v ./config:/app/config \
  -v ./data:/app/data \
  -v ./storage:/app/storage \
  jiandou
```

镜像在容器内监听 `8000` 端口，启动时自动执行数据库迁移。设置 `JIANDOU_AUTO_MIGRATE=false` 可跳过自动迁移。

### 方式二：本地开发

```bash
# 1. 环境配置
cp .env.dev.example .env
cp config/model/providers.secrets.example.yml config/model/providers.secrets.yml
# 编辑 providers.secrets.yml 填入 API Key

# 2. 安装依赖
npm install
uv sync

# 3. 执行数据库迁移
uv run jiandou db migrate

# 4. 启动服务
npm run serve
```

启动后访问：
- **用户前台**：`http://127.0.0.1:8100`
- **管理后台**：`http://127.0.0.1:8100/admin`

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
│   ├── deepseek.yml
│   └── openai.yml
├── providers.secrets.example.yml # API Key 模板（提交到仓库）
└── providers.secrets.yml         # 你的 API Key（本地文件，不提交）
```

支持的厂商：
- **阿里云** — 通义千问、万相
- **火山引擎** — 豆包、Seedream、Seedance
- **OpenAI 兼容接口** — 任意 OpenAI 兼容 API 端点

## 配置说明

所有运行时设置通过环境变量控制。完整参考见 [docs/configuration.md](docs/configuration.md)。

关键变量：

| 变量 | 说明 | 默认值 |
|---|---|---|
| `JIANDOU_SERVER_PORT` | 后端监听端口 | `8100` |
| `JIANDOU_DATABASE_URL` | 数据库连接字符串 | `sqlite+aiosqlite:///./data/jiandou.db` |
| `JIANDOU_SECRET_KEY` | JWT 签名密钥 | （必须设置） |
| `JIANDOU_WEB_ORIGIN` | 前端来源（CORS） | `http://127.0.0.1:8100` |
| `JIANDOU_TRUSTED_ORIGINS` | 额外可信来源（逗号分隔） | — |
| `JIANDOU_COOKIE_SECURE` | 启用安全 Cookie + HSTS | `false` |
| `JIANDOU_WORKER_CONCURRENCY` | 异步工作线程数 | `2` |
| `JIANDOU_DEFAULT_ASPECT_RATIO` | 默认视频画幅 | `16:9` |
| `JIANDOU_DEFAULT_DURATION_SECONDS` | 默认视频时长 | `8` |

认证接口内置限流。可通过 `JIANDOU_AUTH_LOGIN_RATE_LIMIT`、`JIANDOU_AUTH_INVITE_ACTIVATION_RATE_LIMIT` 和 `JIANDOU_AUTH_RATE_LIMIT_WINDOW_SECONDS` 调整。

## 开发指南

### 前端

前端使用 **Vue 3 + TypeScript + Element Plus + Tailwind CSS**，Vite 作为开发服务器并自动代理 API 请求。

```bash
# 拷贝前端环境变量模板
cp frontends/web/.env.example frontends/web/.env

# 开发服务器（默认 http://localhost:5173）
npm run web:dev

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

后端使用 **FastAPI + SQLAlchemy + Alembic**，SQLite 通过 aiosqlite 驱动。

```bash
# 代码检查（ruff，要求零错误）
uv run ruff check backend/

# 运行全部测试（314 个测试，要求零失败）
uv run pytest

# 按分类运行测试
uv run pytest -m unit      # 快速单元测试（64 个）
uv run pytest -m api       # API 端点测试（90 个）
uv run pytest -m domain    # 领域层测试（33 个）
uv run pytest -m "not slow" # 跳过慢速测试

# 导出 OpenAPI 模式
uv run jiandou openapi --output docs/openapi.json

# 仅启动 API 开发服务器
npm run api:dev
```

模块职责见 [docs/backend-architecture.md](docs/backend-architecture.md)，数据库设计见 [docs/database-design.md](docs/database-design.md)。

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
