<template>
  <section class="tasks-view space-y-6">
    <PageHeader
      eyebrow="Workspace"
      title="任务"
      description="筛选、排序并进入任务详情，快速定位进行中与失败任务。"
    >
      <div class="flex items-center gap-2">
        <HintBell
          title="任务页说明"
          text="这是筛选、排序和进入任务的侧边入口。配置与输出细节都在详情页。"
          :items="[
            '先戳进行中/失败任务，及时复检',
            '卡片视图便于浏览，列表视图便于巡检',
            '排序优先最近更新，尽量清空筛选再新建'
          ]"
        />
        <RouterLink to="/tasks/new" class="btn-primary">
          创建新任务
        </RouterLink>
      </div>
    </PageHeader>

    <div class="grid gap-4 xl:grid-cols-[minmax(0,1fr)_320px]">
      <div class="surface-panel p-5">
        <div class="grid gap-4 lg:grid-cols-[minmax(0,1.35fr)_200px_200px]">
          <label class="grid gap-2 text-sm text-slate-700">
            搜索任务
            <input
              v-model="searchText"
              class="field-input"
              placeholder="按标题、文件名或平台检索"
              type="search"
            />
          </label>
          <label class="grid gap-2 text-sm text-slate-700">
            状态
            <select v-model="statusFilter" class="field-select">
              <option value="all">全部状态</option>
              <option value="PENDING">排队中</option>
              <option value="ANALYZING">分析中</option>
              <option value="PLANNING">规划中</option>
              <option value="RENDERING">渲染中</option>
              <option value="COMPLETED">已完成</option>
              <option value="FAILED">失败</option>
            </select>
          </label>
          <label class="grid gap-2 text-sm text-slate-700">
            平台
            <select v-model="platformFilter" class="field-select">
              <option value="all">全部平台</option>
              <option v-for="platform in platformOptions" :key="platform" :value="platform">{{ platformLabel(platform) }}</option>
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
              <option value="semantic_desc">语义任务优先</option>
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
          <p class="mt-2 text-sm text-slate-600">分析、规划和渲染阶段的任务。</p>
        </div>
        <div class="surface-tile p-4">
          <p class="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-500">已完成</p>
          <p class="mt-3 text-3xl font-semibold tracking-[-0.04em] text-slate-900">{{ metrics.completed }}</p>
          <p class="mt-2 text-sm text-slate-600">可直接预览、下载和复盘。</p>
        </div>
        <div class="surface-tile p-4">
          <p class="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-500">需要处理</p>
          <p class="mt-3 text-3xl font-semibold tracking-[-0.04em] text-slate-900">{{ metrics.failed }}</p>
          <p class="mt-2 text-sm text-slate-600">失败任务可重试或复制参数重建。</p>
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
                @clone="handleClone"
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
                @clone="handleClone"
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

    <p class="text-xs text-slate-500">最近刷新：{{ lastLoadedAt }}</p>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { deleteTask, fetchTasks, retryTask } from "@/api/tasks";
import type { TaskListItem, TaskStatus } from "@/types";
import HintBell from "@/components/HintBell.vue";
import PageHeader from "@/components/PageHeader.vue";
import TaskCard from "@/components/TaskCard.vue";
import TaskRow from "@/components/TaskRow.vue";
import { usePolling } from "@/composables/usePolling";
import { getTaskLifecycleGroup, TASK_LIFECYCLE_GROUP_LABELS } from "@/utils/task";

const route = useRoute();
const router = useRouter();

const tasks = ref<TaskListItem[]>([]);
const loading = ref(true);
const errorMessage = ref("");
const lastLoadedAt = ref("尚未刷新");
const searchText = ref("");
const statusFilter = ref<TaskStatus | "all">("all");
const platformFilter = ref<string | "all">("all");
const sortMode = ref<"updated_desc" | "created_desc" | "progress_desc" | "semantic_desc">("updated_desc");
const viewMode = ref<"rows" | "cards">("rows");
const managingTaskId = ref("");
const collapsedGroups = ref<Record<string, boolean>>({});
let querySyncTimer: number | null = null;

