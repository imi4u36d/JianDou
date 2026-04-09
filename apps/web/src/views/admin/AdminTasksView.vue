<template>
  <section class="admin-page admin-tasks-view">
    <div class="admin-panel px-5 py-5">
      <div class="flex flex-wrap items-start justify-between gap-4">
        <div class="admin-heading-block">
          <p class="admin-eyebrow">Task Ops</p>
          <h2 class="admin-title">任务管理</h2>
          <p class="admin-subtitle">标准数据表管理：筛选、批量操作、状态巡检、详情跳转。</p>
        </div>
        <div class="admin-action-row">
          <RouterLink to="/tasks/new" :class="primaryButtonClass">新建任务</RouterLink>
          <button :class="secondaryButtonClass" type="button" @click="refreshAll">刷新</button>
        </div>
      </div>
    </div>

    <div class="grid gap-3 sm:grid-cols-2 xl:grid-cols-6">
      <article
        v-for="card in summaryCards"
        :key="card.key"
        class="admin-metric-card"
      >
        <p class="admin-metric-label">{{ card.label }}</p>
        <p class="admin-metric-value">{{ card.value }}</p>
        <p class="admin-metric-hint">{{ card.hint }}</p>
      </article>
    </div>

    <section class="admin-panel p-5">
      <div class="grid gap-3 xl:grid-cols-[minmax(0,1.2fr)_repeat(2,minmax(0,0.72fr))]">
        <label class="grid gap-1 text-xs text-slate-600">
          搜索
          <input
            v-model="searchText"
            class="admin-field"
            placeholder="搜索标题、文件名、比例"
            type="search"
          />
        </label>
        <label class="grid gap-1 text-xs text-slate-600">
          状态
          <select v-model="statusFilter" class="admin-field">
            <option value="all">全部状态</option>
            <option value="PENDING">排队中</option>
            <option value="PAUSED">已暂停</option>
            <option value="ANALYZING">分析中</option>
            <option value="PLANNING">编排中</option>
            <option value="RENDERING">渲染中</option>
            <option value="COMPLETED">已完成</option>
            <option value="FAILED">失败</option>
          </select>
        </label>
        <label class="grid gap-1 text-xs text-slate-600">
          排序
          <select v-model="sortMode" class="admin-field">
            <option value="updated_desc">最近更新</option>
            <option value="created_desc">最新创建</option>
            <option value="progress_desc">进度优先</option>
            <option value="status_desc">状态优先</option>
          </select>
        </label>
      </div>

      <div class="mt-4 flex flex-wrap items-center gap-2 text-sm">
        <button :class="warningButtonClass" :disabled="selectedIds.length === 0 || actionLoading" type="button" @click="handleBulkRetry">
          批量重试
        </button>
        <button :class="dangerButtonClass" :disabled="selectedIds.length === 0 || actionLoading" type="button" @click="handleBulkDelete">
          批量删除
        </button>
        <button :class="ghostButtonClass" type="button" @click="toggleSelectVisible">
          {{ allVisibleSelected ? "取消选择可见项" : "选择可见项" }}
        </button>
        <button :class="ghostButtonClass" type="button" @click="clearSelection">
          清空选择
        </button>
        <span class="admin-chip">已选 {{ selectedIds.length }} 条</span>
        <span class="admin-chip">可见 {{ sortedTasks.length }} / {{ tasks.length }}</span>
      </div>
    </section>

    <div v-if="errorMessage" class="admin-alert-error">
      {{ errorMessage }}
    </div>
    <div
      v-else-if="actionMessage"
      :class="actionMessageTone === 'warn' ? 'admin-alert-warn' : 'admin-alert-success'"
    >
      {{ actionMessage }}
    </div>

    <section class="admin-panel overflow-hidden">
      <div class="admin-panel-header">
        <div>
          <h3 class="text-base font-semibold text-slate-900">任务数据表</h3>
          <p class="mt-1 text-sm text-slate-600">支持批量运维与单任务快速处置。</p>
        </div>
        <span class="admin-chip">{{ summaryFooterLabel }}</span>
      </div>

      <div v-if="loading" class="px-4 py-8 text-sm text-slate-500">正在读取任务...</div>
      <div v-else-if="sortedTasks.length === 0" class="admin-empty m-5">当前没有符合筛选条件的任务。</div>
      <div v-else class="admin-table-wrap m-5">
        <table class="admin-table min-w-[1400px]">
          <thead>
            <tr>
              <th><input :checked="allVisibleSelected" type="checkbox" @change="toggleSelectVisible" /></th>
              <th>任务</th>
              <th>状态</th>
              <th>文本输入</th>
              <th>进度</th>
              <th>更新时间</th>
              <th class="text-right">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="task in sortedTasks"
              :key="task.id"
              :class="rowToneClass(task.status)"
            >
              <td>
                <input :checked="selectedIds.includes(task.id)" type="checkbox" @change="toggleSelected(task.id)" />
              </td>
              <td>
                <p class="font-medium text-slate-900">{{ task.title }}</p>
                <p class="mt-0.5 text-xs text-slate-500">{{ task.sourceFileName }}</p>
                <div class="mt-1 flex flex-wrap gap-1 text-xs text-slate-600">
                  <span>{{ task.aspectRatio }}</span>
                  <span>·</span>
                  <span>{{ task.minDurationSeconds }}-{{ task.maxDurationSeconds }} 秒</span>
                </div>
              </td>
              <td>
                <span :class="statusPillClass(task.status)" class="inline-flex rounded px-2 py-0.5 text-xs font-medium">
                  {{ statusLabel(task.status) }}
                </span>
                <p class="mt-1 text-xs text-slate-500">重试 {{ task.retryCount ?? 0 }} 次</p>
              </td>
              <td>
                <p class="text-sm text-slate-700">{{ semanticHint(task) }}</p>
              </td>
              <td>
                <p class="font-medium text-slate-900">{{ task.progress }}%</p>
                <div class="mt-1 h-1.5 overflow-hidden rounded-full bg-slate-200">
                  <div class="h-full rounded-full" :class="progressBarClass(task.status)" :style="{ width: `${task.progress}%` }"></div>
                </div>
                <p class="mt-1 text-xs text-slate-500">{{ progressLabel(task) }}</p>
              </td>
              <td>
                <p class="text-sm text-slate-800">{{ formatShortDate(task.updatedAt) }}</p>
                <p class="mt-0.5 text-xs text-slate-500">创建 {{ formatShortDate(task.createdAt) }}</p>
              </td>
              <td class="text-right">
                <div class="flex flex-wrap justify-end gap-1.5">
                  <RouterLink :to="`/admin/tasks/${task.id}`" class="admin-btn-secondary admin-btn-sm">详情</RouterLink>
                  <button
                    v-if="task.status === 'FAILED'"
                    :class="warningButtonClassSm"
                    :disabled="actionLoading"
                    type="button"
                    @click="retrySingle(task.id)"
                  >
                    重试
                  </button>
                  <button
                    :class="dangerButtonClassSm"
                    :disabled="actionLoading || runningStatus(task.status)"
                    type="button"
                    @click="deleteSingle(task.id, task.title)"
                  >
                    删除
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { bulkDeleteAdminTasks, bulkRetryAdminTasks, deleteAdminTask, fetchAdminTasks, retryAdminTask } from "@/api/admin";
import { usePolling } from "@/composables/usePolling";
import type { TaskListItem, TaskStatus } from "@/types";

