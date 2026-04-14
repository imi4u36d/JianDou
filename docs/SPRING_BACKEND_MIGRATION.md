# Spring Boot 3 后端迁移

## 当前状态

- 新增 Spring Boot 3 + Maven 工程：`apps/api-spring`
- 当前 Spring 包内部分层草图见 `docs/SPRING_API_ARCHITECTURE.md`
- 前端仍保持当前 Vue 3 + Vite 架构
- 接口前缀仍保持 `/api/v2`
- 当前 Spring 版已落地的基础接口：
  - `GET /api/v2/health`
  - `POST /api/v2/uploads/texts`
  - `POST /api/v2/uploads/videos`
  - `POST /api/v2/tasks/generation`
  - `POST /api/v2/tasks/generate-prompt`
  - `GET /api/v2/tasks`
  - `GET /api/v2/tasks/{taskId}`
  - `GET /api/v2/tasks/{taskId}/trace`
  - `GET /api/v2/tasks/{taskId}/status-history`
  - `GET /api/v2/tasks/{taskId}/model-calls`
  - `GET /api/v2/tasks/{taskId}/results`
  - `GET /api/v2/tasks/{taskId}/materials`
  - `GET /api/v2/tasks/{taskId}/logs`
  - `GET /api/v2/tasks/seedance/{remoteTaskId}`
  - `POST /api/v2/tasks/{taskId}/retry`
  - `POST /api/v2/tasks/{taskId}/pause`
  - `POST /api/v2/tasks/{taskId}/continue`
  - `POST /api/v2/tasks/{taskId}/terminate`
  - `DELETE /api/v2/tasks/{taskId}`
  - `GET /api/v2/admin/overview`
  - `GET /api/v2/admin/tasks`
  - `GET /api/v2/admin/tasks/{taskId}`
  - `GET /api/v2/admin/tasks/{taskId}/trace`
  - `GET /api/v2/admin/traces`
  - `GET /api/v2/admin/workers`
  - `GET /api/v2/admin/workers/{workerInstanceId}`
  - `GET /api/v2/admin/queue`
  - `GET /api/v2/admin/queue/events`
  - `GET /api/v2/admin/tasks/{taskId}/queue-events`
  - `POST /api/v2/admin/tasks/{taskId}/retry`
  - `POST /api/v2/admin/tasks/{taskId}/terminate`
  - `DELETE /api/v2/admin/tasks/{taskId}`
  - `POST /api/v2/admin/tasks/bulk-delete`
  - `POST /api/v2/admin/tasks/bulk-retry`
  - `GET /api/v2/generation/catalog`
  - `GET /api/v2/generation/runs`
  - `POST /api/v2/generation/runs`
  - `GET /api/v2/generation/runs/{runId}`
  - `GET /api/v2/generation/usage`

## 目前实现性质

当前 Spring 版本已承担正式后端主链，旧 Python worker 不再参与运行：

- 任务域当前使用 `TaskApplicationServiceImpl`，并通过 `MybatisTaskRepository` 持久化任务主数据
- 适合先把前端与 Spring API 契约稳定下来
- `generation/runs` 当前已真实接入 `probe` / `script` / `image` / `video`，并持久化 `run.json`
- `image` 会走文本提示词重写 + 远端图片生成并回存本地
- `video` 会走文本提示词重写 + 远端视频生成、任务轮询、结果下载回本地
- worker 实例、队列事件、全局 traces 已落到 MySQL，可通过 `/api/v2/admin` 查看真实持久化监控数据
- 多镜头顺序生成、join 拼接调度、clip 级恢复与产物回写已迁到 Spring
- 当前剩余工作主要是继续压缩历史 Python 痕迹、补文档与做更深的恢复/监控优化

## 迁移状态概览

