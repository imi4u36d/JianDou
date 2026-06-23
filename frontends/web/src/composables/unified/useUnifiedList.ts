/**
 * 统一列表组合式逻辑。
 * 仅拉取 workflows，归一化为 UnifiedListItem[]，
 * 提供统一的搜索、筛选、排序能力。
 */
import { computed, ref } from "vue";
import { useAuthSessionState } from "@/auth/session";
import { usePolling } from "@/composables/usePolling";
import { fetchWorkflows } from "@/features/workflows";
import { messageApi } from "@/composables/useMessage";
import type { WorkflowSummary } from "@/types";
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
  READY: 1,
  RUNNING: 2,
  PAUSED: 3,
  DRAFT: 4,
  COMPLETED: 5,
  FAILED: 6,
};

/**
 * 计算 workflow 的完成百分比。
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
 * 将 WorkflowSummary 归一化为 UnifiedListItem。
 */
function normalizeWorkflow(workflow: WorkflowSummary): UnifiedListItem {
  return {
    id: workflow.id,
    title: workflow.title || "未命名工作流",
    status: workflow.status,
    progress: workflowCompletionPercentage(workflow),
    createdAt: workflow.createdAt,
    updatedAt: workflow.updatedAt,
    aspectRatio: workflow.aspectRatio,
    currentStage: workflow.currentStage,
    executionMode: workflow.executionMode ?? undefined,
    autoPilotState: workflow.autoPilotState ?? undefined,
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

  const workflows = ref<WorkflowSummary[]>([]);
  const loading = ref(true);

  const searchText = ref("");
  const statusFilter = ref<UnifiedStatusFilter>("all");
  const sortMode = ref<UnifiedSortMode>("updated_desc");

  /**
   * 将 workflows 归一化为 UnifiedListItem[]。
   */
  const items = computed<UnifiedListItem[]>(() => {
    return workflows.value.map(normalizeWorkflow);
  });

  /**
   * 判断 item 是否匹配当前状态筛选。
   */
  function matchesStatusFilter(item: UnifiedListItem): boolean {
    if (statusFilter.value === "all") return true;
    if (statusFilter.value === "active") {
      const status = item.status.toLowerCase();
      return !["completed", "failed"].includes(status) || (item.progress > 0 && item.progress < 100);
    }
    if (statusFilter.value === "pending") {
      return item.status === "DRAFT" || item.status === "READY" || item.status === "RUNNING" || item.status === "PAUSED";
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
   * 加载数据（仅拉取 workflows）。
   */
  async function load() {
    if (!authState.isAuthenticated.value) {
      workflows.value = [];
      loading.value = false;
      return;
    }
    try {
      const fetchedWorkflows = await fetchWorkflows();
      workflows.value = fetchedWorkflows;
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
    workflows,
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
