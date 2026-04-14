# Spring API 架构草图

## 目标

在不改前端接口契约的前提下，把 Spring Boot 3 后端逐步演进成可替换当前 Python API 的正式实现。

## 当前分层

- `controller`
  - 对外暴露 `/api/v2` REST 接口
  - 只做参数接收、异常转换、返回 HTTP 结构
- `application`
  - `task/application/TaskApplicationService` 定义任务应用层接口
  - `generation/application/GenerationApplicationService` 定义生成运行接口
  - `upload/application/UploadApplicationService` 定义上传入口
- `service`
  - `TaskApplicationServiceImpl` 是当前任务域应用服务实现
  - `DefaultGenerationApplicationService` 和 `DefaultUploadApplicationService` 已把对应 controller 中的占位业务下沉
  - `RuntimeDescriptorService` 统一生成 runtime/health 描述
- `application/port`
  - 抽象持久化、聚合查询、队列、后续模型调用与存储网关
- `repository`
  - `TaskRepository` 定义仓储接口
  - `MybatisTaskRepository` 提供当前 MyBatis-Plus 持久化实现
- `domain`
  - 已开始映射 `TaskAggregate`、`TaskAttemptSnapshot`、`TaskStageRunSnapshot`、`TaskStatus`
- `persistence`
  - 已新增 `TaskRow`、`TaskAttemptRow`、`TaskStageRunRow`、`TaskStatusHistoryRow`
  - 为后续 JDBC/MyBatis 落库提供第一批表映射骨架
- `record / mapper`
  - `TaskRecord` 作为当前任务聚合的内存载体
  - `TaskViewMapper` 负责把内部对象映射成前端需要的响应结构

## 当前价值

- 控制器层与存储层开始解耦
- health、generation、upload 不再把主要占位业务直接写在 controller 中
- 应用层接口已经从具体内存实现中分离出来
- 后续接 MySQL 时可以直接新增 `JdbcTaskRepository` / `MyBatisTaskRepository`
- 后续如需外部消息队列，可以替换 `TaskQueuePort` 的实现，不需要重写控制器
- 前端依然可以继续用现有 `/api/v2` 接口工作

## 下一阶段建议

1. 把 `TaskRecord` 替换成基于 `TaskRow + detail rows` 的正式聚合读取
2. 新增 `TaskExecutionCoordinator`，把 claim/attempt/dispatch 从 `TaskApplicationServiceImpl` 中继续抽离
3. 在 `task/infrastructure` 落地 `TaskPersistencePort` 与 `TaskAggregateQueryPort`
4. 接 MySQL 后保留当前 `TaskViewMapper`，避免前端响应结构抖动
5. 继续补恢复治理、素材清理与更细粒度监控

## Runtime 与 Worker 映射

| Python 简写 | Spring 对应 | 状态 | 说明 |
| --- | --- | --- | --- |
| `packages/pipeline/jiandou_pipeline/runtime.py::build_runtime` | Spring `@Configuration` + `RuntimeDescriptorService` | 已接管 | `RuntimeDescriptorService` 已接管 health runtime payload，旧 Python runtime 可下线。|
| `packages/pipeline/jiandou_pipeline/service.py` | `task/application/TaskApplicationService` + `TaskApplicationServiceImpl` | 已接管 | 应用服务接口已承接任务主数据与聚合查询，后续继续增强治理能力。|
| `packages/pipeline/jiandou_pipeline/service.py::_dispatch_task` / `worker.py::TaskWorker` | `task/application/port/TaskQueuePort` + `TaskQueueCoordinator` + `TaskExecutionCoordinator` | 已接管 | 入队/出队、claim、attempt、dispatch 已收敛到 Spring。|
| `packages/pipeline/jiandou_pipeline/worker.py` | `TaskWorkerRunner` | 已接管 | Spring 已承担队列消费、心跳、trace、多镜头执行与结果回写。|
| `packages/db/jiandou_db/models.py` + `packages/db/sql/mysql_init_schema.sql` | `task/domain` + `task/persistence` | 已接管主链 | 领域模型和主链表映射已由 MyBatis-Plus 兑现。|

## 当前迁移里程碑

- 控制器层已对外提供 health、uploads、tasks、admin、generation 五大类接口，前端无感知。  
- `TaskApplicationService` 抽象完成，`TaskPersistencePort` / `TaskAggregateQueryPort` / `TaskQueuePort` 已定义，便于逐步替换基础设施实现。  
- `TaskQueueCoordinator` 已把队列占位逻辑从 `TaskApplicationServiceImpl` 中抽出来。  
- `RuntimeDescriptorService`、`DefaultGenerationApplicationService`、`DefaultUploadApplicationService` 已把 controller 中的主要占位业务下沉。  
- `task/domain` 与 `task/persistence` 里聚合、尝试、阶段、状态历史第一批模型已经跟 Python 表/字段对齐。  
- 当前主链已切到 MySQL；后续重点转为恢复治理、监控可观测性与历史 Python 代码清理。
