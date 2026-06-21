# JianDou（煎豆）

JianDou 是一个文本到视频工作台。上传小说章节、粘贴正文或输入提示词，即可通过可配置的多模型链路生成视频。

## 快速启动

```bash
# 1. 准备本地环境变量
cp .env.dev.example .env

# 2. 配置模型 API Key（按需启用）
cp config/model/providers.secrets.example.yml config/model/providers.secrets.yml
# 编辑 config/model/providers.secrets.yml，填入各厂商密钥
```

**方式一：Docker**

```bash
cp .env.docker.example .env.docker
docker build -t jiandou .
docker run -d -p 8100:8000 \
  --env-file .env.docker \
  -v ./config:/app/config \
  -v ./data:/app/data \
  -v ./storage:/app/storage \
  jiandou
```

镜像默认监听容器内 `8000` 端口，并在启动时自动执行数据库迁移；如需手动控制，可设置 `JIANDOU_AUTO_MIGRATE=false`。如果修改 `.env.docker` 里的 `JIANDOU_SERVER_PORT`，需要同步调整 `docker run -p` 的容器端口。

**方式二：本地命令**

```bash
# 首次需安装依赖
npm install
uv sync
uv run jiandou db migrate
npm run serve
```

启动后访问：
- 用户前台：`http://127.0.0.1:8100`
- 管理后台：`http://127.0.0.1:8100/admin`

健康检查：
- 存活检查：`GET /api/v3/health`
- 就绪检查：`GET /api/v3/ready`，会验证数据库和存储目录可用性；容器镜像也使用该端点作为 `HEALTHCHECK`

如果前端和 API 不在同一个 origin 下，部署时需要设置 `JIANDOU_WEB_ORIGIN`；多个可信前端域名可用逗号分隔写入 `JIANDOU_TRUSTED_ORIGINS`。后端会拒绝非可信来源发起的状态变更 API 请求。

登录和邀请码激活接口默认带有按客户端 IP 计数的基础限流，可通过 `JIANDOU_AUTH_LOGIN_RATE_LIMIT`、`JIANDOU_AUTH_INVITE_ACTIVATION_RATE_LIMIT` 和 `JIANDOU_AUTH_RATE_LIMIT_WINDOW_SECONDS` 调整。

API 默认发送基础浏览器安全响应头；当 `JIANDOU_COOKIE_SECURE=true` 时会额外启用 HSTS，生产环境应通过 HTTPS 访问。

完整配置变量见 [docs/configuration.md](docs/configuration.md)。


## 开发

### 前端开发

```bash
# 拷贝环境变量模板
cp frontends/web/.env.example frontends/web/.env

# 启动前端开发服务器（默认 http://localhost:5173）
npm run web:dev

# 类型检查
npm run web:typecheck

# 代码检查与格式化
npm run web:lint
npm run web:format

# 运行前端测试
npm run web:test

# 测试覆盖率
npx vitest run --coverage
```

前端使用 Vite 开发服务器，自动将 `/api/v3` 和 `/storage` 请求代理到后端。如需修改后端地址，编辑 `frontends/web/.env` 中的 `VITE_API_PROXY_TARGET`。

详细架构说明见 [docs/frontend-architecture.md](docs/frontend-architecture.md)，开发指南见 [CONTRIBUTING.md](CONTRIBUTING.md)。

### 后端开发

```bash
# 代码检查（ruff lint，零错误）
uv run ruff check backend/

# 运行全部测试（314 个测试，零失败）
uv run pytest

# 按标记分类运行测试
uv run pytest -m unit      # 快速单元测试（64 个）
uv run pytest -m api       # API 端点测试（90 个）
uv run pytest -m domain    # 领域层测试（33 个）
uv run pytest -m "not slow" # 跳过慢速测试

# 导出 OpenAPI 模式
uv run jiandou openapi --output docs/openapi.json

# 仅启动 API
npm run api:dev
```

## 工作流程