const tasks = ref<TaskListItem[]>([]);
const loading = ref(true);
const actionLoading = ref(false);
const errorMessage = ref("");
const actionMessage = ref("");
const actionMessageTone = ref<"success" | "warn">("success");
const searchText = ref("");
const statusFilter = ref<TaskStatus | "all">("all");
const sortMode = ref<"updated_desc" | "created_desc" | "progress_desc" | "status_desc">("updated_desc");
const selectedIds = ref<string[]>([]);
let refreshDebounceTimer: ReturnType<typeof setTimeout> | null = null;

const primaryButtonClass = "admin-btn-primary";
const secondaryButtonClass = "admin-btn-secondary";
const ghostButtonClass = "admin-btn-ghost";
const warningButtonClass = "admin-btn-warning";
const dangerButtonClass = "admin-btn-danger";
const warningButtonClassSm = "admin-btn-warning admin-btn-sm";
const dangerButtonClassSm = "admin-btn-danger admin-btn-sm";

const filteredTasks = computed(() => {
  const keyword = searchText.value.trim().toLowerCase();
  return tasks.value.filter((task) => {
    if (statusFilter.value !== "all" && task.status !== statusFilter.value) {
      return false;
    }
    if (!keyword) {
      return true;
    }
    return [task.title, task.sourceFileName, task.aspectRatio].join(" ").toLowerCase().includes(keyword);
  });
});

const sortedTasks = computed(() => {
  const items = [...filteredTasks.value];
  if (sortMode.value === "created_desc") {
    return items.sort((left, right) => new Date(right.createdAt).getTime() - new Date(left.createdAt).getTime());
  }
  if (sortMode.value === "progress_desc") {
    return items.sort((left, right) => (right.progress ?? 0) - (left.progress ?? 0));
  }
  if (sortMode.value === "status_desc") {
    return items.sort((left, right) => String(left.status).localeCompare(String(right.status)));
  }
  return items.sort((left, right) => new Date(right.updatedAt).getTime() - new Date(left.updatedAt).getTime());
});

