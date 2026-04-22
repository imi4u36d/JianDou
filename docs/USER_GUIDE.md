# JianDou 用户使用指南

本文档面向首次使用 JianDou 的用户，重点说明两件事：

1. 如何配置模型 API Key
2. 如何启动项目

## 1. 运行前准备

推荐准备以下环境：

- Docker 与 Docker Compose Plugin
- Node.js 20+
- npm
- Java 17
- Maven 3.9+

如果你只是想最快跑起来，优先使用 Docker Compose 方式。

## 2. 配置模型 API Key

JianDou 的模型配置位于 `config/model/`，其中：

- `config/model/models.yml`：定义可选模型列表
- `config/model/providers/*.yml`：定义各厂商的基础配置
- `config/model/providers.secrets.yml`：用于覆盖和保存真实 API Key，推荐把密钥写在这里

### 2.1 推荐方式：编辑 `providers.secrets.yml`

在项目根目录创建或修改文件 `config/model/providers.secrets.yml`：

```yaml
model:
  providers:
    qwen:
      api_key: "你的阿里云 DashScope Key"
    ark:
      api_key: "你的火山引擎 Ark Key"
    seedream:
      api_key: "你的 Seedream Key"
    seedance:
      api_key: "你的 Seedance Key"
    openai:
      api_key: "你的 OpenAI Key"
```

当前仓库里实际会用到的主要 provider 包括：

- `qwen`：文本模型、视觉理解模型
- `seedream`：文生图 / 关键帧相关模型
- `seedance`：视频生成模型
- `ark`：火山引擎通用接入
- `openai`：OpenAI 兼容模型接入

如果你只使用部分模型，只填写对应 provider 的 `api_key` 即可。

### 2.2 对应配置文件位置

项目内置的 provider 基础配置文件如下：

- `config/model/providers/aliyun.yml`
- `config/model/providers/volcengine.yml`
- `config/model/providers/openai.yml`

这些文件里已经包含默认 `base_url`，通常不需要改；大多数情况下只需要补充 `api_key`。

### 2.3 安全建议

- 不要把真实密钥提交到公共仓库
- 优先把真实密钥写入 `config/model/providers.secrets.yml`
- 如需更换配置目录，后端会读取 `JIANDOU_CONFIG_DIR` 指向的外部配置目录

## 3. 启动项目

JianDou 提供两种常用启动方式：

1. Docker Compose 一键启动
2. 本地开发模式启动

## 4. Docker Compose 启动

这是最推荐的启动方式，前台、后台、Spring Boot API、MySQL 会一起启动。

### 4.1 初始化环境文件

在项目根目录执行：

```bash
cp .env.dev.example .env.dev
cp .env.prod.example .env.prod
```

至少检查并修改这些字段：

- `MYSQL_ROOT_PASSWORD`
- `MYSQL_PASSWORD`
- `JIANDOU_AUTH_BOOTSTRAP_INITIAL_ADMIN_PASSWORD`
- `JIANDOU_WEB_ORIGIN`
- `JIANDOU_PUBLIC_ADMIN_BASE_URL`

### 4.2 启动开发环境

```bash
npm run compose:dev
```

常用配套命令：

```bash
npm run compose:dev:logs
npm run compose:dev:ps
npm run compose:dev:down
npm run compose:dev:down:volumes
```

启动后默认访问地址：

- 用户前台：`http://127.0.0.1`
- 管理后台：`http://127.0.0.1:5174`
- API 健康检查：`http://127.0.0.1/api/v2/health`

### 4.3 启动生产编排

```bash
npm run compose:prod
```

常用配套命令：

```bash
npm run compose:prod:logs
npm run compose:prod:ps
npm run compose:prod:down
npm run compose:prod:down:volumes
```

## 5. 本地开发模式启动

如果你需要分别调试前端、后台和后端，可以使用本地开发模式。

### 5.1 安装前端依赖

```bash
npm --prefix apps/web install
npm --prefix apps/admin install
```

### 5.2 启动前台 + Spring Boot API

```bash
npm run dev
```

该命令会启动：

- Web 前台：`http://127.0.0.1:5173`
- Spring Boot API：`http://127.0.0.1:8000`

### 5.3 单独启动后台管理端

```bash
npm run admin:dev
```

启动后访问：

- 管理后台：`http://127.0.0.1:5174`

### 5.4 单独启动后端

```bash
npm run api:dev
```

注意：

- 本地开发模式下，数据库等基础设施需要你自行准备
- 默认开发代理会把 `/api/v2` 和 `/storage` 转发到 `http://127.0.0.1:8000`

## 6. 数据库变更与重建

后端现在通过 Flyway 管理 MySQL 结构变更，迁移脚本目录是 `apps/api-spring/src/main/resources/db/migration/`。

约定如下：

- `V1__init.sql`：当前完整初始化结构，只用于新库首次建库
- 后续改表一律新增版本脚本，例如 `V3__add_task_index.sql`
- 不再直接维护单独的 `schema.sql`，避免结构变更没有版本记录

如果你重建 MySQL 数据卷，Flyway 会在应用启动时自动按顺序执行迁移脚本，把空库恢复到最新结构。

开发环境彻底删除 MySQL 数据并重建：

```bash
npm run compose:dev:down:volumes
npm run compose:dev
```

生产编排同理：

```bash
npm run compose:prod:down:volumes
npm run compose:prod
```

如果是已有老库首次接入，Flyway 会先基线登记，再执行后续兼容迁移，不会重复整库建表。

## 7. 启动后检查

建议按下面顺序检查：

1. 打开用户前台，确认页面能正常加载
2. 打开后台管理端，确认登录页或首页可访问
3. 访问 `http://127.0.0.1/api/v2/health`，确认 API 健康检查返回正常
4. 在创建任务前，确认对应模型 provider 已配置真实 `api_key`

如果模型密钥未配置，任务创建或模型调用会失败。

## 8. 常见文件位置

- 环境变量示例：`.env.dev.example`、`.env.prod.example`
- 当前环境变量：`.env.dev`、`.env.prod`
- 模型定义：`config/model/models.yml`
- Provider 配置：`config/model/providers/`
- Provider 密钥覆盖：`config/model/providers.secrets.yml`
- 数据库迁移：`apps/api-spring/src/main/resources/db/migration/`
- 启动脚本：`scripts/compose-stack.sh`、`scripts/dev-spring.sh`
