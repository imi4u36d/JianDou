# 架构说明

## 1. 系统概览

AI Cut 采用前后端分离 + 可独立 worker 的架构，核心目标是把“文本输入 -> 任务编排 -> 视频生成 -> 结果回传”串成统一任务链路。

主要组件：

- `apps/web`：Vue 3 + Vite 前端
- `apps/api`：FastAPI API 网关
- `apps/worker`：任务消费进程（可选）
- `packages/pipeline`：任务服务与执行流水线
- `packages/ai`：模型调用、规划与生成编排
- `packages/db`：SQLAlchemy 数据模型与数据库初始化
- `packages/storage`：本地文件存储封装
- `packages/shared`：配置与跨模块 schema
- `MySQL`：任务与结果元数据
- `Redis`：任务队列（非 inline 模式）

## 2. 目录结构

```text
ai_cut/
├── apps/
│   ├── api/        # FastAPI 服务
│   ├── web/        # Vue 前端
│   └── worker/     # Worker 进程入口
├── packages/
│   ├── ai/         # 文本/视频生成与编排
│   ├── pipeline/   # TaskService / TaskWorker
│   ├── db/         # ORM 模型与建表
│   ├── storage/    # 本地存储抽象
│   ├── media/      # 媒体处理工具
│   ├── shared/     # 配置与公共 schema
│   └── backend_core/ # 对 pipeline 的兼容导出层
├── config/         # app 与 prompts 配置
├── storage/        # 上传、产物、临时文件
└── docker-compose.yml
```

## 3. 运行时流程

### 3.1 任务创建与执行

1. 前端调用 `POST /api/v2/tasks/generation` 创建任务  
2. `TaskService.create_generation_task` 落库 `biz_tasks`，写入任务上下文  
3. `dispatch_task` 根据 `execution_mode` 选择：
- `inline`：本地线程直接执行 `process_task`
- 非 `inline`：投递 Redis 队列，由 worker 消费
4. 流水线执行阶段更新状态：
- `PENDING -> ANALYZING -> PLANNING -> RENDERING -> COMPLETED`
- 失败时置为 `FAILED`
5. 结果写入数据库并落盘到 `storage/outputs`

### 3.2 文件流转

- 上传素材：`storage/uploads`
- 生成产物：`storage/outputs`
- 临时上下文/追踪：`storage/temp`
- 对外访问统一挂载：`/storage/*`

## 4. 配置体系

- 主配置：`config/app.toml`
- 示例配置：`config/app.example.toml`
- 提示词配置：`config/prompts/*.toml`
- 支持通过 `AI_CUT_*` 环境变量覆盖（如 `AI_CUT_DATABASE_URL`、`AI_CUT_MODEL_API_KEY`）

## 5. 数据与状态

核心业务表：

- `biz_tasks`：任务主表
- `biz_task_results`：任务输出结果
- `biz_task_status_history`：状态变更记录
- `biz_task_model_calls`：模型调用记录
- `biz_system_logs`：系统日志沉淀
- `biz_material_assets`：素材资产信息

任务状态枚举（见 `packages/shared/ai_cut_shared/schemas.py`）：

- `PENDING`
- `PAUSED`
- `ANALYZING`
- `PLANNING`
- `RENDERING`
- `COMPLETED`
- `FAILED`

