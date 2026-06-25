/**
 * 统一列表组合式逻辑。
 * 拉取任务，归一化为 UnifiedListItem[]，
 * 提供统一的搜索、筛选、排序能力。
 */
import { computed, ref } from "vue";
import { useAuthSessionState } from "@/auth/session";
import { usePolling } from "@/composables/usePolling";
import { fetchTasks } from "@/features/tasks";
import { messageApi } from "@/composables/useMessage";
import type { TaskListItem } from "@/types";
import type {
  UnifiedListItem,
  UnifiedSortMode,
  UnifiedStatusFilter,
} from "@/types/unified-task";

const POLL_INTERVAL_MS = 5000;

/**
 * 状态排序优先级（用于 status_desc 排序）。
 */
const STATUS_SORT_PRIORITY: Record<string, number> = {
  RENDERING: 1,
  PLANNING: 2,
  ANALYZING: 3,
  PENDING: 4,
  PAUSED: 5,
  COMPLETED: 5,
  FAILED: 6,
};

/**
 * 将 TaskListItem 归一化为 UnifiedListItem。
 */
function normalizeTask(task: TaskListItem): UnifiedListItem {
  return {
    id: task.id,
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

/**
 * 解析时间戳用于排序比较。
 */
function toTimestamp(value?: string | null): number {
  const timestamp = value ? new Date(value).getTime() : Number.NaN;
  return Number.isFinite(timestamp) ? timestamp : 0;
}

export function useUnifiedList() {
  const authState = useAuthSessionState();

  const tasks = ref<TaskListItem[]>([]);
  const loading = ref(true);

  const searchText = ref("");
  const statusFilter = ref<UnifiedStatusFilter>("all");
  const sortMode = ref<UnifiedSortMode>("updated_desc");

  /**
   * 将 tasks 归一化为 UnifiedListItem[]。
   */
  const items = computed<UnifiedListItem[]>(() => {
    return tasks.value.map(normalizeTask);
  });

  /**
   * 判断 item 是否匹配当前状态筛选。
   */
  function matchesStatusFilter(item: UnifiedListItem): boolean {
    if (statusFilter.value === "all") return true;
    if (statusFilter.value === "active") {
      return item.status === "PENDING" || item.status === "ANALYZING" || item.status === "PLANNING" || item.status === "RENDERING" || item.status === "PAUSED";
    }
    if (statusFilter.value === "pending") {
      return item.status === "PENDING";
    }
    if (statusFilter.value === "completed") {
      return item.status === "COMPLETED";
    }
    if (statusFilter.value === "failed") {
      return item.status === "FAILED";
    }
    return true;
  }

  /**
   * 排序比较函数。
   */
  function compareItems(a: UnifiedListItem, b: UnifiedListItem): number {
    if (sortMode.value === "updated_desc") {
      return toTimestamp(b.updatedAt) - toTimestamp(a.updatedAt);
    }
    if (sortMode.value === "created_desc") {
      return toTimestamp(b.createdAt) - toTimestamp(a.createdAt);
    }
    if (sortMode.value === "progress_desc") {
      return b.progress - a.progress || toTimestamp(b.updatedAt) - toTimestamp(a.updatedAt);
    }
    if (sortMode.value === "status_desc") {
      const pa = STATUS_SORT_PRIORITY[a.status] ?? 99;
      const pb = STATUS_SORT_PRIORITY[b.status] ?? 99;
      if (pa !== pb) return pa - pb;
      return toTimestamp(b.updatedAt) - toTimestamp(a.updatedAt);
    }
    return 0;
  }

  /**
   * 筛选 + 排序后的最终列表。
   */
  const filteredItems = computed<UnifiedListItem[]>(() => {
    const keyword = searchText.value.trim().toLowerCase();
    return items.value
      .filter((item) => {
        if (!matchesStatusFilter(item)) return false;
        if (!keyword) return true;
        const haystack = [
          item.title,
          item.status,
          item.currentStage,
          item.aspectRatio,
          item.executionMode,
        ]
          .filter(Boolean)
          .join(" ")
          .toLowerCase();
        return haystack.includes(keyword);
      })
      .sort(compareItems);
  });

  /**
   * 加载任务数据。
   */
  async function load() {
    if (!authState.isAuthenticated.value) {
      tasks.value = [];
      loading.value = false;
      return;
    }
    try {
      const fetchedTasks = await fetchTasks({ sort: sortMode.value });
      tasks.value = fetchedTasks;
    } catch (error) {
      if (loading.value) {
        messageApi.error(error instanceof Error ? error.message : "列表加载失败");
      }
    } finally {
      loading.value = false;
    }
  }

  /**
   * 根据 ID 查找项。
   */
  function findItem(id: string): UnifiedListItem | undefined {
    return items.value.find((item) => item.id === id);
  }

  // 轮询：每 5 秒刷新一次
  const polling = usePolling(load, POLL_INTERVAL_MS);

  /**
   * 启动轮询。
   */
  function startPolling() {
    polling.start(true);
  }

  /**
   * 停止轮询。
   */
  function stopPolling() {
    polling.stop();
  }

  return {
    tasks,
    items,
    loading,
    searchText,
    statusFilter,
    sortMode,
    filteredItems,
    load,
    findItem,
    startPolling,
    stopPolling,
  };
}
