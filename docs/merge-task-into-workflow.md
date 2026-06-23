# 快速任务融合到工作流系统 — 实施计划

> 创建时间: 2026-06-23
> 状态: 待执行

## Context

当前 JianDou 存在两套并行的生成系统：**快速任务**（BizTask + 队列 Worker 自动执行）和**阶段工作流**（BizStageWorkflow + 用户手动逐步执行）。两者数据模型、服务层、前端 UI 完全独立，维护成本高，用户也需理解两种概念。

**目标**：将快速任务融合到工作流系统中，使一切皆为工作流，区别仅在于执行模式：
- **自动模式**（替代快速任务）：创建后自动执行全部阶段，可随时暂停，暂停后可手动干预再继续
- **手动模式**（当前工作流）：逐阶段手动触发，用户选版本

---

## Phase 1: 后端基础设施（Week 1-2）

### 1.1 数据模型变更

**文件**: `backend/models/workflow.py`

在 `BizStageWorkflow` 表上新增字段：

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `execution_mode` | `String(32) NOT NULL` | `"manual"` | `"auto"` / `"manual"` |
| `auto_pilot_state` | `String(32) NOT NULL` | `"idle"` | `idle` / `running` / `paused` / `failed` / `completed` |
| `auto_pilot_next_stage` | `String(64) NOT NULL` | `""` | 当前执行到哪一步，如 `"keyframe:3"`, `"finalize"` |
| `auto_pilot_error_message` | `Text NOT NULL` | `""` | 失败时的错误信息 |
| `auto_pilot_started_at` | `String(32) NOT NULL` | `""` | 最近一次启动/恢复时间 |
| `auto_pilot_paused_at` | `String(32) NOT NULL` | `""` | 最近一次暂停时间 |

新增 CHECK 约束：
```sql
auto_pilot_state in ('idle', 'running', 'paused', 'failed', 'completed')
execution_mode in ('auto', 'manual')
status in ('DRAFT', 'READY', 'RUNNING', 'PAUSED', 'COMPLETED', 'FAILED')  -- 扩展
```

新增索引：`ix_biz_stage_workflows_auto_pilot` on `(auto_pilot_state, is_deleted)`

**文件**: `backend/domain/enums.py`

新增枚举：
```python
class AutoPilotState(StrEnum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    FAILED = "failed"
    COMPLETED = "completed"

class ExecutionMode(StrEnum):
    AUTO = "auto"
    MANUAL = "manual"
```

扩展 `WorkflowStatus`：新增 `RUNNING`, `PAUSED`

**迁移文件**: 新建 Alembic migration 添加以上列和约束。

### 1.2 AutoPilot 核心服务

**新文件**: `backend/services/workflow_auto_pilot.py`

```python
class WorkflowAutoPilot:
    """
    无状态自动执行引擎。在以下时机被调用：
    - 创建 auto 模式工作流时
    - 用户点击"恢复"时
    每次调用顺序执行阶段，直到暂停/失败/完成。
    """

    def __init__(self, db: AsyncSession, workflow_service: WorkflowService):
        self.db = db
        self.wf_service = workflow_service

    async def run(self, workflow_id: str, owner_user_id: int) -> AutoPilotResult:
        """主循环：顺序执行阶段直到暂停/失败/完成"""

    def _compute_next_step(self, wf, versions) -> AutoPilotStep:
        """纯函数：根据当前版本状态决定下一步操作"""

    async def _execute_step(self, step, workflow_id, owner_user_id):
        """执行一步，直接调用 WorkflowService 现有方法"""

    async def _check_pause(self, wf) -> bool:
        """从 DB 重读工作流，检查是否有人请求了暂停"""

    async def _auto_select_first_version(self, wf, stage_type, clip_index) -> bool:
        """自动选择该阶段第一个完成的版本"""
```

**执行链算法**（`_compute_next_step`）：

```
1. 没有分镜版本 → GenerateStoryboard
2. 有分镜版本但未选择 → SelectFirstStoryboard
3. 遍历角色：缺少角色设定图 → GenerateKeyframe(clip_index=1001,1002,...)
4. 遍历镜头：缺少关键帧 → GenerateKeyframe(clip_index=1,2,3,...)
5. 遍历镜头：缺少视频 → GenerateVideo(clip_index=1,2,3,...)
6. 所有视频就绪 → Finalize
7. 完成 → Complete
```

