# 版本记录

## v0.1.0-alpha - 2026-03-25

首个可开发版本，完成项目基础骨架初始化。

### 已完成

- 初始化单仓目录结构。
- 确认技术栈：
  - 前端：Vue 3 + TypeScript + Vite + Vue Router + TailwindCSS
  - 后端：FastAPI
  - 数据库：MySQL（本地）
  - 队列/缓存：Redis（本地）
  - 存储：本地文件存储
  - 模型 provider：Qwen（可配置）
- 新增根配置文件 `config/app.toml` 和示例配置 `config/app.example.toml`
- 新增本地 MySQL / Redis 的 `docker-compose.yml`
- 初始化前端页面骨架：
  - 任务列表
  - 新建任务
  - 任务详情
- 建立运行时配置文件 `apps/web/public/runtime-config.json`
- 建立项目级文档目录

### 计划中

- 完成 FastAPI 后端 API、上传、任务状态、FFmpeg 流水线
- 完成产品范围、架构、UI/UX、测试计划文档
- 完成使用文档和 API 文档

