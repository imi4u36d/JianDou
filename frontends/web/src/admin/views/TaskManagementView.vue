<template>
  <section class="task-page">
    <div class="task-page__summary">
      <el-card v-for="item in summaryCards" :key="item.label" class="surface-card task-page__summary-card" shadow="never">
        <p>{{ item.label }}</p>
        <strong>{{ item.value }}</strong>
        <span>{{ item.note }}</span>
      </el-card>
    </div>

    <div v-if="initialLoading" class="task-page__summary">
      <div v-for="n in 4" :key="n" class="skeleton-card">
        <el-skeleton :rows="3" animated />
      </div>
    </div>

    <transition name="fade" mode="out-in">
      <div v-show="!initialLoading" key="content">
        <el-card class="surface-card" shadow="never">
      <template #header>
        <div class="task-page__toolbar">
          <div class="task-page__toolbar-spacer" aria-hidden="true"></div>
          <div class="task-page__toolbar-actions">
            <el-button plain @click="resetFilters">重置</el-button>
            <el-button
              plain
              type="danger"
              :disabled="selectedTerminableIds.length === 0 || actionLoading"
              :loading="actionLoading"
              @click="terminateSelected"
            >
              批量终止
            </el-button>
            <el-button :icon="Refresh" plain @click="loadTasks">刷新</el-button>
          </div>
        </div>
      </template>

      <el-form class="task-page__filters" inline @submit.prevent="loadTasks">
        <el-form-item label="关键词">
          <el-input v-model.trim="filters.q" clearable placeholder="任务或素材" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="filters.status" clearable placeholder="全部状态" style="width: 180px">
            <el-option v-for="item in statusOptions" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="排序">
          <el-select v-model="filters.sort" placeholder="排序方式" style="width: 180px">
            <el-option v-for="item in sortOptions" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
        </el-form-item>
        <el-form-item class="task-page__filters-action">
          <el-button :loading="refreshing" native-type="submit" type="primary">查询</el-button>
        </el-form-item>
      </el-form>

      <el-alert v-if="successMessage" :closable="false" class="task-page__alert" show-icon type="success" :title="successMessage" />

      <el-table
        v-loading="refreshing"
        :data="tasks"
        class="task-page__table"
        row-key="id"
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="48" />
        <el-table-column label="任务信息" min-width="260">
          <template #default="{ row }">
            <div class="task-page__task-cell">
              <strong>{{ row.title || "未命名任务" }}</strong>
              <span>{{ row.id }}</span>
              <span>{{ row.sourceFileName || "未记录素材文件" }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="创建人" min-width="180">
          <template #default="{ row }">
            <div class="task-page__owner-cell">
              <strong>{{ ownerLabel(row) }}</strong>
              <span>{{ row.ownerUsername || "未绑定账号" }}</span>
              <el-tag v-if="row.ownerRole === 'ADMIN'" effect="plain" size="small" type="warning">管理员</el-tag>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="状态" min-width="120">
          <template #default="{ row }">
            <div class="task-page__status-cell">
              <el-tag :type="statusTagType(row.status)" effect="light">{{ statusLabel(row.status) }}</el-tag>
              <span>{{ row.currentStage || "等待处理" }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="进度" min-width="180">
          <template #default="{ row }">
            <div class="task-page__progress-cell">
              <div class="task-page__progress-head">
                <strong>{{ row.progress ?? 0 }}%</strong>
                <span>{{ progressHint(row) }}</span>
              </div>
              <el-progress :percentage="row.progress ?? 0" :show-text="false" :stroke-width="8" />
            </div>
          </template>
        </el-table-column>
        <el-table-column label="任务参数" min-width="170">
          <template #default="{ row }">
            <div class="task-page__meta-cell">
              <span>{{ row.aspectRatio || "比例未记录" }}</span>
              <span>{{ durationLabel(row) }}</span>
              <span>重试 {{ row.retryCount ?? 0 }} 次</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="素材 / 结果" min-width="150">
          <template #default="{ row }">
            <div class="task-page__meta-cell">
              <span>素材 {{ row.sourceAssetCount ?? 0 }}</span>
              <span>成片 {{ row.completedOutputCount ?? 0 }}</span>
              <span>镜头 {{ renderedClipLabel(row) }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="创建时间" min-width="180">
          <template #default="{ row }">
            {{ formatDateTime(row.createdAt) }}
          </template>
        </el-table-column>
        <el-table-column label="更新时间" min-width="180">
          <template #default="{ row }">
            {{ formatDateTime(row.updatedAt) }}
          </template>
        </el-table-column>
        <el-table-column fixed="right" label="操作" min-width="120">
          <template #default="{ row }">
            <el-button
              v-if="terminableStatus(row.status)"
              link
              type="danger"
              :disabled="actionLoading"
              @click="terminateSingle(row)"
            >
              终止
            </el-button>
            <span v-else class="task-page__muted-action">-</span>
          </template>
        </el-table-column>
      </el-table>

      <div class="task-page__pagination">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :total="totalTasks"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          background
          @size-change="handleSizeChange"
          @current-change="handlePageChange"
        />
      </div>
    </el-card>
      </div>
    </transition>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { Refresh } from "@element-plus/icons-vue";
import { bulkTerminateAdminTasks, fetchAdminTasks, terminateAdminTask } from "@/admin/features/tasks/services/taskService";
import type { AdminTaskListItem, AdminTaskSortMode, TaskStatus } from "@/types";

const initialLoading = ref(true);
const refreshing = ref(false);
const actionLoading = ref(false);
const successMessage = ref("");
const tasks = ref<AdminTaskListItem[]>([]);
const selectedTasks = ref<AdminTaskListItem[]>([]);
const totalTasks = ref(0);
const currentPage = ref(1);
const pageSize = ref(20);
const filters = reactive({
  q: "",
  status: "" as TaskStatus | "",
  sort: "updated_desc" as AdminTaskSortMode
});

const statusOptions: Array<{ label: string; value: TaskStatus }> = [
  { label: "排队中", value: "PENDING" },
  { label: "已暂停", value: "PAUSED" },
  { label: "分析中", value: "ANALYZING" },
  { label: "编排中", value: "PLANNING" },
  { label: "渲染中", value: "RENDERING" },
  { label: "已完成", value: "COMPLETED" },
  { label: "失败", value: "FAILED" }
];

const sortOptions: Array<{ label: string; value: AdminTaskSortMode }> = [
  { label: "最近更新", value: "updated_desc" },
  { label: "最新创建", value: "created_desc" },
  { label: "进度优先", value: "progress_desc" },
  { label: "状态优先", value: "status_desc" }
];

const summaryCards = computed(() => [
  { label: "全部任务", value: totalTasks.value, note: "当前筛选" },
  { label: "当前页", value: tasks.value.length, note: `每页 ${pageSize.value}` },
]);

const selectedTerminableIds = computed(() => selectedTasks.value
  .filter((task) => terminableStatus(task.status))
  .map((task) => task.id));

function formatDateTime(value?: string | null) {
  if (!value) {
    return "未记录";
  }
  return new Date(value).toLocaleString();
}

function statusLabel(status: TaskStatus) {
  switch (status) {
    case "PENDING":
      return "排队中";
    case "PAUSED":
      return "已暂停";
    case "ANALYZING":
      return "分析中";
    case "PLANNING":
      return "编排中";
    case "RENDERING":
      return "渲染中";
    case "COMPLETED":
      return "已完成";
    case "FAILED":
      return "失败";
    default:
      return status;
  }
}

function statusTagType(status: TaskStatus) {
  switch (status) {
    case "COMPLETED":
      return "success";
    case "FAILED":
      return "danger";
    case "RENDERING":
    case "ANALYZING":
    case "PLANNING":
      return "warning";
    case "PAUSED":
      return "info";
    default:
      return "primary";
  }
}

function ownerLabel(task: AdminTaskListItem) {
  return task.ownerDisplayName || task.ownerUsername || (task.ownerUserId ? `用户 #${task.ownerUserId}` : "系统任务");
}

function durationLabel(task: AdminTaskListItem) {
  if (task.minDurationSeconds && task.maxDurationSeconds) {
    return `${task.minDurationSeconds}-${task.maxDurationSeconds} 秒`;
  }
  if (task.minDurationSeconds) {
    return `${task.minDurationSeconds} 秒`;
  }
  if (task.maxDurationSeconds) {
    return `${task.maxDurationSeconds} 秒`;
  }
  return "时长未记录";
}

function renderedClipLabel(task: AdminTaskListItem) {
  const rendered = task.renderedClipCount ?? 0;
  const planned = task.plannedClipCount ?? 0;
  if (planned > 0) {
    return `${rendered}/${planned}`;
  }
  return `${rendered}`;
}

function progressHint(task: AdminTaskListItem) {
  if (task.status === "FAILED") {
    return task.diagnosisHint || "任务执行失败";
  }
  if (task.status === "COMPLETED") {
    return `已产出 ${task.completedOutputCount ?? 0} 个结果`;
  }
  if (task.queuePosition && task.queuePosition > 0) {
    return `队列第 ${task.queuePosition} 位`;
  }
  return task.currentStage || "等待处理";
}

function terminableStatus(status: TaskStatus) {
  return ["PENDING", "ANALYZING", "PLANNING", "RENDERING"].includes(status);
}

function handleSelectionChange(selection: AdminTaskListItem[]) {
  selectedTasks.value = selection;
}

async function loadTasks() {
  refreshing.value = true;
  successMessage.value = "";
  try {
    const offset = (currentPage.value - 1) * pageSize.value;
    const result = await fetchAdminTasks({
      ...filters,
      offset,
      limit: pageSize.value,
    });
    tasks.value = result?.items ?? [];
    totalTasks.value = result?.total ?? 0;
    selectedTasks.value = selectedTasks.value.filter((selected) => tasks.value.some((task) => task.id === selected.id));
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : "读取任务列表失败");
  } finally {
    if (initialLoading.value) {
      initialLoading.value = false;
    }
    refreshing.value = false;
  }
}

function handlePageChange() {
  void loadTasks();
}

function handleSizeChange() {
  currentPage.value = 1;
  void loadTasks();
}

async function terminateSingle(task: AdminTaskListItem) {
  try {
    await ElMessageBox.confirm(
      `确认终止任务"${task.title || task.id}"吗？终止后任务会进入失败状态。`,
      "终止任务",
      {
        confirmButtonText: "终止",
        cancelButtonText: "取消",
        type: "warning"
      }
    );
    actionLoading.value = true;
    successMessage.value = "";
    await terminateAdminTask(task.id);
    selectedTasks.value = selectedTasks.value.filter((item) => item.id !== task.id);
    await loadTasks();
    successMessage.value = "任务已终止。";
    ElMessage.success("任务已终止");
  } catch (error) {
    if (error === "cancel") {
      return;
    }
    ElMessage.error(error instanceof Error ? error.message : "终止任务失败");
  } finally {
    actionLoading.value = false;
  }
}

async function terminateSelected() {
  const taskIds = selectedTerminableIds.value;
  if (taskIds.length === 0) {
    ElMessage.warning("请选择排队或执行中的任务");
    return;
  }
  try {
    await ElMessageBox.confirm(
      `确认终止选中的 ${taskIds.length} 个任务吗？已完成、失败或暂停任务不会被提交。`,
      "批量终止任务",
      {
        confirmButtonText: "批量终止",
        cancelButtonText: "取消",
        type: "warning"
      }
    );
    actionLoading.value = true;
    successMessage.value = "";
    const result = await bulkTerminateAdminTasks(taskIds);
    const failedIds = new Set(result.failed.map((item) => item.taskId));
    selectedTasks.value = result.failed.length
      ? selectedTasks.value.filter((task) => failedIds.has(task.id))
      : [];
    await loadTasks();
    successMessage.value = result.failed.length
      ? `已终止 ${result.succeededTaskIds.length} 个任务，${result.failed.length} 个未成功。`
      : `已终止 ${result.succeededTaskIds.length} 个任务。`;
    ElMessage.success(successMessage.value);
  } catch (error) {
    if (error === "cancel") {
      return;
    }
    ElMessage.error(error instanceof Error ? error.message : "批量终止任务失败");
  } finally {
    actionLoading.value = false;
  }
}

function resetFilters() {
  filters.q = "";
  filters.status = "";
  filters.sort = "updated_desc";
  currentPage.value = 1;
  void loadTasks();
}

onMounted(() => {
  void loadTasks();
});
</script>

<style scoped>
.task-page__summary {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
  margin-bottom: 20px;
}

.task-page > *,
.task-page .surface-card,
.task-page__summary,
.task-page__summary-card {
  min-width: 0;
  max-width: 100%;
}

.task-page__summary-card {
  border-radius: 24px;
}

.task-page__summary-card :deep(.el-card__body) {
  display: grid;
  gap: 8px;
  padding: 22px;
}

.task-page__summary-card p {
  margin: 0;
  color: var(--jd-text-soft);
  font-size: 0.88rem;
}

.task-page__summary-card strong {
  font-family: inherit;
  font-size: 1.9rem;
}

.task-page__summary-card span {
  color: var(--jd-text-soft);
  font-size: 0.92rem;
}

.task-page__toolbar {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 16px;
}

.task-page__toolbar-spacer {
  flex: 1 1 auto;
  min-width: 0;
}

.task-page__toolbar-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.task-page__filters {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 12px;
  margin-bottom: 12px;
  padding-bottom: 10px;
  border-bottom: 1px solid rgba(23, 32, 42, 0.06);
}

.task-page__filters-action {
  margin-left: auto;
}

.task-page__alert {
  margin-bottom: 16px;
}

.task-page__table {
  width: 100%;
}

.task-page__task-cell,
.task-page__owner-cell,
.task-page__status-cell,
.task-page__meta-cell,
.task-page__progress-cell {
  display: grid;
  gap: 6px;
}

.task-page__task-cell strong,
.task-page__owner-cell strong,
.task-page__progress-head strong {
  color: var(--jd-text);
}

.task-page__task-cell span,
.task-page__owner-cell span,
.task-page__status-cell span,
.task-page__meta-cell span,
.task-page__progress-head span {
  color: var(--jd-text-soft);
  font-size: 0.88rem;
}

.task-page__progress-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.task-page__muted-action {
  color: var(--jd-text-soft);
  display: inline-flex;
  justify-content: center;
  min-width: 32px;
  font-size: 0.86rem;
}

.task-page__pagination {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px solid rgba(23, 32, 42, 0.06);
}

@media (max-width: 1200px) {
  .task-page__summary {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 768px) {
  .task-page__summary {
    grid-template-columns: 1fr;
  }

  .task-page__toolbar {
    flex-direction: column;
    align-items: flex-start;
  }

  .task-page__toolbar-actions {
    width: 100%;
  }

  .task-page__toolbar-actions :deep(.el-button) {
    flex: 1;
  }
}
</style>
