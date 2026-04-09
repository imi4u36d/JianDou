<template>
  <section class="tasks-view space-y-6">
    <PageHeader
      eyebrow="Workspace"
      title="任务"
      description="筛选并监控任务执行，实时查看进度与阶段。"
    >
      <div class="flex items-center gap-2">
        <HintBell
          title="任务页说明"
          text="这是统一任务看板，支持列表筛选、实时轮询和单任务详情展开。"
          :items="[
            '卡片视图便于快速浏览，列表视图便于巡检',
            '点击任务即可展开详情并查看阶段日志',
            '新建任务后会自动高亮最新任务'
          ]"
        />
        <RouterLink to="/tasks/new" class="btn-primary">
          创建新任务
        </RouterLink>
      </div>
    </PageHeader>

    <div class="grid gap-4 xl:grid-cols-[minmax(0,1fr)_320px]">
      <div class="surface-panel p-5">
        <div class="grid gap-4 lg:grid-cols-[minmax(0,1.35fr)_200px]">
          <label class="grid gap-2 text-sm text-slate-700">
            搜索任务
            <input
              v-model="searchText"
              class="field-input"
              placeholder="按标题、文件名检索"
              type="search"
            />
          </label>
          <label class="grid gap-2 text-sm text-slate-700">
            状态
            <select v-model="statusFilter" class="field-select">
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
        </div>

        <div class="mt-4 flex flex-wrap items-center gap-2">
          <div class="segmented-shell">
            <button class="btn-segment" :class="viewMode === 'rows' ? 'btn-segment-active' : ''" type="button" @click="viewMode = 'rows'">
              列表
            </button>
            <button class="btn-segment" :class="viewMode === 'cards' ? 'btn-segment-active' : ''" type="button" @click="viewMode = 'cards'">
              卡片
            </button>
          </div>
          <label class="ml-auto min-w-[180px] max-w-[220px] grow text-sm text-slate-700 sm:ml-0 sm:grow-0">
            <select v-model="sortMode" class="field-select">
              <option value="updated_desc">最近更新</option>
              <option value="created_desc">最新创建</option>
              <option value="progress_desc">进度优先</option>
              <option value="semantic_desc">文本输入优先</option>
            </select>
          </label>
          <button :class="isFilterActive ? 'btn-warning' : 'btn-ghost'" type="button" @click="clearFilters">
            清空筛选
          </button>
          <span class="surface-chip">{{ filteredTasks.length }} / {{ tasks.length }}</span>
        </div>
      </div>

      <div class="grid gap-3 sm:grid-cols-3 xl:grid-cols-1">
        <div class="surface-tile p-4">
          <p class="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-500">进行中</p>
          <p class="mt-3 text-3xl font-semibold tracking-[-0.04em] text-slate-900">{{ metrics.running }}</p>
          <p class="mt-2 text-sm text-slate-600">分析、编排和渲染阶段的任务。</p>
        </div>
        <div class="surface-tile p-4">
          <p class="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-500">已完成</p>
          <p class="mt-3 text-3xl font-semibold tracking-[-0.04em] text-slate-900">{{ metrics.completed }}</p>
          <p class="mt-2 text-sm text-slate-600">可直接预览、下载和查看结果。</p>
        </div>
        <div class="surface-tile p-4">
          <p class="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-500">需要处理</p>
          <p class="mt-3 text-3xl font-semibold tracking-[-0.04em] text-slate-900">{{ metrics.failed }}</p>
          <p class="mt-2 text-sm text-slate-600">失败任务可重试或直接删除。</p>
        </div>
      </div>
    </div>

    <div v-if="errorMessage" class="surface-tile border border-rose-200 bg-rose-50/90 p-4 text-sm text-rose-700">
      <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <p>{{ errorMessage }}</p>
        <button class="btn-secondary btn-sm" type="button" @click="loadTasks">
          重新加载
        </button>
      </div>
    </div>

    <div v-if="loading" class="surface-tile p-10 text-center text-slate-600">
      正在加载任务列表...
    </div>

    <template v-else>
      <div v-if="filteredTasks.length === 0" class="surface-panel p-10 text-center">
        <h3 class="text-lg font-semibold text-slate-900">没有匹配的任务</h3>
        <p class="mt-2 text-sm text-slate-600">尝试清空搜索和筛选，或者直接新建一个任务。</p>
        <button class="btn-warning mt-5" type="button" @click="clearFilters">
          清空筛选
        </button>
      </div>

      <div v-else class="grid gap-5">
        <section v-for="group in groupedTasks" :key="group.key" class="surface-panel p-5">
          <div class="flex flex-wrap items-end justify-between gap-3">
            <div>
              <p class="text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-500">任务分组</p>
              <h3 class="mt-2 text-xl font-semibold tracking-[-0.03em] text-slate-900">{{ group.title }}</h3>
              <p class="mt-1 max-w-2xl text-sm leading-6 text-slate-600">{{ group.description }}</p>
            </div>
            <div class="flex flex-wrap items-center gap-2">
              <span class="surface-chip">{{ group.items.length }} 条</span>
              <button class="btn-ghost btn-sm" type="button" @click="toggleGroup(group.key)">
                {{ isGroupCollapsed(group.key) ? "展开" : "折叠" }}
              </button>
            </div>
          </div>
          <div v-if="!isGroupCollapsed(group.key) && group.items.length" class="mt-5">
            <div v-if="viewMode === 'cards'" class="grid min-w-0 gap-4 xl:grid-cols-2 2xl:grid-cols-3">
              <TaskCard
                v-for="task in group.items"
                :key="task.id"
                :busy="managingTaskId === task.id"
                :task="task"
                :selectable="true"
                :selected="task.id === selectedTaskId"
                @select="handleSelectTask"
                @pause="handlePause"
                @continue="handleContinueTask"
                @terminate="handleTerminate"
                @retry="handleRetry"
                @delete="handleDelete"
              />
            </div>
            <div v-else class="grid gap-3">
              <TaskRow
                v-for="task in group.items"
                :key="task.id"
                :busy="managingTaskId === task.id"
                :task="task"
                :selectable="true"
                :selected="task.id === selectedTaskId"
                @select="handleSelectTask"
                @pause="handlePause"
                @continue="handleContinueTask"
                @terminate="handleTerminate"
                @retry="handleRetry"
                @delete="handleDelete"
              />
            </div>
          </div>
          <div v-else class="surface-tile mt-5 p-4 text-sm text-slate-600">
            该分组已折叠，点击右上角可展开查看。
          </div>
        </section>
      </div>
    </template>

    <section v-if="selectedTaskId" class="surface-panel p-5">
      <div class="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p class="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-500">任务详情</p>
          <h3 class="mt-2 text-lg font-semibold text-slate-900">
            {{ selectedTaskDetail?.title || selectedTaskSummary?.title || "加载中..." }}
          </h3>
          <p class="mt-1 text-sm text-slate-600">
            {{ selectedTaskDetail?.id || selectedTaskId }} · 当前阶段 {{ selectedTaskStageLabel }}
          </p>
        </div>
        <div class="flex items-center gap-2">
          <span class="surface-chip">进度 {{ selectedTaskDetail?.progress ?? selectedTaskSummary?.progress ?? 0 }}%</span>
          <button
            v-if="selectedTaskActionTask && ['PENDING', 'ANALYZING', 'PLANNING'].includes(selectedTaskActionTask.status)"
            class="btn-secondary btn-sm"
            type="button"
            :disabled="selectedTaskLoading || managingTaskId === selectedTaskActionTask.id"
            @click="handlePause(selectedTaskActionTask)"
          >
            暂停
          </button>
          <button
            v-if="selectedTaskActionTask && ['PENDING', 'ANALYZING', 'PLANNING', 'RENDERING'].includes(selectedTaskActionTask.status)"
            class="btn-warning btn-sm"
            type="button"
            :disabled="selectedTaskLoading || managingTaskId === selectedTaskActionTask.id"
            @click="handleTerminate(selectedTaskActionTask)"
          >
            终止
          </button>
          <button
            v-if="selectedTaskActionTask?.status === 'PAUSED'"
            class="btn-primary btn-sm"
            type="button"
            :disabled="selectedTaskLoading || managingTaskId === selectedTaskActionTask.id"
            @click="handleContinueTask(selectedTaskActionTask)"
          >
            继续生成
          </button>
          <button class="btn-secondary btn-sm" type="button" :disabled="selectedTaskLoading" @click="refreshSelectedTask">
            刷新详情
          </button>
        </div>
      </div>

      <div v-if="selectedTaskError" class="surface-tile mt-4 border border-rose-200 bg-rose-50/90 p-4 text-sm text-rose-700">
        {{ selectedTaskError }}
      </div>

      <div v-else class="mt-4 grid gap-4 xl:grid-cols-[1.25fr_0.75fr]">
        <div class="surface-tile p-4">
          <p class="text-sm font-semibold text-slate-900">阶段时间线</p>
          <div class="mt-3 grid gap-2">
            <div
              v-for="stage in selectedTaskStages"
              :key="stage.key"
              class="flex items-center justify-between rounded-xl border px-3 py-2 text-sm"
              :class="stageStateClass(stage.state)"
            >
              <span>{{ stage.label }}</span>
              <span class="font-semibold">{{ stage.stateLabel }}</span>
            </div>
          </div>
          <p class="mt-3 text-xs text-slate-500">
            开始 {{ formatDateTime(selectedTaskDetail?.startedAt) }} · 完成 {{ formatDateTime(selectedTaskDetail?.finishedAt) }}
          </p>
        </div>

        <div class="surface-tile p-4">
          <p class="text-sm font-semibold text-slate-900">结果概览</p>
          <div class="mt-3 grid gap-2 text-sm text-slate-600">
            <div class="flex items-center justify-between">
              <span>已生成结果</span>
              <span class="font-semibold text-slate-900">
                {{ selectedTaskDetail?.completedOutputCount ?? selectedTaskDetail?.outputs?.length ?? 0 }} 条
              </span>
            </div>
            <div class="flex items-center justify-between">
              <span>比例</span>
              <span class="font-semibold text-slate-900">{{ selectedTaskDetail?.aspectRatio ?? selectedTaskSummary?.aspectRatio ?? "-" }}</span>
            </div>
          </div>
        </div>
      </div>

      <div class="surface-tile mt-4 p-4">
        <div class="flex items-center justify-between gap-3">
          <p class="text-sm font-semibold text-slate-900">最近阶段日志</p>
          <span class="surface-chip">{{ selectedTaskTrace.length }} 条</span>
        </div>
        <ul class="mt-3 grid gap-2 text-sm text-slate-600">
          <li v-if="selectedTaskTrace.length === 0" class="rounded-xl border border-slate-200 bg-white px-3 py-2 text-slate-500">
            暂无日志，任务刚启动时可能需要等待几秒。
          </li>
          <li
            v-for="event in selectedTaskTrace.slice(0, 8)"
            :key="`${event.timestamp}-${event.event}-${event.stage}`"
            class="rounded-xl border border-slate-200 bg-white px-3 py-2"
          >
            <p class="text-xs text-slate-500">{{ formatDateTime(event.timestamp) }} · {{ event.stage }} · {{ event.level }}</p>
            <p class="mt-1 text-slate-800">{{ event.message }}</p>
          </li>
        </ul>
      </div>
    </section>

    <p class="text-xs text-slate-500">最近刷新：{{ lastLoadedAt }}</p>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { continueTask, deleteTask, fetchTask, fetchTaskTrace, fetchTasks, pauseTask, retryTask, terminateTask } from "@/api/tasks";
