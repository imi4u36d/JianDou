# 版本记录

## Unreleased

### Docs

- 补齐缺失文档：`ARCHITECTURE.md`、`API.md`、`USER_GUIDE.md`、`ROADMAP.md`、`CHANGELOG.md`、`DEVELOPMENT_LOG.md`
- 更新根 `README.md`，修复文档入口并补充 QQ 交流群信息

### Backend

- Docker 编排已切换为 `MySQL + Spring API + Web`，移除旧 Python worker / Redis 运行依赖
- Spring 内嵌 worker 已接管多镜头任务执行、join 拼接与恢复主链

## 0.1.0

- 初始工程版本，包含 Web/API/Worker 与任务生成主流程
- 支持本地 MySQL + Redis + 文件存储
- 支持文本驱动的视频任务创建、执行和结果查询
