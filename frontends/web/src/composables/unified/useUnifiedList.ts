/**
 * 图片任务列表组合式逻辑。
 */
import { computed, ref, watch } from "vue";
import { useAuthSessionState } from "@/auth/session";
import { usePolling } from "@/composables/usePolling";
import { fetchTaskPage } from "@/features/tasks";
import { messageApi } from "@/composables/useMessage";
import type { TaskListItem, WorkflowSummary } from "@/types";
import type { UnifiedListItem, UnifiedStatusFilter } from "@/types/unified-task";

const POLL_INTERVAL_MS = 5000;
const IDLE_POLL_INTERVAL_MS = 15000;
const DEFAULT_PAGE_SIZE = 10;
const MIN_PAGE_SIZE = 4;
const MAX_PAGE_SIZE = 30;
const IMAGE_TASK_EXCLUDE_TYPE = "video_generation";
const ACTIVE_TASK_STATUSES = new Set(["PENDING", "ANALYZING", "PLANNING", "RENDERING", "PAUSED"]);

function normalizeTask(task: TaskListItem): UnifiedListItem {
  return {
    id: task.id,
    kind: "task",
    title: task.title || "未命名任务",
    status: task.status,
    progress: Number(task.progress ?? 0),
    createdAt: task.createdAt,
    updatedAt: task.updatedAt,
    aspectRatio: task.aspectRatio,
    thumbnailUrl: task.thumbnailUrl || null,
    currentStage: task.currentStage || undefined,
    task,
  };
}

function mergeTasks(currentTasks: TaskListItem[], nextTasks: TaskListItem[]) {
  const currentMap = new Map(currentTasks.map((task) => [task.id, task]));
  const merged = [...currentTasks];
  for (const task of nextTasks) {
    const current = currentMap.get(task.id);
    if (current) {
      Object.assign(current, task);
    } else {
      currentMap.set(task.id, task);
      merged.push(task);
    }
  }
  return merged;
}

export function useUnifiedList() {
  const authState = useAuthSessionState();

  const tasks = ref<TaskListItem[]>([]);
  const workflows = ref<WorkflowSummary[]>([]);
  const loading = ref(true);
  const loadingMore = ref(false);
  const total = ref(0);
  const pageSize = ref(DEFAULT_PAGE_SIZE);
  let requestSerial = 0;
  let reloadTimer: number | null = null;

  const searchText = ref("");
  const statusFilter = ref<UnifiedStatusFilter>("all");

  const items = computed<UnifiedListItem[]>(() => tasks.value.map(normalizeTask));
  const filteredItems = computed<UnifiedListItem[]>(() => items.value);

  const hasActiveItems = computed(() => tasks.value.some((task) => ACTIVE_TASK_STATUSES.has(task.status)));
  const hasMore = computed(() => tasks.value.length < total.value);

  async function load(options: { mode?: "reset" | "append" | "refresh"; silent?: boolean } = {}) {
    const mode = options.mode ?? (tasks.value.length ? "refresh" : "reset");
    if (mode === "append" && (loading.value || loadingMore.value || !hasMore.value)) {
      return;
    }
    if (!authState.isAuthenticated.value) {
      tasks.value = [];
      workflows.value = [];
      total.value = 0;
      loading.value = false;
      loadingMore.value = false;
      return;
    }
    const requestId = ++requestSerial;
    const offset = mode === "append" ? tasks.value.length : 0;
    const limit = mode === "refresh" ? Math.max(tasks.value.length, pageSize.value) : pageSize.value;
    if (mode === "append") {
      loadingMore.value = true;
    } else if (!options.silent) {
      loading.value = mode === "reset" || tasks.value.length === 0;
    }
    try {
      const page = await fetchTaskPage({
        q: searchText.value.trim() || undefined,
        status: statusFilter.value,
        sort: "created_desc",
        excludeTaskType: IMAGE_TASK_EXCLUDE_TYPE,
        offset,
        limit,
      });
      if (requestId !== requestSerial) {
        return;
      }
      total.value = page.total;
      tasks.value = mode === "append" ? mergeTasks(tasks.value, page.items) : page.items;
    } catch (error) {
      if (!options.silent && loading.value) {
        messageApi.error(error instanceof Error ? error.message : "任务列表加载失败");
      }
    } finally {
      if (requestId === requestSerial) {
        loading.value = false;
        loadingMore.value = false;
      }
    }
  }

  function loadMore() {
    void load({ mode: "append" });
  }

  function setPageSize(value: number) {
    const normalized = Math.max(MIN_PAGE_SIZE, Math.min(MAX_PAGE_SIZE, Math.round(value)));
    if (!Number.isFinite(normalized) || normalized === pageSize.value) {
      return;
    }
    const previousPageSize = pageSize.value;
    const hasLoadedItems = tasks.value.length > 0;
    pageSize.value = normalized;
    if (
      hasLoadedItems
      && normalized > previousPageSize
      && tasks.value.length < normalized
      && !loading.value
      && !loadingMore.value
    ) {
      void load({ mode: "refresh", silent: true });
    }
  }

  function scheduleReload() {
    if (reloadTimer !== null) {
      window.clearTimeout(reloadTimer);
    }
    reloadTimer = window.setTimeout(() => {
      reloadTimer = null;
      void load({ mode: "reset" });
    }, 260);
  }

  function findItem(id: string): UnifiedListItem | undefined {
    return items.value.find((item) => item.id === id);
  }

  const polling = usePolling(
    () => load({ mode: "refresh", silent: true }),
    () => (hasActiveItems.value ? POLL_INTERVAL_MS : IDLE_POLL_INTERVAL_MS),
  );

  watch([searchText, statusFilter], () => {
    scheduleReload();
  });

  function startPolling() {
    polling.start(true);
  }

  function stopPolling() {
    polling.stop();
    if (reloadTimer !== null) {
      window.clearTimeout(reloadTimer);
      reloadTimer = null;
    }
  }

  return {
    tasks,
    workflows,
    items,
    loading,
    loadingMore,
    searchText,
    statusFilter,
    filteredItems,
    hasMore,
    load,
    loadMore,
    setPageSize,
    findItem,
    startPolling,
    stopPolling,
  };
}