import type { TaskDetail, TaskListItem, TaskStatus, TaskTraceEvent } from "@/types";
import HintBell from "@/components/HintBell.vue";
import PageHeader from "@/components/PageHeader.vue";
import TaskCard from "@/components/TaskCard.vue";
import TaskRow from "@/components/TaskRow.vue";
import { usePolling } from "@/composables/usePolling";
import { formatTaskStatus, getTaskLifecycleGroup, TASK_LIFECYCLE_GROUP_LABELS } from "@/utils/task";

const route = useRoute();
const router = useRouter();

const tasks = ref<TaskListItem[]>([]);
const loading = ref(true);
const errorMessage = ref("");
const lastLoadedAt = ref("尚未刷新");
const searchText = ref("");
const statusFilter = ref<TaskStatus | "all">("all");
const sortMode = ref<"updated_desc" | "created_desc" | "progress_desc" | "semantic_desc">("updated_desc");
const viewMode = ref<"rows" | "cards">("rows");
const managingTaskId = ref("");
const collapsedGroups = ref<Record<string, boolean>>({});
const selectedTaskId = ref("");
const selectedTaskDetail = ref<TaskDetail | null>(null);
const selectedTaskTrace = ref<TaskTraceEvent[]>([]);
const selectedTaskLoading = ref(false);
const selectedTaskError = ref("");
let querySyncTimer: number | null = null;

