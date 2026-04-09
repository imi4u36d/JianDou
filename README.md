# AI Cut

AI 文本驱动视频生成平台，面向短剧类内容生产场景。当前工程提供 Web 前端、FastAPI 后端、Worker 与本地化存储/数据库能力。

## 重要说明

项目中的示例 Key 仅用于占位，**请全部替换为你自己的有效 Key**。

## QQ 交流群

- 群号：`1090387362`

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


