# 架构说明

## 1. 系统概览

JianDou 采用前后端分离 + Spring 内嵌 worker 的架构，核心目标是把“文本输入 -> 任务编排 -> 视频生成 -> 结果回传”串成统一任务链路。

主要组件：

- `apps/web`：Vue 3 + Vite 前端
- `apps/api-spring`：Spring Boot 3 API 与内嵌任务执行器
- `MySQL`：任务与结果元数据

## 2. 目录结构

```text
jiandou/
├── apps/
│   ├── api-spring/ # Spring Boot 后端
│   ├── web/        # Vue 前端
├── config/         # app 与 prompts 配置
├── storage/        # 上传、产物、临时文件
└── docker-compose.yml
```

## 3. 运行时流程

### 3.1 任务创建与执行

1. 前端调用 `POST /api/v2/tasks/generation` 创建任务  
2. Spring 应用服务落库 `biz_tasks`，写入任务上下文
3. `TaskExecutionCoordinator` 创建 attempt 并进入数据库队列
4. API 进程内的 `TaskWorkerRunner` 消费任务并执行分镜流水线
5. 流水线执行阶段更新状态：
- `PENDING -> ANALYZING -> PLANNING -> RENDERING -> COMPLETED`
- 失败时置为 `FAILED`
6. 结果写入数据库并落盘到 `storage/outputs`

### 3.2 文件流转

- 上传素材：`storage/uploads`
- 生成产物：`storage/outputs`
- 临时上下文/追踪：`storage/temp`
- 对外访问统一挂载：`/storage/*`

## 4. 配置体系

- 主配置：`config/app.yml`
- 示例配置：`config/app.example.yml`
- 提示词配置：`config/prompts/*.yml`
- 支持通过 `JIANDOU_*` 环境变量覆盖（如 `JIANDOU_DATABASE_URL`、`JIANDOU_MODEL_API_KEY`）

## 5. 数据与状态

核心业务表：

- `biz_tasks`：任务主表
- `biz_task_results`：任务输出结果
- `biz_task_status_history`：状态变更记录
- `biz_task_model_calls`：模型调用记录
- `biz_system_logs`：系统日志沉淀
- `biz_material_assets`：素材资产信息

任务状态枚举：

- `PENDING`
- `PAUSED`
- `ANALYZING`
- `PLANNING`
- `RENDERING`
- `COMPLETED`
- `FAILED`
