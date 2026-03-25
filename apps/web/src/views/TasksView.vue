<template>
  <section class="space-y-6">
    <PageHeader
      eyebrow="Workspace"
      title="任务列表"
      description="查看当前排队、处理中、已完成和失败任务，直接进入详情或复制参数继续创建。"
    >
      <RouterLink to="/tasks/new" class="rounded-full bg-rose-500 px-4 py-2 text-sm font-medium text-white transition duration-200 hover:bg-rose-400">
        创建新任务
      </RouterLink>
    </PageHeader>

    <div class="grid gap-4 lg:grid-cols-[1.15fr_0.85fr]">
      <div class="rounded-[28px] border border-white/10 bg-[linear-gradient(180deg,rgba(15,15,35,0.82),rgba(8,11,24,0.68))] p-5 shadow-[0_20px_70px_rgba(0,0,0,0.28)]">
        <div class="grid gap-3 md:grid-cols-[1.3fr_0.7fr_0.7fr]">
          <label class="grid gap-2 text-sm text-slate-200">
            搜索任务
            <input
              v-model="searchText"
              class="rounded-2xl border border-white/10 bg-slate-950/70 px-4 py-3 text-white outline-none transition duration-200 placeholder:text-slate-500 focus:border-rose-300/60"
              placeholder="按标题、文件名或平台检索"
              type="search"
            />
          </label>
          <label class="grid gap-2 text-sm text-slate-200">
            状态筛选
            <select v-model="statusFilter" class="rounded-2xl border border-white/10 bg-slate-950/70 px-4 py-3 text-white transition duration-200 focus:border-rose-300/60">
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
            <select v-model="platformFilter" class="rounded-2xl border border-white/10 bg-slate-950/70 px-4 py-3 text-white transition duration-200 focus:border-rose-300/60">
              <option value="all">全部平台</option>
              <option v-for="platform in platformOptions" :key="platform" :value="platform">{{ platformLabel(platform) }}</option>
            </select>
          </label>
        </div>

        <div class="mt-3 grid gap-3 md:grid-cols-[1fr_1fr]">
          <label class="grid gap-2 text-sm text-slate-200">
            排序方式
            <select v-model="sortMode" class="rounded-2xl border border-white/10 bg-slate-950/70 px-4 py-3 text-white transition duration-200 focus:border-rose-300/60">
              <option value="updated_desc">最近更新</option>
              <option value="created_desc">最新创建</option>
              <option value="progress_desc">进度优先</option>
              <option value="semantic_desc">语义任务优先</option>
            </select>
          </label>
          <div class="rounded-2xl border border-white/10 bg-slate-950/50 px-4 py-3 text-sm text-slate-300">
            <p class="text-xs uppercase tracking-[0.24em] text-slate-400">运营提醒</p>
            <p class="mt-2">优先关注带时间戳字幕的任务，它们更容易让模型给出稳定切点。</p>
          </div>
        </div>

        <div class="mt-4 flex flex-wrap gap-2">
          <button
            class="rounded-full border px-4 py-2 text-sm transition duration-200"
            :class="isFilterActive ? 'border-rose-300/40 bg-rose-500/15 text-rose-100' : 'border-white/10 bg-white/[0.04] text-slate-200 hover:border-rose-300/40 hover:bg-white/10'"
            type="button"
            @click="clearFilters"
          >
            清空筛选
          </button>
          <div class="rounded-full border border-white/10 bg-white/[0.04] px-4 py-2 text-sm text-slate-300">
            当前筛选：{{ filteredTasks.length }} / {{ tasks.length }}
          </div>
        </div>
      </div>

      <div class="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        <div class="rounded-[24px] border border-white/10 bg-white/[0.04] p-4">
          <p class="text-xs uppercase tracking-[0.24em] text-slate-400">总任务数</p>
          <p class="mt-3 text-3xl font-semibold text-white">{{ metrics.total }}</p>
          <p class="mt-2 text-xs text-slate-400">包含所有状态的任务</p>
        </div>
        <div class="rounded-[24px] border border-white/10 bg-white/[0.04] p-4">
          <p class="text-xs uppercase tracking-[0.24em] text-slate-400">进行中</p>
          <p class="mt-3 text-3xl font-semibold text-white">{{ metrics.running }}</p>
          <p class="mt-2 text-xs text-slate-400">分析、规划和渲染中的任务</p>
        </div>
        <div class="rounded-[24px] border border-white/10 bg-white/[0.04] p-4">
          <p class="text-xs uppercase tracking-[0.24em] text-slate-400">已完成</p>
          <p class="mt-3 text-3xl font-semibold text-white">{{ metrics.completed }}</p>
          <p class="mt-2 text-xs text-slate-400">可直接预览和下载</p>
        </div>
        <div class="rounded-[24px] border border-white/10 bg-white/[0.04] p-4">
          <p class="text-xs uppercase tracking-[0.24em] text-slate-400">失败任务</p>
          <p class="mt-3 text-3xl font-semibold text-white">{{ metrics.failed }}</p>
          <p class="mt-2 text-xs text-slate-400">可重试或复用参数再建</p>
        </div>
        <div class="rounded-[24px] border border-white/10 bg-white/[0.04] p-4">
          <p class="text-xs uppercase tracking-[0.24em] text-slate-400">语义任务</p>
          <p class="mt-3 text-3xl font-semibold text-white">{{ metrics.semantic }}</p>
          <p class="mt-2 text-xs text-slate-400">已提供字幕或台词文本</p>
        </div>
        <div class="rounded-[24px] border border-white/10 bg-white/[0.04] p-4">
          <p class="text-xs uppercase tracking-[0.24em] text-slate-400">带时间戳字幕</p>
          <p class="mt-3 text-3xl font-semibold text-white">{{ metrics.timedSemantic }}</p>
          <p class="mt-2 text-xs text-slate-400">更适合模型按剧情切点规划</p>
        </div>
      </div>
    </div>

    <div v-if="errorMessage" class="rounded-[24px] border border-rose-500/20 bg-rose-500/10 p-4 text-sm text-rose-100">
      <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <p>{{ errorMessage }}</p>
        <button class="rounded-full border border-rose-300/30 px-4 py-2 text-xs font-medium text-rose-50 transition hover:bg-rose-500/20" type="button" @click="loadTasks">
          重新加载
        </button>
      </div>
    </div>

    <div v-if="loading" class="rounded-[24px] border border-white/10 bg-white/[0.04] p-10 text-center text-slate-300">
      正在加载任务列表...
    </div>

    <template v-else>
      <div v-if="filteredTasks.length === 0" class="rounded-[24px] border border-dashed border-white/15 bg-white/[0.04] p-10 text-center">
        <h3 class="text-lg font-medium text-white">没有匹配的任务</h3>
        <p class="mt-2 text-sm text-slate-300">尝试清空搜索和筛选，或者新建一个任务。</p>
        <button class="mt-5 rounded-full bg-rose-500 px-4 py-2 text-sm font-medium text-white transition duration-200 hover:bg-rose-400" type="button" @click="clearFilters">
          清空筛选
        </button>
      </div>

      <div v-else class="grid gap-5">
        <section v-for="group in groupedTasks" :key="group.key" class="grid gap-4">
          <div class="flex flex-wrap items-end justify-between gap-3">
            <div>
              <h3 class="text-lg font-semibold text-white">{{ group.title }}</h3>
              <p class="mt-1 text-sm text-slate-400">{{ group.description }}</p>
            </div>
            <span class="rounded-full border border-white/10 bg-white/[0.04] px-3 py-1 text-xs font-medium text-slate-200">{{ group.items.length }} 条</span>
          </div>
          <div v-if="group.items.length" class="grid gap-4 xl:grid-cols-2 2xl:grid-cols-3">
            <TaskCard v-for="task in group.items" :key="task.id" :task="task" @clone="handleClone" />
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
import { fetchTasks } from "@/api/tasks";
import type { TaskListItem, TaskStatus } from "@/types";
import PageHeader from "@/components/PageHeader.vue";
import TaskCard from "@/components/TaskCard.vue";
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

  const currentQuery = route.query;
  const nextQuery = query;
  const sameQuery =
    (normalizeQueryValue(currentQuery.q) || "") === (nextQuery.q || "") &&
    (normalizeQueryValue(currentQuery.status) || "") === (nextQuery.status || "") &&
    (normalizeQueryValue(currentQuery.platform) || "") === (nextQuery.platform || "") &&
    (normalizeQueryValue(currentQuery.sort) || "") === (nextQuery.sort || "");

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

watch([searchText, statusFilter, platformFilter, sortMode], () => {
  writeQuery();
  void loadTasks();
});

onMounted(async () => {
  await start();
});
</script>