const platformOptions = computed(() => {
  return Array.from(new Set(tasks.value.map((task) => task.platform).filter(Boolean))).sort();
});

const isFilterActive = computed(() => {
  return Boolean(searchText.value.trim() || statusFilter.value !== "all" || platformFilter.value !== "all");
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
  statusFilter.value = ["PENDING", "ANALYZING", "PLANNING", "RENDERING", "COMPLETED", "FAILED"].includes(nextStatus)
    ? (nextStatus as TaskStatus)
    : "all";

  const nextPlatform = normalizeQueryValue(route.query.platform);
  platformFilter.value = nextPlatform || "all";

  const nextSort = normalizeQueryValue(route.query.sort);
  sortMode.value = ["updated_desc", "created_desc", "progress_desc", "semantic_desc"].includes(nextSort)
    ? (nextSort as typeof sortMode.value)
    : "updated_desc";

  const nextView = normalizeQueryValue(route.query.view);
  viewMode.value = nextView === "cards" ? "cards" : "rows";
}

const filteredTasks = computed(() => {
  const keyword = searchText.value.trim().toLowerCase();
  return tasks.value.filter((task) => {
    if (statusFilter.value !== "all" && task.status !== statusFilter.value) {
      return false;
    }
    if (platformFilter.value !== "all" && task.platform !== platformFilter.value) {
      return false;
    }
    if (!keyword) {
      return true;
    }
    return [task.title, task.platform, task.sourceFileName ?? "", task.aspectRatio ?? ""]
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
      description: "分析、规划和渲染中的任务会优先显示在这里。",
      items: sortedFilteredTasks.value.filter((task) => getTaskLifecycleGroup(task.status) === "running")
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
      description: "失败任务可直接重试，也可以复制参数继续实验。",
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

function writeQuery() {
  const query: Record<string, string> = {};
  if (searchText.value.trim()) {
    query.q = searchText.value.trim();
  }
  if (statusFilter.value !== "all") {
    query.status = statusFilter.value;
  }
  if (platformFilter.value !== "all") {
    query.platform = platformFilter.value;
  }
  if (sortMode.value !== "updated_desc") {
    query.sort = sortMode.value;
  }
  if (viewMode.value !== "rows") {
    query.view = viewMode.value;
  }

  const currentQuery = route.query;
  const nextQuery = query;
  const sameQuery =
    (normalizeQueryValue(currentQuery.q) || "") === (nextQuery.q || "") &&
    (normalizeQueryValue(currentQuery.status) || "") === (nextQuery.status || "") &&
    (normalizeQueryValue(currentQuery.platform) || "") === (nextQuery.platform || "") &&
    (normalizeQueryValue(currentQuery.sort) || "") === (nextQuery.sort || "") &&
    (normalizeQueryValue(currentQuery.view) || "") === (nextQuery.view || "");

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
  platformFilter.value = "all";
  sortMode.value = "updated_desc";
}

function handleClone(task: TaskListItem) {
  router.push({ path: "/tasks/new", query: { cloneFrom: task.id } });
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
    await loadTasks();
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "删除任务失败";
  } finally {
    managingTaskId.value = "";
  }
}

function platformLabel(platform: string) {
  switch (platform) {
    case "douyin":
      return "抖音";
    case "kuaishou":
      return "快手";
    case "xiaohongshu":
      return "小红书";
    case "wechat":
      return "视频号";
    default:
      return platform;
  }
}

const { start } = usePolling(loadTasks, 5000);

watch(
  () => route.query,
  () => {
    applyRouteFilters();
  },
  { immediate: true, deep: true }
);

watch([searchText, statusFilter, platformFilter, sortMode, viewMode], () => {
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