**关键设计**：AutoPilot **不复制任何生成逻辑**，它纯粹是编排层，直接调用现有方法：

| AutoPilotStep | 调用的 WorkflowService 方法 |
|---|---|
| `generate_storyboard` | `generate_storyboard(workflow_id, owner_user_id)` |
| `select_storyboard` | `select_storyboard(workflow_id, version_id, owner_user_id)` |
| `generate_keyframe(n)` | `generate_keyframe(workflow_id, clip_index, owner_user_id)` |
| `generate_video(n)` | `generate_video(workflow_id, clip_index, owner_user_id)` |
| `finalize` | `finalize_workflow(workflow_id, owner_user_id)` |

**暂停机制**：每个阶段执行完毕后，从 DB 重读工作流状态。如果 `auto_pilot_state` 已被并发 API 调用设为 `"paused"`，则退出循环。暂停只在阶段边界生效，不中断正在运行的生成。

**错误处理**：异常被捕获 → `auto_pilot_state = "failed"` → 记录错误信息 → 用户可手动修复后点"恢复"。

**安全限制**：`max_iterations = 200`，超时 2 小时自动暂停。

**视频异步等待**：`generate_video` 返回后视频可能还在异步生成中。AutoPilot 需要轮询等待视频完成（复用 `_refresh_video_versions` 的逻辑），然后再继续下一个 clip。

### 1.3 API 变更

**文件**: `backend/routers/workflows.py`

新增 4 个端点：

```
POST /api/v3/workflows/{id}/auto-pilot/start     — 启动自动执行
POST /api/v3/workflows/{id}/auto-pilot/pause      — 暂停（设置标记，下次阶段边界生效）
POST /api/v3/workflows/{id}/auto-pilot/resume     — 恢复自动执行
POST /api/v3/workflows/{id}/auto-pilot/terminate  — 永久停止，切换为手动模式
```

修改 `POST /api/v3/workflows`（创建工作流）：
- `CreateWorkflowRequest` 新增 `execution_mode` 字段（默认 `"manual"`）
- 如果 `execution_mode === "auto"`，创建后将 job 入队到 auto-pilot 队列

**文件**: `backend/schemas/workflow.py`

- `CreateWorkflowRequest` 新增 `execution_mode: str = "manual"`
- `WorkflowDetailResponse` 新增：`execution_mode`, `auto_pilot_state`, `auto_pilot_next_stage`, `auto_pilot_error_message`, `auto_pilot_started_at`, `auto_pilot_paused_at`
- `WorkflowSummaryResponse` 新增：`execution_mode`, `auto_pilot_state`

**AutoPilot 队列 Worker 运行方案**：

复用现有队列基础设施，新建一个 AutoPilot Worker 类型：

```python
# backend/services/auto_pilot_worker_runner.py（新文件）
class AutoPilotWorkerRunner:
    """
    类似 TaskWorkerRunner，但专门处理 AutoPilot 任务。
    轮询队列，领取 auto-pilot job，调用 WorkflowAutoPilot.run()。
    """
    def __init__(self, task_queue_port, workflow_service_factory, ...):
        ...

    async def _poll_once(self):
        job = await self._queue_port.claim_next(self._worker_id)
        if job:
            auto_pilot = WorkflowAutoPilot(db, wf_service)
            await auto_pilot.run(job.workflow_id, job.owner_user_id)
```

**工作流程**：
1. 创建 auto 模式工作流时 → 将 `workflow_id` 入队到 `auto_pilot` 队列
2. AutoPilotWorkerRunner 轮询队列 → 领取 job → 实例化 `WorkflowAutoPilot` → 调用 `run()`
3. 暂停后恢复时 → 重新入队
4. Worker 维护心跳，stale recovery 自动重新入队

**优势**：进程重启时不丢失任务、支持并发控制（`worker_concurrency`）、复用 stale claim recovery 机制。

**队列端口扩展**：在 `TaskQueuePort` 协议上新增 `auto_pilot` 队列名，或复用同一个队列但通过 job type 区分。推荐新建独立队列以隔离关注点。

**Worker 实例化**：在 `backend/main.py` 的 lifespan 中，与 `TaskWorkerRunner` 并行启动 `AutoPilotWorkerRunner`：

