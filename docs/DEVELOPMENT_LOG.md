# 功能开发记录

## 2026-03-25

### 阶段

项目启动与首版骨架搭建

### 本次开发目标

- 确认 MVP 边界
- 建立前后端工程结构
- 落地统一配置方式
- 为本地开发准备 MySQL、Redis、本地存储方案
- 建立文档体系

### 已落实内容

1. 工程结构初始化
- 创建 `apps/web`、`apps/api`、`apps/worker`、`packages/*`、`docs`、`config`、`storage`

2. 配置体系
- 使用 `config/app.toml` 管理应用、数据库、Redis、本地存储、模型、流水线配置
- 使用 `apps/web/public/runtime-config.json` 管理前端运行时 API 地址

3. 前端首版页面
- 任务列表页
- 新建任务页
- 任务详情页
- 基础状态轮询与上传/创建任务交互

4. 并行协作
- 已启用需求、架构、UI/UX、前端、后端、测试 6 个 agent 并行推进

### 待继续

- 后端任务模型与 API
- 本地视频上传和素材输出
- FFmpeg 裁切与片头片尾拼接
- Qwen provider 接入层
- 完整使用文档和接口文档