- **已完成**：将 `/api/v2` 系列接口（health、uploads、tasks、admin、generation）全量出口迁到 Spring，并用 `TaskApplicationService` 构建统一应用层接口，前端无需切换。  
- **进行中**：领域模型（`TaskAggregate`/`TaskAttemptSnapshot`/`TaskStageRunSnapshot`）和第一批持久化 row（`TaskRow`/`TaskAttemptRow`/`TaskStageRunRow`/`TaskStatusHistoryRow`）已对齐 Python 表结构，当前已通过 MyBatis-Plus 落地 `biz_tasks`、`biz_task_status_history`、`biz_task_queue_events`、`biz_worker_instances` 等表。  
- **进行中**：`TaskWorkerRunner` 已改为调用 `GenerationApplicationService`，会串行创建 `script`、`image`、`video` 三类 run，并把 runId、script、素材、结果写回 task 明细；worker 启动、心跳、停止状态也已持久化。  
- **进行中**：队列已从 JVM 内存列表切到基于 `biz_task_attempts` 的最小 durable queue 语义，`snapshot` 与 `claim` 都直接查库，管理端可以看到真实 `enqueued -> claimed -> completed` 链路。  
- **进行中**：worker 现已拆出独立 heartbeat 维护线程，并支持 stale claim recovery；当失效 worker 长时间不心跳时，可将任务重新标记为 `retry_enqueued` 再次消费。  
- **进行中**：`DefaultGenerationApplicationService` 已接入真实文本模型、Seedream 图片生成、Seedance/Wan 视频生成；`GET /api/v2/tasks/seedance/{remoteTaskId}` 已补到 Spring 远端查询。  
- **已完成**：旧 Python worker 已可下线；当前任务消费、attempt、heartbeat、stale recovery、多镜头 clip 输出与 join 拼接均由 Spring 负责。  
- **风险**：当前 Spring 已能跑通多镜头 `task -> script -> image -> video -> join`，但更细粒度的 stage 级恢复、清理策略与更完整的运营监控仍可继续加强。

## Python -> Spring 对照

| Python 源 | Spring 对应 | 当前状态 | 说明 |
| --- | --- | --- | --- |
| `packages/pipeline/jiandou_pipeline/runtime.py::build_runtime` | `HealthController` + `RuntimeDescriptorService` | 已接管 | runtime 相关描述已由 Spring 统一暴露，旧 Python runtime 可移除。 |
| `packages/pipeline/jiandou_pipeline/service.py` | `task/application/TaskApplicationService` + `TaskApplicationServiceImpl` | 已接管 | 创建/重试/暂停/继续/终止、任务详情聚合、远端结果查询已由 Spring 应用服务承担。 |
| `packages/pipeline/jiandou_pipeline/service.py::_dispatch_task` + `packages/pipeline/jiandou_pipeline/worker.py::TaskWorker` | `TaskQueuePort` + `TaskQueueCoordinator` + `TaskExecutionCoordinator` + `TaskWorkerRunner` | 已接管 | 数据库队列、claim、heartbeat、stale recovery、多镜头 clip 执行与 join 调度都已落到 Spring。 |
| `packages/db/jiandou_db/models.py` + `packages/db/sql/mysql_init_schema.sql` | `task/domain` + `task/persistence` | 已接管主链 | 主链所需表读写与聚合映射已由 MyBatis-Plus 承担，后续只剩模型细节与治理性增强。 |

## 优先级说明

1. **任务主表 + 状态历史**：`biz_tasks`、`biz_task_status_history`、`biz_task_model_calls` 是 Spring 替换 Python API 的核心，先做查询/写入，保证 `TaskViewMapper` 的响应结构与旧系统一致。  
2. **真实单镜头执行**：当前已打通 `task worker -> generation service -> task materials/results/context`，并接入真实文本/图片/视频模型；下一步补任务结果聚合与首尾帧上下文回写。  
3. **恢复与监控深化**：继续强化 stage 级恢复、素材清理、失败诊断与运维监控。  

## 下一步计划

- 补充 `biz_tasks.context_json` 的 execution context 约定，并围绕 `analysisRunId/scriptRunId/imageRunId/videoRunId` 扩展监控查询。  
- 补充更细粒度的 resume/recovery 语义；当前 stale claim 已能整体重入队，但还不是按 stage/clip 精准恢复。  
- 继续完善 Spring 中的视频结果聚合、`lastFrameUrl` 约束、join 产物治理与更细粒度恢复。

## 推荐迁移顺序

1. 把 `health / uploads / tasks / admin / generation-catalog` 的接口契约稳定在 Spring 侧
2. 引入 Spring Data JDBC / JPA 或 MyBatis，先迁移 `tasks / status history / model calls / outputs`
3. 把 Python 的 `TaskService` 逻辑拆成 Spring 的 application service + domain service
4. 清理剩余旧 Python 代码与过期文档
5. 视需要再评估是否引入外部消息队列

## 本地运行

```bash
npm run dev:spring
```

只启动 Spring 后端：

```bash
npm run api:spring:dev
```

当前项目脚本默认直接使用本机 Maven 配置与本地仓库。

默认开发入口已切换为 Spring：

```bash
npm run dev
```