```python
@asynccontextmanager
async def lifespan(app):
    # ... existing startup ...
    auto_pilot_runner = AutoPilotWorkerRunner(
        queue_port=auto_pilot_queue_port,
        wf_service_factory=create_wf_service,
        config=auto_pilot_worker_config,
    )
    await auto_pilot_runner.start()
    yield
    await auto_pilot_runner.stop()
```

### 1.4 旧系统处理

以下代码**保留但标记为 deprecated**，不立即删除：

| 组件 | 文件 | 处理 |
|------|------|------|
| `TaskCommandService` | `backend/services/task_command_service.py` | 保留，加 `@deprecated` 注释 |
| `TaskWorkerRunner` | `backend/services/task_worker_runner.py` | 保留结构，作为 `AutoPilotWorkerRunner` 的参考模板 |
| `TaskExecutionCoordinator` | `backend/services/task_execution_coordinator.py` | 保留队列管理逻辑，AutoPilot 队列复用类似模式 |
| `POST /api/v3/tasks/*` | `backend/routers/tasks.py` | 保留端点但标记 deprecated |
| `BizTask` 等模型 | `backend/models/task.py` | 保留表结构，加注释 |

**前端不再展示存量 BizTask**：`useUnifiedList` 仅加载 workflows，不加载 tasks。旧 API 端点保留以便外部调用者过渡，但前端完全切换到 workflows。

---

## Phase 2: 前端改造（Week 3）

### 2.1 创建对话框

**文件**: `frontends/web/src/views/unified/components/CreateTaskDialog.vue`

- 移除"快速任务"/"阶段工作流"的双模式切换
- 统一为工作流创建表单，新增**执行模式**切换：
  - **自动执行**（默认）：创建后自动跑完全流程
  - **手动执行**：逐步手动控制
- 当选择"自动执行"时显示提示："创建后将自动执行分镜→关键帧→视频全流程，可随时暂停修改。"

### 2.2 详情面板统一

**文件**: `frontends/web/src/views/unified/components/WorkflowDetailPanel.vue`

**同一个 WorkflowDetailPanel 用于两种模式**，通过条件渲染控制栏：

**自动模式控制栏**（`execution_mode === "auto"` 时显示）：

```
┌──────────────────────────────────────────────────────┐
│ 🟢 自动执行中...  下一步: 生成镜头3关键帧              │
│ [⏸ 暂停]  [⏹ 终止]                                   │
└──────────────────────────────────────────────────────┘
```

暂停/失败状态：
```
┌──────────────────────────────────────────────────────┐
│ 🟡 已暂停                                             │
│ [▶ 继续自动执行]  [⏹ 切换为手动模式]                   │
│                                                       │
│  ↓ 下方显示完整的手动控制（生成/选择/调整按钮全部激活）   │
└──────────────────────────────────────────────────────┘
```

失败状态：
```
┌──────────────────────────────────────────────────────┐
│ 🔴 自动执行失败: 视频模型返回错误                       │
│ [🔄 重试]  [✏ 手动修复后继续]                          │
└──────────────────────────────────────────────────────┘
```

**手动模式**：无控制栏，保持现有的逐阶段手动操作。

**阶段画布完全复用**：分镜版本 tabs、角色卡片、关键帧时间线、视频播放器、最终合成——所有 UI 组件在两种模式下完全相同。

### 2.3 新增 Composable

**新文件**: `frontends/web/src/composables/workflow/useAutoPilot.ts`

```typescript
export function useAutoPilot(workflowId: Ref<string>) {
  // 状态
  const autoPilotState = ref<string>("idle")
  const nextStage = ref<string>("")
  const errorMessage = ref<string>("")
  const busy = ref(false)

  // 操作
  async function startAutoPilot() { ... }
  async function pauseAutoPilot() { ... }
  async function resumeAutoPilot() { ... }
  async function terminateAutoPilot() { ... }

  // 轮询（auto 模式下 2 秒间隔获取最新状态）
  function startPolling() { ... }
  function stopPolling() { ... }

  return { autoPilotState, nextStage, errorMessage, busy,
           startAutoPilot, pauseAutoPilot, resumeAutoPilot, terminateAutoPilot,
           startPolling, stopPolling }
}
```

### 2.4 新增 API 函数