const allVisibleSelected = computed(() => sortedTasks.value.length > 0 && sortedTasks.value.every((task) => selectedIds.value.includes(task.id)));

const summaryCards = computed(() => {
  const total = tasks.value.length;
  const running = tasks.value.filter((task) => runningStatus(task.status)).length;
  const failed = tasks.value.filter((task) => task.status === "FAILED").length;
  const semantic = tasks.value.filter((task) => task.hasTranscript || task.hasTimedTranscript).length;
  const timedSemantic = tasks.value.filter((task) => task.hasTimedTranscript).length;
  const average = total ? Math.round(tasks.value.reduce((sum, task) => sum + (task.progress ?? 0), 0) / total) : 0;

  return [
    { key: "total", label: "任务总量", value: total, hint: "全部任务" },
    { key: "running", label: "运行中", value: running, hint: "分析/编排/渲染阶段" },
    { key: "failed", label: "失败任务", value: failed, hint: "需要人工处理" },
    { key: "semantic", label: "文本输入任务", value: semantic, hint: "带字幕或文本输入" },
    { key: "timed", label: "时间轴字幕", value: timedSemantic, hint: "切点准确度更高" },
    { key: "average", label: "平均进度", value: `${average}%`, hint: "任务池整体推进" },
  ];
});

const summaryFooterLabel = computed(() => {
  if (loading.value) {
    return "正在同步任务...";
  }
  return `${sortedTasks.value.length} / ${tasks.value.length} 可见`;
});

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

function statusPillClass(status: TaskStatus) {
  switch (status) {
    case "PENDING":
      return "bg-slate-100 text-slate-700";
    case "PAUSED":
      return "bg-amber-100 text-amber-700";
    case "ANALYZING":
      return "bg-sky-100 text-sky-700";
    case "PLANNING":
      return "bg-cyan-100 text-cyan-700";
    case "RENDERING":
      return "bg-amber-100 text-amber-700";
    case "COMPLETED":
      return "bg-emerald-100 text-emerald-700";
    case "FAILED":
      return "bg-rose-100 text-rose-700";
    default:
      return "bg-slate-100 text-slate-700";
  }
}

function progressBarClass(status: TaskStatus) {
  if (status === "FAILED") {
    return "bg-rose-400";
  }
  if (status === "COMPLETED") {
    return "bg-emerald-500";
  }
  if (status === "RENDERING") {
    return "bg-amber-500";
  }
  if (status === "PAUSED") {
    return "bg-amber-400";
  }
  return "bg-sky-500";
}

function rowToneClass(status: TaskStatus) {
  if (status === "FAILED") {
    return "bg-rose-50/40";
  }
  if (status === "RENDERING") {
    return "bg-amber-50/30";
  }
  if (status === "PAUSED") {
    return "bg-amber-50/25";
  }
  return "";
}

function semanticHint(task: TaskListItem) {
  if (task.hasTimedTranscript) {
    return "时间轴字幕";
  }
  if (task.hasTranscript) {
    return "文本输入";
  }
  return "无文本输入";
}

function progressLabel(task: TaskListItem) {
  if (task.status === "FAILED") {
    return "任务异常";
  }
  if (task.status === "COMPLETED") {
    return "已完成";
  }
  if (task.status === "RENDERING") {
    return "渲染中";
  }
  if (task.status === "PAUSED") {
    return "已暂停";
  }
  if (task.status === "PLANNING") {
    return "编排中";
  }
  if (task.status === "ANALYZING") {
    return "分析中";
  }
  return "待处理";
}

function formatShortDate(value: string) {
  return new Date(value).toLocaleString();
}

function runningStatus(status: TaskStatus) {
  return status === "ANALYZING" || status === "PLANNING" || status === "RENDERING";
}

function toggleSelected(taskId: string) {
  const index = selectedIds.value.indexOf(taskId);
  if (index >= 0) {
    selectedIds.value.splice(index, 1);
    return;
  }
  selectedIds.value.push(taskId);
}

function toggleSelectVisible() {
  if (allVisibleSelected.value) {
    selectedIds.value = selectedIds.value.filter((id) => !sortedTasks.value.some((task) => task.id === id));
    return;
  }

  const merged = new Set(selectedIds.value);
  sortedTasks.value.forEach((task) => merged.add(task.id));
  selectedIds.value = Array.from(merged);
}

function clearSelection() {
  selectedIds.value = [];
}