const isFilterActive = computed(() => {
  return Boolean(searchText.value.trim() || statusFilter.value !== "all");
});

function normalizeQueryValue(value: unknown) {
  if (Array.isArray(value)) {
    return value[0] == null ? "" : String(value[0]);
  }
  return value == null ? "" : String(value);
}

function applyRouteFilters() {
  searchText.value = normalizeQueryValue(route.query.q);

  const nextStatus = normalizeQueryValue(route.query.status);
  statusFilter.value = ["PENDING", "PAUSED", "ANALYZING", "PLANNING", "RENDERING", "COMPLETED", "FAILED"].includes(nextStatus)
    ? (nextStatus as TaskStatus)
    : "all";

  const nextSort = normalizeQueryValue(route.query.sort);
  sortMode.value = ["updated_desc", "created_desc", "progress_desc", "semantic_desc"].includes(nextSort)
    ? (nextSort as typeof sortMode.value)
    : "updated_desc";

  const nextView = normalizeQueryValue(route.query.view);
  viewMode.value = nextView === "cards" ? "cards" : "rows";

  const selected = normalizeQueryValue(route.query.selected) || normalizeQueryValue(route.query.taskId);
  selectedTaskId.value = selected.trim();
}

const selectedTaskSummary = computed(() => {
  if (!selectedTaskId.value) {
    return null;
  }
  return tasks.value.find((task) => task.id === selectedTaskId.value) ?? null;
});

