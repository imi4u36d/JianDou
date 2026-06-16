import { ref, computed } from "vue";
import { requireAuth } from "@/auth/modal";
import { messageApi } from "@/composables/useMessage";
import { fetchWorkflows } from "@/features/workflows";
import type { WorkflowSummary } from "@/types";

export function useWorkflowList() {
  const loadingWorkflows = ref(false);
  const workflowSearch = ref("");
  const workflowSearchInput = ref<HTMLInputElement | null>(null);
  const workflows = ref<WorkflowSummary[]>([]);

  const filteredWorkflows = computed(() => {
    const keyword = workflowSearch.value.trim().toLowerCase();
    if (!keyword) return workflows.value;
    return workflows.value.filter((item) => {
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

  function workflowCompletionPercentage(workflow: WorkflowSummary): number {
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
    workflowSearchInput,
    workflows,
    filteredWorkflows,
    focusWorkflowSearch,
    clearWorkflowSearch,
    workflowCompletionPercentage,
    loadWorkflows,
  };
}
