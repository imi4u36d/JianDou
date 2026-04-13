# Python -> Spring Boot 迁移台账

## 1. API 层映射

已移除的 Python API 入口：

- `apps/api/app/main.py`
- `apps/api/app/routers/health.py`
- `apps/api/app/routers/uploads.py`
- `apps/api/app/routers/tasks.py`
- `apps/api/app/routers/admin.py`
- `apps/api/app/routers/generation_v2.py`

当前 FastAPI 路由统一依赖：

- `request.app.state.runtime`
- `runtime.service`

已在 Spring 骨架中接住的接口族：

- `health`
- `uploads`
- `tasks`
- `admin`
- `generation`

当前仍属于收尾优化阶段的接口/能力：

- 更细粒度的 stage 级恢复与断点续跑
- 失败后的清理与重放策略
- 监控查询与运维诊断增强

## 2. 任务执行链路映射

已被 Spring 接管的 Python 执行链路关键文件：

- `packages/pipeline/jiandou_pipeline/runtime.py`
- `packages/pipeline/jiandou_pipeline/service.py`
- `packages/pipeline/jiandou_pipeline/worker.py`
- `packages/pipeline/jiandou_pipeline/task_trace.py`

建议迁移到 Spring 的组件拆分：

- `api/controller`
  - 负责 HTTP 入参与错误码转换
- `task/application`
  - 负责创建任务、状态流转、管理端聚合查询
- `task/application/port`
  - 定义持久化、队列、模型调用、存储端口
- `task/domain`
  - 承载任务聚合、尝试、阶段运行、状态枚举
- `task/infrastructure`
  - 负责 JDBC/MyBatis、Redis、文件存储等具体实现
- `worker`
  - 负责 claim、heartbeat、阶段执行、重试恢复

建议优先顺序：

1. 先迁移任务查询与任务主状态写入
2. 再迁移 attempt / stage run / status history / model calls
3. 再把 task worker 与 generation 统一成真实模型调用链
4. 最后做历史 Python 目录清理与文档收口

## 3. 数据库映射优先级

SQL 入口：

- `packages/db/sql/mysql_init_schema.sql`
- `packages/db/jiandou_db/models.py`

建议第一批优先映射的表：

1. `biz_tasks`
2. `biz_task_attempts`
3. `biz_task_stage_runs`
4. `biz_task_status_history`
5. `biz_task_model_calls`
6. `biz_task_results`
7. `biz_material_assets`

## 4. 当前 Spring 已落地的迁移骨架

代码位置：

- `apps/api-spring/src/main/java/com/jiandou/api/task/application`
- `apps/api-spring/src/main/java/com/jiandou/api/task/application/port`
- `apps/api-spring/src/main/java/com/jiandou/api/task/domain`
- `apps/api-spring/src/main/java/com/jiandou/api/task`

本轮新增价值：
- 控制器层已对外提供 health、uploads、tasks、admin、generation 五大类接口，前端无感知。  
- `TaskApplicationService` 抽象完成，`TaskPersistencePort` / `TaskAggregateQueryPort` / `TaskQueuePort` 已定义，便于逐步替换基础设施实现。  
- `RuntimeDescriptorService`、`DefaultGenerationApplicationService`、`DefaultUploadApplicationService` 已把 controller 中的主要占位业务下沉。  
- `TaskQueueCoordinator` 已把队列占位能力从 `TaskApplicationServiceImpl` 中抽离。  
- `task/domain` 里聚合、尝试、阶段、状态枚举已经跟 Python 表/字段对齐。  
- `task/persistence` 第一批表行映射已经落地，当前任务主数据、attempt、status history、queue event、worker instance 已切到 MyBatis-Plus，便于边迁边验。  
- `generation/runs` 的 `script` 已接入真实文本模型；`image` / `video` 已接入文本提示词重写、远端媒体生成、任务轮询与本地回存。  
- `TaskWorkerRunner` 已改为调用 `GenerationApplicationService`，会落 `script/image/video` 三类 run，并回写 materials/results/stage-runs 与 execution context。  
- `TaskQueueCoordinator` 已不再维护 JVM 内存队列，当前 queue source 改为 `biz_task_attempts.status='QUEUED'`，worker 通过 DB `claim` 消费。  
- worker 已拆出独立 heartbeat 维护线程，并能把 stale worker 标记为 `STALE`，对 stale running claim 执行自动 `retry_enqueued` 回收。  
- `/api/v2/admin/workers`、`/api/v2/admin/queue`、`/api/v2/admin/queue/events`、`/api/v2/admin/traces` 已可读取 MySQL 中的真实监控数据。

## 模块边界与 Python -> Spring 映射

| Python 源 | Spring 对应托管 | 当前状态 | 说明 |
| --- | --- | --- | --- |
| `packages/pipeline/jiandou_pipeline/runtime.py` | Spring `HealthController` + `RuntimeDescriptorService` | 已接管 | Python runtime 已不再参与运行。 |
| `packages/pipeline/jiandou_pipeline/service.py` | `TaskApplicationService` + `TaskApplicationServiceImpl` | 已接管 | 任务状态流转、聚合查询与远端结果查询已落到 Spring。 |
| `packages/pipeline/jiandou_pipeline/worker.py` | `TaskQueuePort` + `TaskQueueCoordinator` + `TaskExecutionCoordinator` + `TaskWorkerRunner` | 已接管 | 数据库队列、worker 心跳、trace、多镜头执行、join 与恢复主链都已迁到 Spring。 |
| `packages/db/jiandou_db/models.py` + `packages/db/sql/mysql_init_schema.sql` | `task/domain` + `task/persistence` + `task/infrastructure` | 已接管主链 | Java 领域模型与 MyBatis-Plus 已承担主链表的读写与聚合。 |

## 当前优先级梳理

1. **任务主数据 + 状态历史**：`biz_tasks` + `biz_task_status_history` 是旧 API 的核心，先保障读取/写入，使 `TaskViewMapper` 对接上正式数据。  
2. **精细恢复语义**：当前 stale claim 与 clip 级恢复已接通，但还没有更细的 stage 级 resume、lease token、去重物料清理。  
3. **结果治理**：继续增强视频结果标准化、`lastFrameUrl` 约束与 join 产物治理。  
4. **历史清理**：删除已脱钩的 Python 目录与过期文档描述。  

## 进度备注

- `TaskApplicationService` 已抽象出 controller 所需的全量接口，便于后续替换实现。  
- `TaskPersistencePort`/`TaskQueuePort` 已定义，后续只要补 `task/infrastructure` 即可切换到真实 DB/queue。  
- `TaskViewMapper` 继续复用，保持前端响应结构与 Python 版本一致。  
- `generation/runs` 与 `task worker` 当前已能产出真实远端图片/视频素材，且 task worker 已回写 `analysisRunId/scriptRunId/imageRunId/videoRunId` 到 task context；但多镜头编排、join 拼接与 stage 级恢复仍未迁完。