const selectedTaskActionTask = computed(() => selectedTaskDetail.value ?? selectedTaskSummary.value);

const selectedTaskStageLabel = computed(() => {
  if (selectedTaskDetail.value) {
    return formatTaskStatus(selectedTaskDetail.value.status);
  }
  if (selectedTaskSummary.value) {
    return formatTaskStatus(selectedTaskSummary.value.status);
  }
  return "等待更新";
});

const selectedTaskStages = computed(() => {
  const status = selectedTaskDetail.value?.status ?? selectedTaskSummary.value?.status ?? "PENDING";
  const stageOrder: TaskStatus[] = ["ANALYZING", "PLANNING", "RENDERING", "COMPLETED"];
  const pausedAtRender = status === "PAUSED";
  const currentIndex = pausedAtRender ? 2 : stageOrder.indexOf(status);
  const toLabel = (state: "pending" | "active" | "paused" | "done" | "failed") => {
    switch (state) {
      case "done":
        return "已完成";
      case "active":
        return "进行中";
      case "paused":
        return "已暂停";
      case "failed":
        return "失败";
      default:
        return "等待";
    }
  };
  const items = [
    { key: "ANALYZING", label: "素材分析", state: currentIndex > 0 ? "done" : currentIndex === 0 ? "active" : "pending" },
    { key: "PLANNING", label: "任务编排", state: currentIndex > 1 ? "done" : currentIndex === 1 ? "active" : "pending" },
    { key: "RENDERING", label: "视频生成", state: pausedAtRender ? "paused" : currentIndex > 2 ? "done" : currentIndex === 2 ? "active" : "pending" },
    { key: "COMPLETED", label: "任务完成", state: status === "COMPLETED" ? "done" : status === "FAILED" ? "failed" : "pending" },
  ] as Array<{ key: string; label: string; state: "pending" | "active" | "paused" | "done" | "failed" }>;
  return items.map((item) => ({ ...item, stateLabel: toLabel(item.state) }));
});

