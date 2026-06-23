/**
 * 统一列表组合式逻辑。
 * 并行拉取 tasks 和 workflows，归一化为 UnifiedListItem[]，
 * 提供统一的搜索、筛选、排序能力。
 */
import { computed, ref } from "vue";
import { useAuthSessionState } from "@/auth/session";
import { usePolling } from "@/composables/usePolling";
import { fetchTasks } from "@/features/tasks";
import { fetchWorkflows } from "@/features/workflows";
import { messageApi } from "@/composables/useMessage";
import type { TaskListItem, WorkflowSummary } from "@/types";
import type {
  UnifiedItemKind,
  UnifiedListItem,
  UnifiedKindFilter,
  UnifiedSortMode,
  UnifiedStatusFilter,
} from "@/types/unified-task";

const POLL_INTERVAL_MS = 5000;

/**
 * 活跃任务状态集合（用于统一筛选"进行中"）。
 */
const ACTIVE_TASK_STATUSES = new Set(["PENDING", "ANALYZING", "PLANNING", "RENDERING"]);

/**
 * 状态排序优先级（用于 status_desc 排序）。
 */
const STATUS_SORT_PRIORITY: Record<string, number> = {
  RENDERING: 0,
  ANALYZING: 1,
  PLANNING: 2,
  PENDING: 3,
  PAUSED: 4,
  FAILED: 5,
  COMPLETED: 6,
  // Workflow statuses
  DRAFT: 3,
  READY: 1,
};

/**
 * 计算 workflow 的完成百分比（复用 useWorkflowList 的逻辑）。
 */
function workflowCompletionPercentage(workflow: WorkflowSummary): number {
  const storyboardCount = Number(workflow.storyboardVersionCount ?? 0);
  const characterTotal = Number(workflow.characterSheetCount ?? 0);
  const characterSelected = Number(
    workflow.selectedCharacterSheetCount ?? workflow.characterSheetVersionCount ?? 0
  );
  const keyframeCount = Number(workflow.keyframeVersionCount ?? 0);
  const videoCount = Number(workflow.videoVersionCount ?? 0);
  const total = storyboardCount + characterTotal + keyframeCount + videoCount;
  if (total === 0) return 0;
  const completed = storyboardCount + characterSelected + keyframeCount + videoCount;
  return Math.round((completed / total) * 100);
}

/**
 * 将 TaskListItem 归一化为 UnifiedListItem。
 */
function normalizeTask(task: TaskListItem): UnifiedListItem {
  return {
    kind: "task" as UnifiedItemKind,
    id: task.id,
    title: task.title || "未命名任务",
    status: task.status,
    progress: Math.max(0, Math.min(100, Math.round(task.progress ?? 0))),
    createdAt: task.createdAt,
    updatedAt: task.updatedAt,
    aspectRatio: task.aspectRatio,
    thumbnailUrl: task.thumbnailUrl ?? null,
    taskType: task.taskType ?? undefined,
    currentStage: task.currentStage ?? undefined,
    task,
  };
}

/**
 * 将 WorkflowSummary 归一化为 UnifiedListItem。
 */
function normalizeWorkflow(workflow: WorkflowSummary): UnifiedListItem {
  return {
    kind: "workflow" as UnifiedItemKind,
    id: workflow.id,
    title: workflow.title || "未命名工作流",
    status: workflow.status,
    progress: workflowCompletionPercentage(workflow),
    createdAt: workflow.createdAt,
    updatedAt: workflow.updatedAt,
    aspectRatio: workflow.aspectRatio,
    thumbnailUrl: null,
    currentStage: workflow.currentStage,
    workflow,
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
  const workflows = ref<WorkflowSummary[]>([]);
  const loading = ref(true);

  const searchText = ref("");
  const statusFilter = ref<UnifiedStatusFilter>("all");
  const kindFilter = ref<UnifiedKindFilter>("all");
  const sortMode = ref<UnifiedSortMode>("updated_desc");

  /**
   * 将 tasks 和 workflows 合并归一化为 UnifiedListItem[]。
   */
  const items = computed<UnifiedListItem[]>(() => {
    const taskItems = tasks.value.map(normalizeTask);
    const workflowItems = workflows.value.map(normalizeWorkflow);
    return [...taskItems, ...workflowItems];
  });

  /**
   * 判断 item 是否匹配当前状态筛选。
   */
  function matchesStatusFilter(item: UnifiedListItem): boolean {
    if (statusFilter.value === "all") return true;
    if (statusFilter.value === "active") {
      if (item.kind === "task") return ACTIVE_TASK_STATUSES.has(item.status);
      // Workflow "active" = not completed, not failed, has progress > 0 or is in draft/ready
      const status = item.status.toLowerCase();
      return !["completed", "failed"].includes(status) || (item.progress > 0 && item.progress < 100);
    }
    if (statusFilter.value === "pending") {
      return item.status === "PENDING" || item.status === "PAUSED" || item.status === "DRAFT";
    }
    if (statusFilter.value === "completed") {
      return item.status === "COMPLETED" || item.progress >= 100;
    }
    if (statusFilter.value === "failed") {
      return item.status === "FAILED";
    }
    return true;
  }

  /**
   * 判断 item 是否匹配当前类型筛选。
   */
  function matchesKindFilter(item: UnifiedListItem): boolean {
    if (kindFilter.value === "all") return true;
    return item.kind === kindFilter.value;
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
        if (!matchesKindFilter(item)) return false;
        if (!keyword) return true;
        const haystack = [
          item.title,
          item.status,
          item.currentStage,
          item.aspectRatio,
          item.taskType,
        ]
          .filter(Boolean)
          .join(" ")
          .toLowerCase();
        return haystack.includes(keyword);
      })
      .sort(compareItems);
  });

  /**
   * 加载数据（并行拉取 tasks 和 workflows）。
   */
  async function load() {
    if (!authState.isAuthenticated.value) {
      tasks.value = [];
      workflows.value = [];
      loading.value = false;
      return;
    }
    try {
      const [fetchedTasks, fetchedWorkflows] = await Promise.all([
        fetchTasks({ sort: "updated_desc" }),
        fetchWorkflows(),
      ]);
      tasks.value = fetchedTasks;
      workflows.value = fetchedWorkflows;
    } catch (error) {
      // 静默处理轮询错误，首次加载时提示
      if (loading.value) {
        messageApi.error(error instanceof Error ? error.message : "列表加载失败");
      }
    } finally {
      loading.value = false;
    }
  }

  /**
   * 根据 kind 查找指定 ID 的项。
   */
  function findItem(id: string, kind?: UnifiedItemKind): UnifiedListItem | undefined {
    if (kind === "task") {
      return items.value.find((item) => item.kind === "task" && item.id === id);
    }
    if (kind === "workflow") {
      return items.value.find((item) => item.kind === "workflow" && item.id === id);
    }
    // kind 未指定时，两者都查找
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
    // 原始数据
    tasks,
    workflows,
    items,
    loading,
    // 筛选和排序
    searchText,
    statusFilter,
    kindFilter,
    sortMode,
    filteredItems,
    // 操作
    load,
    findItem,
    startPolling,
    stopPolling,
  };
}