async function loadTasks() {
  tasks.value = await fetchAdminTasks({
    q: searchText.value.trim() || undefined,
    status: statusFilter.value,
  });
}

async function refreshAll() {
  errorMessage.value = "";
  loading.value = true;
  try {
    await loadTasks();
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "读取任务失败";
  } finally {
    loading.value = false;
  }
}

async function retrySingle(taskId: string) {
  actionLoading.value = true;
  errorMessage.value = "";
  actionMessage.value = "";
  try {
    await retryAdminTask(taskId);
    actionMessage.value = "任务已提交重试。";
    actionMessageTone.value = "success";
    await refreshAll();
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "重试失败";
  } finally {
    actionLoading.value = false;
  }
}

async function deleteSingle(taskId: string, title: string) {
  if (!window.confirm(`确认删除任务“${title}”吗？`)) {
    return;
  }
  actionLoading.value = true;
  errorMessage.value = "";
  actionMessage.value = "";
  try {
    await deleteAdminTask(taskId);
    selectedIds.value = selectedIds.value.filter((id) => id !== taskId);
    actionMessage.value = "任务已删除。";
    actionMessageTone.value = "success";
    await refreshAll();
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "删除失败";
  } finally {
    actionLoading.value = false;
  }
}

async function handleBulkRetry() {
  if (selectedIds.value.length === 0) {
    return;
  }
  actionLoading.value = true;
  errorMessage.value = "";
  actionMessage.value = "";
  try {
    const result = await bulkRetryAdminTasks(selectedIds.value);
    const failedIds = new Set(result.failed.map((item) => item.taskId));
    selectedIds.value = result.failed.length
      ? selectedIds.value.filter((id) => failedIds.has(id))
      : [];
    if (result.failed.length) {
      actionMessage.value = `已重试 ${result.succeededTaskIds.length} 条，${result.failed.length} 条未成功：${result.failed
        .slice(0, 3)
        .map((item) => `${item.taskId}（${item.reason}）`)
        .join("；")}`;
      actionMessageTone.value = "warn";
    } else {
      actionMessage.value = `已批量重试 ${result.succeededTaskIds.length} 条任务。`;
      actionMessageTone.value = "success";
    }
    await refreshAll();
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "批量重试失败";
  } finally {
    actionLoading.value = false;
  }
}

async function handleBulkDelete() {
  if (selectedIds.value.length === 0) {
    return;
  }
  if (!window.confirm(`确认删除选中的 ${selectedIds.value.length} 个任务吗？`)) {
    return;
  }
  actionLoading.value = true;
  errorMessage.value = "";
  actionMessage.value = "";
  try {
    const result = await bulkDeleteAdminTasks(selectedIds.value);
    const failedIds = new Set(result.failed.map((item) => item.taskId));
    selectedIds.value = result.failed.length
      ? selectedIds.value.filter((id) => failedIds.has(id))
      : [];
    if (result.failed.length) {
      actionMessage.value = `已删除 ${result.succeededTaskIds.length} 条，${result.failed.length} 条未成功：${result.failed
        .slice(0, 3)
        .map((item) => `${item.taskId}（${item.reason}）`)
        .join("；")}`;
      actionMessageTone.value = "warn";
    } else {
      actionMessage.value = `已批量删除 ${result.succeededTaskIds.length} 条任务。`;
      actionMessageTone.value = "success";
    }
    await refreshAll();
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "批量删除失败";
  } finally {
    actionLoading.value = false;
  }
}

watch([searchText, statusFilter, sortMode], () => {
  selectedIds.value = selectedIds.value.filter((id) => sortedTasks.value.some((task) => task.id === id));
}, { deep: false });

watch([searchText, statusFilter], () => {
  if (refreshDebounceTimer) {
    clearTimeout(refreshDebounceTimer);
  }
  refreshDebounceTimer = setTimeout(() => {
    void refreshAll();
  }, 260);
}, { deep: false });

const { start } = usePolling(refreshAll, 6000);

onMounted(async () => {
  await start();
});
</script>

<style scoped>
.admin-tasks-view :deep(.admin-panel) {
  border: 1px solid #dbe4ee;
  border-radius: 1.25rem;
  background: #ffffff;
  box-shadow: 0 12px 28px rgba(15, 23, 42, 0.08);
}

.admin-tasks-view :deep(.admin-metric-card) {
  border-color: #dbe4ee;
  background: #f8fafc;
}

.admin-tasks-view :deep(.admin-table th) {
  background: #f1f5f9;
}

.admin-tasks-view :deep(.admin-table tr:hover td) {
  background: #f8fafc;
}
</style>