const filteredTasks = computed(() => {
  const keyword = searchText.value.trim().toLowerCase();
  return tasks.value.filter((task) => {
    if (statusFilter.value !== "all" && task.status !== statusFilter.value) {
      return false;
    }
    if (!keyword) {
      return true;
    }
    return [task.title, task.sourceFileName ?? "", task.aspectRatio ?? ""]
      .join(" ")
      .toLowerCase()
      .includes(keyword);
  });
});

const sortedFilteredTasks = computed(() => {
  const items = [...filteredTasks.value];
  switch (sortMode.value) {
    case "created_desc":
      return items.sort((left, right) => new Date(right.createdAt).getTime() - new Date(left.createdAt).getTime());
    case "progress_desc":
      return items.sort((left, right) => (right.progress ?? 0) - (left.progress ?? 0));
    case "semantic_desc":
      return items.sort((left, right) => Number(Boolean(right.hasTimedTranscript || right.hasTranscript)) - Number(Boolean(left.hasTimedTranscript || left.hasTranscript)));
    default:
      return items.sort((left, right) => new Date(right.updatedAt).getTime() - new Date(left.updatedAt).getTime());
  }
});

const metrics = computed(() => {
  const total = tasks.value.length;
  const running = tasks.value.filter((task) => getTaskLifecycleGroup(task.status) === "running").length;
  const completed = tasks.value.filter((task) => getTaskLifecycleGroup(task.status) === "completed").length;
  const failed = tasks.value.filter((task) => getTaskLifecycleGroup(task.status) === "failed").length;
  const semantic = tasks.value.filter((task) => task.hasTranscript).length;
  const timedSemantic = tasks.value.filter((task) => task.hasTimedTranscript).length;
  return { total, running, completed, failed, semantic, timedSemantic };
});

const groupedTasks = computed(() => {
  const groups = [
    {
      key: "running",
      title: TASK_LIFECYCLE_GROUP_LABELS.running,
      description: "分析、编排和渲染中的任务会优先显示在这里。",
      items: sortedFilteredTasks.value.filter((task) => getTaskLifecycleGroup(task.status) === "running")
    },
    {
      key: "paused",
      title: TASK_LIFECYCLE_GROUP_LABELS.paused,
      description: "已暂停的任务可继续生成，也可以直接删除。",
      items: sortedFilteredTasks.value.filter((task) => getTaskLifecycleGroup(task.status) === "paused")
    },
    {
      key: "queued",
      title: TASK_LIFECYCLE_GROUP_LABELS.queued,
      description: "等待处理的任务，适合查看队列压力。",
      items: sortedFilteredTasks.value.filter((task) => getTaskLifecycleGroup(task.status) === "queued")
    },
    {
      key: "completed",
      title: TASK_LIFECYCLE_GROUP_LABELS.completed,
      description: "已经完成渲染的素材，可以直接预览和下载。",
      items: sortedFilteredTasks.value.filter((task) => getTaskLifecycleGroup(task.status) === "completed")
    },
    {
      key: "failed",
      title: TASK_LIFECYCLE_GROUP_LABELS.failed,
      description: "失败任务可直接重试或删除后重新创建。",
      items: sortedFilteredTasks.value.filter((task) => getTaskLifecycleGroup(task.status) === "failed")
    }
  ];
  return groups.filter((group) => group.items.length > 0);
});

