# JianDou（煎豆）

JianDou（中文名：煎豆）是一个 AI 文本驱动视频生成平台，面向短剧类内容生产场景。当前工程提供 Web 前端、Spring Boot 3 后端与本地化存储/数据库能力。
我们的终极目标是打造一个可以让你快速消耗Token（不是）批量化最大利用率的提升文转视频的多线程异步并发平台。

## 感谢TG大佬 Army1197的TOKEN支持😄

## Star History

<a href="https://www.star-history.com/?repos=imi4u36d%2FJianDou&type=date&legend=top-left">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/chart?repos=imi4u36d/JianDou&type=date&theme=dark&legend=top-left" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/chart?repos=imi4u36d/JianDou&type=date&legend=top-left" />
   <img alt="Star History Chart" src="https://api.star-history.com/chart?repos=imi4u36d/JianDou&type=date&legend=top-left" />
 </picture>
</a>

## 重要说明

> 项目中的示例 Key 仅用于占位，**请全部替换为你自己的有效 Key**。

> 最新版本当前为main版本，2.1.0版本正在积极开发中，正在开发模型快速切换快速接入能力，改善目前的模型端点配置麻烦的问题。

> 目前建议不使用docker部署，建议本地开发模式启动。每次版本稳定后会发布docker版本。

> 当前默认开发入口已切换到 Spring Boot 3：`npm run dev`、`npm run dev:spring`、`npm run api:spring:dev` 都会启动 `apps/api-spring`。

> 旧 Python API 入口已废弃并移除，当前以 `apps/api-spring` 作为唯一后端 API 入口。

## QQ 交流群

- 群号：`1090387362`

## 项目截图

<img src="screencapture-localhost-5173-generate-2026-04-09-19_07_43.png" alt="JianDou Screenshot" width="800"/>
<img src="ScreenShot_2026-04-09_190924_682.png" alt="JianDou Screenshot" width="800"/>

## 当前能力

- 文本上传（TXT）与文本输入
- 任务创建、状态追踪、暂停/继续/重试/终止
- 统一生成能力接口（模型目录、运行任务、用量查询）
- 任务结果与日志查询
- 本地 MySQL / 文件存储

## feature
- 模型快速切换与快速接入能力（插件化AI模型）
- 大文本、文本文件拆分异步调用大模型后组装

## 文档导航

- [架构说明](./docs/ARCHITECTURE.md)
- [Spring 后端架构草图](./docs/SPRING_API_ARCHITECTURE.md)
- [Python 到 Spring 迁移台账](./docs/PYTHON_TO_SPRING_MIGRATION_BACKLOG.md)
- [API 文档](./docs/API.md)
- [使用文档](./docs/USER_GUIDE.md)
- [Docker 部署](./docs/DEPLOY_DOCKER.md)
- [路线图](./docs/ROADMAP.md)
- [版本记录](./docs/CHANGELOG.md)
- [功能开发记录](./docs/DEVELOPMENT_LOG.md)
