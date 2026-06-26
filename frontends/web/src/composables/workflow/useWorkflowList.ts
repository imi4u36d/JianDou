import { ref, computed } from "vue";
import { requireAuth } from "@/auth/modal";
import { messageApi } from "@/composables/useMessage";
import { fetchWorkflows } from "@/features/workflows";
import type { WorkflowSummary } from "@/types";

type WorkflowProgressSource = object & Partial<Pick<
  WorkflowSummary,
  "storyboardVersionCount" | "characterSheetCount" | "selectedCharacterSheetCount" | "characterSheetVersionCount" | "keyframeVersionCount" | "videoVersionCount"
>>;

export function useWorkflowList() {
  const loadingWorkflows = ref(false);
  const workflowSearch = ref("");
  const workflowFilter = ref<"all" | "active" | "ready" | "done">("all");
  const workflowSearchInput = ref<HTMLInputElement | null>(null);
  const workflows = ref<WorkflowSummary[]>([]);

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

  function matchesWorkflowFilter(item: WorkflowSummary) {
    if (workflowFilter.value === "all") {
      return true;
    }
    const stage = String(item.currentStage || "").toLowerCase();
    const status = String(item.status || "").toLowerCase();
    const progress = workflowCompletionPercentage(item);
    if (workflowFilter.value === "done") {
      return stage === "final" || stage === "joined" || progress >= 100 || status === "completed";
    }
    if (workflowFilter.value === "ready") {
      return ["storyboard", "character", "keyframe", "video"].includes(stage) && progress > 0 && progress < 100;
    }
    return progress === 0 || ["pending", "running", "processing", "created"].includes(status);
  }

  const filteredWorkflows = computed(() => {
    const keyword = workflowSearch.value.trim().toLowerCase();
    return workflows.value.filter((item) => {
      if (!matchesWorkflowFilter(item)) {
        return false;
      }
      if (!keyword) {
        return true;
      }
      const haystack = [item.title, item.status, item.currentStage, item.aspectRatio].join(" ").toLowerCase();
      return haystack.includes(keyword);
    });
  });

  function focusWorkflowSearch() {
    workflowSearchInput.value?.focus();
  }

  function clearWorkflowSearch() {
    workflowSearch.value = "";
  }

  async function loadWorkflows() {
    const authenticated = await requireAuth({
      title: "登录后查看工作流",
      message: "阶段工作流只展示你的个人数据，请先登录或使用邀请码注册。",
    });
    if (!authenticated) {
      workflows.value = [];
      messageApi.warning("登录后可查看阶段工作流。");
      return;
    }
    loadingWorkflows.value = true;
    try {
      workflows.value = await fetchWorkflows();
    } catch (error) {
      messageApi.error(error instanceof Error ? error.message : "工作流列表加载失败");
    } finally {
      loadingWorkflows.value = false;
    }
  }

  return {
    loadingWorkflows,
    workflowSearch,
    workflowFilter,
    workflowSearchInput,
    workflows,
    filteredWorkflows,
    focusWorkflowSearch,
    clearWorkflowSearch,
    workflowCompletionPercentage,
    loadWorkflows,
  };
}