async function loadTasks() {
  errorMessage.value = "";
  loading.value = tasks.value.length === 0;
  try {
    // Keep filtering local so typing and toggling view mode do not trigger extra requests.
    tasks.value = await fetchTasks();
    lastLoadedAt.value = new Date().toLocaleString();
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "加载任务列表失败";
  } finally {
    loading.value = false;
  }
}

async function loadSelectedTaskDetails() {
  if (!selectedTaskId.value) {
    selectedTaskDetail.value = null;
    selectedTaskTrace.value = [];
    selectedTaskError.value = "";
    return;
  }
  selectedTaskLoading.value = true;
  selectedTaskError.value = "";
  try {
    const [detail, trace] = await Promise.all([
      fetchTask(selectedTaskId.value),
      fetchTaskTrace(selectedTaskId.value, 120),
    ]);
    selectedTaskDetail.value = detail;
    selectedTaskTrace.value = [...trace].reverse();
  } catch (error) {
    selectedTaskError.value = error instanceof Error ? error.message : "任务详情加载失败";
  } finally {
    selectedTaskLoading.value = false;
  }
}

async function refreshSelectedTask() {
  await loadSelectedTaskDetails();
}

function writeQuery() {
  const query: Record<string, string> = {};
  if (searchText.value.trim()) {
    query.q = searchText.value.trim();
  }
  if (statusFilter.value !== "all") {
    query.status = statusFilter.value;
  }
  if (sortMode.value !== "updated_desc") {
    query.sort = sortMode.value;
  }
  if (viewMode.value !== "rows") {
    query.view = viewMode.value;
  }
  if (selectedTaskId.value) {
    query.selected = selectedTaskId.value;
  }

  const currentQuery = route.query;
  const nextQuery = query;
  const sameQuery =
    (normalizeQueryValue(currentQuery.q) || "") === (nextQuery.q || "") &&
    (normalizeQueryValue(currentQuery.status) || "") === (nextQuery.status || "") &&
    (normalizeQueryValue(currentQuery.sort) || "") === (nextQuery.sort || "") &&
    (normalizeQueryValue(currentQuery.view) || "") === (nextQuery.view || "") &&
    ((normalizeQueryValue(currentQuery.selected) || normalizeQueryValue(currentQuery.taskId) || "") === (nextQuery.selected || ""));

  if (!sameQuery) {
    router.replace({ query: nextQuery });
  }
}

function scheduleWriteQuery() {
  if (querySyncTimer !== null) {
    window.clearTimeout(querySyncTimer);
  }
  querySyncTimer = window.setTimeout(() => {
    querySyncTimer = null;
    writeQuery();
  }, 160);
}

function clearFilters() {
  searchText.value = "";
  statusFilter.value = "all";
  sortMode.value = "updated_desc";
}

function handleSelectTask(task: TaskListItem) {
  selectedTaskId.value = task.id;
  writeQuery();
  void loadSelectedTaskDetails();
}

function isGroupCollapsed(groupKey: string) {
  return Boolean(collapsedGroups.value[groupKey]);
}

function toggleGroup(groupKey: string) {
  collapsedGroups.value = {
    ...collapsedGroups.value,
    [groupKey]: !collapsedGroups.value[groupKey]
  };
}

async function handleRetry(task: TaskListItem) {
  if (managingTaskId.value) {
    return;
  }
  managingTaskId.value = task.id;
  errorMessage.value = "";
  try {
    await retryTask(task.id);
    await loadTasks();
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "任务重试失败";
  } finally {
    managingTaskId.value = "";
  }
}

async function handlePause(task: TaskListItem) {
  if (managingTaskId.value) {
    return;
  }
  managingTaskId.value = task.id;
  errorMessage.value = "";
  try {
    await pauseTask(task.id);
    await Promise.all([loadTasks(), loadSelectedTaskDetails()]);
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "暂停任务失败";
  } finally {
    managingTaskId.value = "";
  }
}