**文件**: `frontends/web/src/api/workflows.ts`

```typescript
export function startAutoPilot(id: string) { return postJson(`/workflows/${id}/auto-pilot/start`) }
export function pauseAutoPilot(id: string) { return postJson(`/workflows/${id}/auto-pilot/pause`) }
export function resumeAutoPilot(id: string) { return postJson(`/workflows/${id}/auto-pilot/resume`) }
export function terminateAutoPilot(id: string) { return postJson(`/workflows/${id}/auto-pilot/terminate`) }
```

### 2.5 列表简化

**文件**: `frontends/web/src/composables/unified/useUnifiedList.ts`

- 仅加载 workflows（`fetchWorkflows()`），**不再加载 tasks**
- `UnifiedListItem` 新增 `executionMode` 和 `autoPilotState` 字段
- 移除 `UnifiedKindFilter`（不再有 task/workflow 之分）

**文件**: `frontends/web/src/views/UnifiedTaskView.vue`

- 右侧详情区统一渲染 `WorkflowDetailPanel`
- 移除 `TaskDetailPanel` 的条件分支

---

## Phase 3: 清理与废弃（Week 4）

### 3.1 前端完全切换

- `useUnifiedList` 仅调用 `fetchWorkflows()`，不再调用 `fetchTasks()`
- `UnifiedTaskView` 不再区分 `TaskDetailPanel` / `WorkflowDetailPanel`，统一使用 `WorkflowDetailPanel`
- `CreateTaskDialog` 不再有"快速任务"模式选项

### 3.2 旧 API 废弃

- `POST /api/v3/tasks/*` 端点保留但加 `Deprecation` 响应头
- 90 天后可归档 BizTask 相关表

---

## 验证方案

### 单元测试
- `WorkflowAutoPilot._compute_next_step` 是纯函数，用各种版本组合测试下一步判断
- 测试暂停边界：运行中请求暂停 → 应在当前阶段完成后停止

### 集成测试
- 创建 auto 模式工作流 → 验证 AutoPilot 自动完成所有阶段
- 创建后暂停 → 验证状态正确
- 暂停后手动生成新版本 → 恢复 → 验证 AutoPilot 跳过已完成的阶段

### E2E 手动验证
1. 创建"自动执行"工作流 → 观察分镜→关键帧→视频依次自动生成
2. 在关键帧阶段暂停 → 对某个镜头重新生成并选择满意的版本 → 点"继续" → 验证后续视频使用新选的关键帧
3. 创建"手动执行"工作流 → 验证与现有工作流行为一致
4. 在统一列表中验证两种模式的显示和过滤

---

## 关键文件清单

| 文件 | 变更类型 |
|------|---------|
| `backend/models/workflow.py` | 修改：新增 6 个字段 + 约束 |
| `backend/domain/enums.py` | 修改：新增枚举 |
| `backend/services/workflow_auto_pilot.py` | **新建**：AutoPilot 核心编排服务 |
| `backend/services/auto_pilot_worker_runner.py` | **新建**：AutoPilot 队列 Worker |
| `backend/services/workflow_service.py` | 修改：`create_workflow` 接受 `execution_mode` |
| `backend/routers/workflows.py` | 修改：新增 4 个 auto-pilot 端点 |
| `backend/schemas/workflow.py` | 修改：新增字段 |
| `backend/main.py` | 修改：lifespan 中启动 AutoPilotWorkerRunner |
| `migrations/versions/xxx_merge_task_into_workflow.py` | **新建**：数据迁移 |
| `frontends/web/src/views/unified/components/CreateTaskDialog.vue` | 修改：统一创建 + 模式切换 |
| `frontends/web/src/views/unified/components/WorkflowDetailPanel.vue` | 修改：新增 AutoPilot 控制栏 |
| `frontends/web/src/composables/workflow/useAutoPilot.ts` | **新建**：AutoPilot 状态管理 |
| `frontends/web/src/api/workflows.ts` | 修改：新增 4 个 API 函数 |
| `frontends/web/src/composables/unified/useUnifiedList.ts` | 修改：仅加载 workflows |
| `frontends/web/src/views/UnifiedTaskView.vue` | 修改：统一详情面板 |
| `frontends/web/src/types/unified-task.ts` | 修改：新增字段 |
