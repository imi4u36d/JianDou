import { computed, onBeforeUnmount, ref, watch } from "vue";
import { requireAuth } from "@/auth/modal";
import { messageApi } from "@/composables/useMessage";
import { fetchWorkflowPage } from "@/features/workflows";
import type { WorkflowSummary } from "@/types";

type WorkflowProgressSource = object & Partial<Pick<
  WorkflowSummary,
  "storyboardVersionCount" | "characterSheetCount" | "selectedCharacterSheetCount" | "characterSheetVersionCount" | "keyframeVersionCount" | "videoVersionCount"
>>;

const DEFAULT_PAGE_SIZE = 10;
const MIN_PAGE_SIZE = 4;
const MAX_PAGE_SIZE = 30;

export function useWorkflowList() {
  const loadingWorkflows = ref(false);
  const loadingMoreWorkflows = ref(false);
  const workflowSearch = ref("");
  const workflowFilter = ref<"all" | "active" | "ready" | "done">("all");
  const workflowSearchInput = ref<HTMLInputElement | null>(null);
  const workflows = ref<WorkflowSummary[]>([]);
  const workflowTotal = ref(0);
  const workflowPageSize = ref(DEFAULT_PAGE_SIZE);
  let requestSerial = 0;
  let reloadTimer: number | null = null;

  function workflowCompletionPercentage(workflow: WorkflowProgressSource): number {
    const storyboardCount = Number(workflow.storyboardVersionCount ?? 0);
    const characterTotal = Number(workflow.characterSheetCount ?? 0);
    const characterSelected = Number(workflow.selectedCharacterSheetCount ?? workflow.characterSheetVersionCount ?? 0);
    const keyframeCount = Number(workflow.keyframeVersionCount ?? 0);
    const videoCount = Number(workflow.videoVersionCount ?? 0);
    const total = storyboardCount + characterTotal + keyframeCount + videoCount;
    if (total === 0) return 0;
    const completed = storyboardCount + characterSelected + keyframeCount + videoCount;
    return Math.round((completed / total) * 100);
  }

  const filteredWorkflows = computed(() => workflows.value);
  const hasMoreWorkflows = computed(() => workflows.value.length < workflowTotal.value);

  function focusWorkflowSearch() {
    workflowSearchInput.value?.focus();
  }

  function clearWorkflowSearch() {
    workflowSearch.value = "";
  }

  function mergeWorkflows(currentWorkflows: WorkflowSummary[], nextWorkflows: WorkflowSummary[]) {
    const currentMap = new Map(currentWorkflows.map((workflow) => [workflow.id, workflow]));
    const merged = [...currentWorkflows];
    for (const workflow of nextWorkflows) {
      const current = currentMap.get(workflow.id);
      if (current) {
        Object.assign(current, workflow);
      } else {
        currentMap.set(workflow.id, workflow);
        merged.push(workflow);
      }
    }
    return merged;
  }

  async function loadWorkflows(options: { mode?: "reset" | "append" | "refresh"; silent?: boolean } = {}) {
    const mode = options.mode ?? (workflows.value.length ? "refresh" : "reset");
    if (mode === "append" && (loadingWorkflows.value || loadingMoreWorkflows.value || !hasMoreWorkflows.value)) {
      return;
    }
    const authenticated = await requireAuth({
      title: "登录后查看视频",
      message: "视频任务只展示你的个人数据，请先登录或使用邀请码注册。",
    });
    if (!authenticated) {
      workflows.value = [];
      workflowTotal.value = 0;
      if (!options.silent) {
        messageApi.warning("登录后可查看视频任务。");
      }
      return;
    }
    const requestId = ++requestSerial;
    const offset = mode === "append" ? workflows.value.length : 0;
    const limit = mode === "refresh" ? Math.max(workflows.value.length, workflowPageSize.value) : workflowPageSize.value;
    if (mode === "append") {
      loadingMoreWorkflows.value = true;
    } else if (!options.silent) {
      loadingWorkflows.value = mode === "reset" || workflows.value.length === 0;
    }
    try {
      const page = await fetchWorkflowPage({
        q: workflowSearch.value.trim() || undefined,
        status: workflowFilter.value,
        sort: "created_desc",
        offset,
        limit,
      });
      if (requestId !== requestSerial) {
        return;
      }
      workflowTotal.value = page.total;
      workflows.value = mode === "append" ? mergeWorkflows(workflows.value, page.items) : page.items;
    } catch (error) {
      if (!options.silent) {
        messageApi.error(error instanceof Error ? error.message : "视频列表加载失败");
      }
    } finally {
      if (requestId === requestSerial) {
        loadingWorkflows.value = false;
        loadingMoreWorkflows.value = false;
      }
    }
  }

  function loadMoreWorkflows() {
    void loadWorkflows({ mode: "append" });
  }

  function setWorkflowPageSize(value: number) {
    const normalized = Math.max(MIN_PAGE_SIZE, Math.min(MAX_PAGE_SIZE, Math.round(value)));
    if (!Number.isFinite(normalized) || normalized === workflowPageSize.value) {
      return;
    }
    const previousPageSize = workflowPageSize.value;
    const hasLoadedItems = workflows.value.length > 0;
    workflowPageSize.value = normalized;
    if (
      hasLoadedItems
      && normalized > previousPageSize
      && workflows.value.length < normalized
      && !loadingWorkflows.value
      && !loadingMoreWorkflows.value
    ) {
      void loadWorkflows({ mode: "refresh", silent: true });
    }
  }

  function scheduleReload() {
    if (reloadTimer !== null) {
      window.clearTimeout(reloadTimer);
    }
    reloadTimer = window.setTimeout(() => {
      reloadTimer = null;
      void loadWorkflows({ mode: "reset" });
    }, 260);
  }

  watch([workflowSearch, workflowFilter], scheduleReload);

  onBeforeUnmount(() => {
    if (reloadTimer !== null) {
      window.clearTimeout(reloadTimer);
      reloadTimer = null;
    }
  });

  return {
    loadingWorkflows,
    loadingMoreWorkflows,
    workflowSearch,
    workflowFilter,
    workflowSearchInput,
    workflows,
    filteredWorkflows,
    hasMoreWorkflows,
    focusWorkflowSearch,
    clearWorkflowSearch,
    workflowCompletionPercentage,
    loadWorkflows,
    loadMoreWorkflows,
    setWorkflowPageSize,
  };
}