```
文本输入 ──▶ 文本模型(生成分镜/提示词)
                ──▶ 视觉模型(理解参考图)
                        ──▶ 关键帧模型(生成首尾帧)
                                ──▶ 视频模型(生成视频)
                                        ──▶ 预览/下载/评分
```

每一段模型均可独立选择厂商和模型版本，按需组合。

## 能力概述

**创作输入**
- 上传 TXT 文件或直接粘贴正文，自动提取内容生成提示词
- 也可直接输入自定义提示词，灵活控制生成方向
- 支持参考图作为关键帧的首帧或尾帧

**生成控制**
- 多段模型链路（文本/视觉/关键帧/视频）支持不同厂商自由组合
- 输出参数动态约束：画幅、清晰度、时长区间、生成数量、Seed 等
- 参数选项会根据所选视频模型的能力自动过滤，避免无效配置

**任务管理**
- 实时查看任务进度、阶段状态、耗时和视频预览
- 支持任务的创建、筛选、详情查看
- 支持重试、暂停、继续、终止、删除、评分等运维操作

**Seed 管理**
- 自动汇总高评分任务中的可用 Seed
- 支持一键回填 Seed 到当前任务，提升稳定出片效率

**管理后台**
- 独立的管理后台，与用户前台分离
- 适合内容生产团队和管理运维分层协作

## 模型配置

模型配置集中在 `config/model/` 目录：

```
config/model/
├── models.yml                  # 可选模型列表定义
├── providers/                  # 各厂商基础配置（base_url 等）
│   ├── volcengine.yml
│   ├── deepseek.yml
│   └── openai.yml
├── providers.secrets.example.yml # API Key 示例模板（提交到仓库）
└── providers.secrets.yml       # API Key 覆盖（本地文件，不提交）
```

支持的厂商：阿里云（通义千问/万相）、火山引擎（豆包/Seedream/Seedance）、OpenAI 兼容接口。

## 开发与验证

```bash
# 后端 lint + 测试
npm test

# 数据库迁移从空库验证
TMP_DB=$(mktemp -t jiandou.XXXXXX.db) && \
  JIANDOU_DATABASE_URL="sqlite+aiosqlite:///$TMP_DB" uv run alembic upgrade head && \
  rm -f "$TMP_DB"

# 前端和共享包类型检查
npm run packages:typecheck
npm run web:typecheck

# 导出 OpenAPI 契约（生成 docs/openapi.json，本地生成物不提交）
npm run api:openapi

# 发布前完整预检（会自动清理生成物）
npm run release:check
```

后端数据库模型要求所有表/字段都有注释，核心字符串状态字段必须有数据库约束；这些规则已纳入测试门禁。

仓库只提交源码级静态资源，例如 `static/web/brand/` 下的品牌图形。`npm run web:build` 生成的 `static/web/assets/` 和 `static/web/index.html` 属于本地/镜像构建产物，不应提交；仓库卫生测试会拦截 secrets、本地数据库和前端构建产物被误提交。

后端模块职责和改动边界见 [docs/backend-architecture.md](docs/backend-architecture.md)，数据库设计约束见 [docs/database-design.md](docs/database-design.md)。

版本变更见 [CHANGELOG.md](CHANGELOG.md)，发布流程见 [docs/release-process.md](docs/release-process.md)。

## 社区与支持

- QQ 交流群：`1090387362`
- [报告 Bug / 功能建议](https://github.com/imi4u36d/JianDou/issues)
- 使用求助、Bug、功能建议和安全问题的分流说明见 [SUPPORT.md](SUPPORT.md)。

## Star History

<a href="https://www.star-history.com/?repos=imi4u36d%2FJianDou&type=date&legend=top-left">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/chart?repos=imi4u36d/JianDou&type=date&theme=dark&legend=top-left" />
    <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/chart?repos=imi4u36d/JianDou&type=date&legend=top-left" />
    <img alt="Star History Chart" src="https://api.star-history.com/chart?repos=imi4u36d/JianDou&type=date&legend=top-left" />
  </picture>
</a>

## License

本项目采用仓库内的 [License](./License)。