async function handleContinueTask(task: TaskListItem) {
  if (managingTaskId.value) {
    return;
  }
  managingTaskId.value = task.id;
  errorMessage.value = "";
  try {
    await continueTask(task.id);
    await Promise.all([loadTasks(), loadSelectedTaskDetails()]);
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "继续任务失败";
  } finally {
    managingTaskId.value = "";
  }
}

async function handleTerminate(task: TaskListItem) {
  if (managingTaskId.value) {
    return;
  }
  const ok = window.confirm(`确认终止任务“${task.title}”吗？终止后任务会变为失败状态，可再删除或重试。`);
  if (!ok) {
    return;
  }
  managingTaskId.value = task.id;
  errorMessage.value = "";
  try {
    await terminateTask(task.id);
    await Promise.all([loadTasks(), loadSelectedTaskDetails()]);
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "终止任务失败";
  } finally {
    managingTaskId.value = "";
  }
}

async function handleDelete(task: TaskListItem) {
  if (managingTaskId.value) {
    return;
  }
  const ok = window.confirm(`确认删除任务“${task.title}”吗？已生成的输出和日志也会一并清理。`);
  if (!ok) {
    return;
  }
  managingTaskId.value = task.id;
  errorMessage.value = "";
  try {
    await deleteTask(task.id);
    if (selectedTaskId.value === task.id) {
      selectedTaskId.value = "";
      selectedTaskDetail.value = null;
      selectedTaskTrace.value = [];
      selectedTaskError.value = "";
      writeQuery();
    }
    await loadTasks();
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "删除任务失败";
  } finally {
    managingTaskId.value = "";
  }
}

function formatDateTime(value?: string | null) {
  if (!value) {
    return "-";
  }
  const timestamp = new Date(value).getTime();
  if (!Number.isFinite(timestamp)) {
    return value;
  }
  return new Date(timestamp).toLocaleString();
}

function stageStateClass(state: "pending" | "active" | "paused" | "done" | "failed") {
  switch (state) {
    case "done":
      return "border-emerald-200 bg-emerald-50 text-emerald-800";
    case "active":
      return "border-sky-200 bg-sky-50 text-sky-800";
    case "paused":
      return "border-amber-200 bg-amber-50 text-amber-800";
    case "failed":
      return "border-rose-200 bg-rose-50 text-rose-700";
    default:
      return "border-slate-200 bg-white text-slate-600";
  }
}

const { start } = usePolling(async () => {
  await loadTasks();
  await loadSelectedTaskDetails();
}, 5000);

watch(
  () => route.query,
  () => {
    applyRouteFilters();
    void loadSelectedTaskDetails();
  },
  { immediate: true, deep: true }
);

watch([searchText, statusFilter, sortMode, viewMode], () => {
  scheduleWriteQuery();
});

onMounted(async () => {
  await start();
});

onUnmounted(() => {
  if (querySyncTimer !== null) {
    window.clearTimeout(querySyncTimer);
    querySyncTimer = null;
  }
});
</script>

<style scoped>
.tasks-view {
  --accent: #0891b2;
}

.tasks-view :deep(.surface-panel) {
  border: 1px solid #dbe4ee;
  border-radius: 1.5rem;
  background: #ffffff;
  box-shadow: 0 14px 32px rgba(15, 23, 42, 0.08);
}

.tasks-view :deep(.surface-tile) {
  border: 1px solid #dbe4ee;
  border-radius: 1rem;
  background: #f8fafc;
  box-shadow: none;
}

.tasks-view :deep(.surface-chip) {
  border-color: #cfe8ef;
  background: #ecfeff;
  color: #0e7490;
}

.tasks-view :deep(.segmented-shell) {
  border-color: #dbe4ee;
  background: #f8fafc;
}

.tasks-view :deep(.btn-segment-active) {
  background: #ffffff;
  color: #0f172a;
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.08);
}

.tasks-view :deep(.btn-primary) {
  background: linear-gradient(135deg, #0e7490, #0891b2);
}

.tasks-view :deep(.btn-primary:hover:not(:disabled)) {
  box-shadow: 0 10px 20px rgba(8, 145, 178, 0.24);
}
</style>
