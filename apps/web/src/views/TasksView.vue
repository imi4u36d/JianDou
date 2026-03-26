<template>
  <section class="space-y-5 xl:space-y-6">
    <PageHeader
      eyebrow="Workspace"
      title="任务列表"
      description="高密度查看当前排队、处理中、已完成和失败任务，直接进入详情、复制参数或切换紧凑巡检模式。"
    >
      <RouterLink
        to="/tasks/new"
        class="btn-primary"
      >
        创建新任务
      </RouterLink>
    </PageHeader>

    <div class="grid min-w-0 gap-4 lg:grid-cols-[minmax(0,1.05fr)_320px] 2xl:grid-cols-[minmax(0,1.1fr)_360px]">
      <div class="surface-panel min-w-0 p-5 backdrop-blur-xl lg:sticky lg:top-6">
        <div class="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-sky-300/50 to-transparent"></div>
        <div class="grid gap-4 md:grid-cols-[minmax(0,1.35fr)_minmax(0,0.8fr)_minmax(0,0.8fr)]">
          <label class="grid gap-2 text-sm text-slate-200">
            搜索任务
            <input
              v-model="searchText"
              class="field-input"
              placeholder="按标题、文件名或平台检索"
              type="search"
            />
          </label>
          <label class="grid gap-2 text-sm text-slate-200">
            状态筛选
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
          <label class="grid gap-2 text-sm text-slate-200">
            平台筛选
            <select v-model="platformFilter" class="field-select">
              <option value="all">全部平台</option>
              <option v-for="platform in platformOptions" :key="platform" :value="platform">{{ platformLabel(platform) }}</option>
            </select>
          </label>
        </div>

        <div class="mt-4 grid gap-3 md:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
          <label class="grid gap-2 text-sm text-slate-200">
            排序方式
            <select v-model="sortMode" class="field-select">
              <option value="updated_desc">最近更新</option>
              <option value="created_desc">最新创建</option>
              <option value="progress_desc">进度优先</option>
              <option value="semantic_desc">语义任务优先</option>
            </select>
          </label>
          <div class="surface-tile px-4 py-3 text-sm text-slate-300">
            <p class="text-xs uppercase tracking-[0.24em] text-slate-400">工作台提示</p>
            <p class="mt-2 leading-6">高密度模式更适合批量巡检，卡片模式更适合查看单条任务的语义和输出。</p>
          </div>
        </div>

        <div class="mt-4 flex flex-wrap items-center gap-2">
          <div class="segmented-shell">
            <button
              class="btn-segment"
              :class="viewMode === 'rows' ? 'btn-segment-active' : ''"
              type="button"
              @click="viewMode = 'rows'"
            >
              紧凑行
            </button>
            <button
              class="btn-segment"
              :class="viewMode === 'cards' ? 'btn-segment-active' : ''"
              type="button"
              @click="viewMode = 'cards'"
            >
              卡片视图
            </button>
          </div>
          <button
            :class="isFilterActive ? 'btn-warning' : 'btn-ghost'"
            type="button"
            @click="clearFilters"
          >
            清空筛选
          </button>
          <div class="surface-chip whitespace-nowrap">
            当前筛选：{{ filteredTasks.length }} / {{ tasks.length }}
          </div>
          <div class="surface-chip whitespace-nowrap">
            当前视图：{{ viewMode === "rows" ? "紧凑巡检" : "卡片摘要" }}
          </div>
        </div>
      </div>

      <div class="grid min-w-0 gap-3 sm:grid-cols-2 xl:grid-cols-3">
        <div class="surface-tile relative min-w-0 overflow-hidden p-4">
          <div class="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-sky-300/0 via-sky-300/60 to-sky-300/0"></div>
          <p class="text-xs uppercase tracking-[0.24em] text-slate-400">总任务数</p>
          <p class="mt-3 text-3xl font-semibold text-white">{{ metrics.total }}</p>
          <p class="mt-2 text-xs text-slate-400">包含所有状态的任务</p>
        </div>
        <div class="surface-tile relative min-w-0 overflow-hidden p-4">
          <div class="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-emerald-300/0 via-emerald-300/60 to-emerald-300/0"></div>
          <p class="text-xs uppercase tracking-[0.24em] text-slate-400">进行中</p>
          <p class="mt-3 text-3xl font-semibold text-white">{{ metrics.running }}</p>
          <p class="mt-2 text-xs text-slate-400">分析、规划和渲染中的任务</p>
        </div>
        <div class="surface-tile relative min-w-0 overflow-hidden p-4">
          <div class="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-fuchsia-300/0 via-fuchsia-300/60 to-fuchsia-300/0"></div>
          <p class="text-xs uppercase tracking-[0.24em] text-slate-400">已完成</p>
          <p class="mt-3 text-3xl font-semibold text-white">{{ metrics.completed }}</p>
          <p class="mt-2 text-xs text-slate-400">可直接预览和下载</p>
        </div>
        <div class="surface-tile relative min-w-0 overflow-hidden p-4">
          <div class="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-rose-300/0 via-rose-300/60 to-rose-300/0"></div>
          <p class="text-xs uppercase tracking-[0.24em] text-slate-400">失败任务</p>
          <p class="mt-3 text-3xl font-semibold text-white">{{ metrics.failed }}</p>
          <p class="mt-2 text-xs text-slate-400">可重试或复用参数再建</p>
        </div>
        <div class="surface-tile relative min-w-0 overflow-hidden p-4">
          <div class="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-amber-300/0 via-amber-300/60 to-amber-300/0"></div>
          <p class="text-xs uppercase tracking-[0.24em] text-slate-400">语义任务</p>
          <p class="mt-3 text-3xl font-semibold text-white">{{ metrics.semantic }}</p>
          <p class="mt-2 text-xs text-slate-400">已提供字幕或台词文本</p>
        </div>
        <div class="surface-tile relative min-w-0 overflow-hidden p-4">
          <div class="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-cyan-300/0 via-cyan-300/60 to-cyan-300/0"></div>
          <p class="text-xs uppercase tracking-[0.24em] text-slate-400">带时间戳字幕</p>
          <p class="mt-3 text-3xl font-semibold text-white">{{ metrics.timedSemantic }}</p>
          <p class="mt-2 text-xs text-slate-400">更适合模型按剧情切点规划</p>
        </div>
      </div>
    </div>

    <div v-if="errorMessage" class="rounded-[24px] border border-rose-500/20 bg-rose-500/10 p-4 text-sm text-rose-100">
      <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <p>{{ errorMessage }}</p>
        <button class="btn-secondary btn-sm" type="button" @click="loadTasks">
          重新加载
        </button>
      </div>
    </div>

    <div v-if="loading" class="surface-tile p-10 text-center text-slate-300">
      正在加载任务列表...
    </div>

    <template v-else>
      <div v-if="filteredTasks.length === 0" class="surface-tile border-dashed p-10 text-center">
        <h3 class="text-lg font-medium text-white">没有匹配的任务</h3>
        <p class="mt-2 text-sm text-slate-300">尝试清空搜索和筛选，或者新建一个任务。</p>
        <button class="btn-warning mt-5" type="button" @click="clearFilters">
          清空筛选
        </button>
      </div>

      <div v-else class="grid gap-5">
        <section v-for="group in groupedTasks" :key="group.key" class="surface-panel relative grid gap-4 p-5">
          <div class="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-white/20 to-transparent"></div>
          <div class="flex flex-wrap items-end justify-between gap-3">
            <div>
              <p class="text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-500">分组</p>
              <h3 class="mt-2 text-lg font-semibold text-white">{{ group.title }}</h3>
              <p class="mt-1 max-w-2xl line-clamp-2 text-sm leading-6 text-slate-400">{{ group.description }}</p>
            </div>
            <div class="flex flex-wrap items-center gap-2">
              <span class="surface-chip shrink-0 text-xs font-medium">{{ group.items.length }} 条</span>
              <button class="btn-ghost btn-sm" type="button" @click="toggleGroup(group.key)">
                {{ isGroupCollapsed(group.key) ? "展开" : "折叠" }}
              </button>
            </div>
          </div>
          <div v-if="!isGroupCollapsed(group.key) && group.items.length">
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
          <div v-else class="surface-tile border-dashed p-4 text-sm text-slate-400">
            该分组已折叠，点击右上角可展开查看。
          </div>
        </section>
      </div>
    </template>

    <p class="mt-2 text-xs text-slate-400">最近刷新：{{ lastLoadedAt }}</p>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { deleteTask, fetchTasks, retryTask } from "@/api/tasks";
import type { TaskListItem, TaskStatus } from "@/types";
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
    tasks.value = await fetchTasks({
      q: searchText.value,
      status: statusFilter.value,
      platform: platformFilter.value
    });
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
  writeQuery();
  void loadTasks();
});

onMounted(async () => {
  await start();
});
</script>
