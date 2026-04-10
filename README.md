# AI Cut

AI 文本驱动视频生成平台，面向短剧类内容生产场景。当前工程提供 Web 前端、FastAPI 后端、Worker 与本地化存储/数据库能力。
我们的终极目标是打造一个可以让你快速消耗Token（不是）批量化最大利用率的提升文转视频的多线程异步并发平台。

## 重要说明

> 项目中的示例 Key 仅用于占位，**请全部替换为你自己的有效 Key**。

> 最新版本当前为main版本，2.1.0版本正在积极开发中，正在开发模型快速切换快速接入能力，改善目前的模型端点配置麻烦的问题。

> 目前建议不使用docker部署，建议本地开发模式启动。每次版本稳定后会发布docker版本。

## QQ 交流群

- 群号：`1090387362`

## 项目截图

<img src="screencapture-localhost-5173-generate-2026-04-09-19_07_43.png" alt="AI Cut Screenshot" width="800"/>
<img src="ScreenShot_2026-04-09_190924_682.png" alt="AI Cut Screenshot" width="800"/>

## 当前能力

- 文本上传（TXT）与文本输入
- 任务创建、状态追踪、暂停/继续/重试/终止
- 统一生成能力接口（模型目录、运行任务、用量查询）
- 任务结果与日志查询
- 本地 MySQL / Redis / 文件存储

## 文档导航

- [架构说明](./docs/ARCHITECTURE.md)
- [API 文档](./docs/API.md)
- [使用文档](./docs/USER_GUIDE.md)
- [路线图](./docs/ROADMAP.md)
- [版本记录](./docs/CHANGELOG.md)
- [功能开发记录](./docs/DEVELOPMENT_LOG.md)

## 快速启动（Docker Compose）

```bash
docker compose up --build
```

默认访问地址：

- 前端：`http://127.0.0.1:5173`
- 后端：`http://127.0.0.1:8000`
- MySQL：`127.0.0.1:3306`
- Redis：`127.0.0.1:6379`

停止服务：

```bash
docker compose down
```

清空数据卷：

```bash
docker compose down -v
```

## 本地开发（非 Docker）

```bash
npm run dev
```

该命令会执行 `scripts/dev.sh`，同时启动前后端。  
详细步骤见 [使用文档](./docs/USER_GUIDE.md)。
