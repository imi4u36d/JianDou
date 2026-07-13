import { computed, watch, type Ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { messageApi } from "@/composables/useMessage";
import { hasMissingCharacterSheets } from "@/composables/workflow/useCharacterSheetUtils";
import { fetchWorkflow } from "@/features/workflows";
import {
  normalizeWorkflowCanvasStage,
  normalizeWorkflowDetailStage,
  workflowCanvasStageFromCurrent,
  type WorkflowCanvasStageKey,
  type WorkflowDetailRouteStageKey,
} from "@/features/workflows/summary";
import {
  workflowSettingsDraftFromDetail,
  type WorkflowSettingsDraft,
} from "@/features/workflows/workflow-settings";
import type { WorkflowDetail } from "@/types";

interface StageWorkflowDetailLoaderOptions {
  selectedWorkflow: Ref<WorkflowDetail | null>;
  loadingDetail: Ref<boolean>;
  activeCreateStage: Ref<WorkflowDetailRouteStageKey>;
  activeCanvasStage: Ref<WorkflowCanvasStageKey>;
  selectedCanvasClipIndex: Ref<number | null>;
  previewStoryboardVersionId: Ref<string>;
  workflowSettingsOpen: Ref<boolean>;
  workflowSettingsDraft: WorkflowSettingsDraft;
  syncVideoSizeSelection: (target: WorkflowSettingsDraft, preferred?: string | null) => void;
  applyPreviewSelections: (workflow: WorkflowDetail) => void;
  loadWorkflows: () => Promise<void>;
}

export function useStageWorkflowDetailLoader(options: StageWorkflowDetailLoaderOptions) {
  const route = useRoute();
  const router = useRouter();
  const selectedWorkflowId = computed(() => {
    const workflowId = route.params.workflowId;
    return typeof workflowId === "string" ? workflowId : "";
  });
  const showDetailLoadFailed = computed(
    () => Boolean(selectedWorkflowId.value && !options.selectedWorkflow.value && !options.loadingDetail.value),
  );

  function applyWorkflowDrafts(workflow: WorkflowDetail | null) {
    if (!workflow) {
      options.workflowSettingsOpen.value = false;
      return;
    }
    Object.assign(options.workflowSettingsDraft, workflowSettingsDraftFromDetail(workflow));
    options.syncVideoSizeSelection(options.workflowSettingsDraft, workflow.videoSize);
    options.applyPreviewSelections(workflow);
  }

  function openWorkflow(workflowId: string, preferredStage?: string | null) {
    const nextStage = normalizeWorkflowCanvasStage(preferredStage)
      ?? normalizeWorkflowDetailStage(route.query.stage)
      ?? options.activeCreateStage.value;
    options.activeCanvasStage.value = nextStage;
    if (nextStage === "final") {
      void router.push(`/video-tasks/${workflowId}`);
      return;
    }
    void router.push({ path: `/video-tasks/${workflowId}`, query: { stage: nextStage } });
  }

  function switchWorkflowStage(stage: WorkflowDetailRouteStageKey) {
    options.activeCreateStage.value = stage;
    options.activeCanvasStage.value = stage;
    if (!selectedWorkflowId.value || normalizeWorkflowDetailStage(route.query.stage) === stage) return;
    void router.replace({ path: route.path, query: { ...route.query, stage } });
  }

  function switchCanvasStage(stage: string) {
    const normalizedStage = normalizeWorkflowCanvasStage(stage) ?? "storyboard";
    options.activeCanvasStage.value = normalizedStage;
    if (normalizedStage === "final") {
      void router.push({ path: route.path, query: { ...route.query, stage: normalizedStage } });
    } else {
      switchWorkflowStage(normalizedStage);
    }
  }

  async function loadWorkflowDetail(workflowId: string) {
    options.loadingDetail.value = true;
    try {
      const workflow = await fetchWorkflow(workflowId);
      options.selectedWorkflow.value = workflow;
      const routeStage = normalizeWorkflowCanvasStage(route.query.stage);
      const resolvedStage = routeStage
        ?? workflowCanvasStageFromCurrent(workflow, hasMissingCharacterSheets);
      options.activeCreateStage.value = resolvedStage === "final" ? "video" : resolvedStage;
      options.activeCanvasStage.value = resolvedStage;
      if (resolvedStage !== "final" && routeStage !== resolvedStage) {
        await router.replace({ path: route.path, query: { ...route.query, stage: resolvedStage } });
      }
      applyWorkflowDrafts(workflow);
      const storyboardVersions = workflow.storyboardVersions ?? [];
      options.previewStoryboardVersionId.value =
        storyboardVersions.find((version) => version.selected)?.id
        ?? storyboardVersions[0]?.id ?? "";
      const clipSlots = workflow.clipSlots ?? [];
      if (!clipSlots.length) options.selectedCanvasClipIndex.value = null;
      else if (!clipSlots.some((slot) => slot.clipIndex === options.selectedCanvasClipIndex.value)) {
        options.selectedCanvasClipIndex.value = clipSlots[0].clipIndex;
      }
    } catch (error) {
      messageApi.error(error instanceof Error ? error.message : "工作流详情加载失败");
      options.selectedWorkflow.value = null;
    } finally {
      options.loadingDetail.value = false;
    }
  }

  async function reloadCurrentWorkflow() {
    if (!selectedWorkflowId.value) return;
    await loadWorkflowDetail(selectedWorkflowId.value);
    await options.loadWorkflows();
  }

  watch(
    () => route.query.stage,
    (stage) => {
      if (!selectedWorkflowId.value) return;
      const resolvedStage = normalizeWorkflowCanvasStage(stage);
      if (resolvedStage && resolvedStage !== options.activeCreateStage.value) {
        options.activeCreateStage.value = resolvedStage === "final" ? "video" : resolvedStage;
        options.activeCanvasStage.value = resolvedStage;
      }
    },
  );

  watch(
    selectedWorkflowId,
    (workflowId) => {
      options.workflowSettingsOpen.value = false;
      if (!workflowId) {
        options.selectedWorkflow.value = null;
        return;
      }
      void loadWorkflowDetail(workflowId);
    },
    { immediate: true },
  );

  return {
    applyWorkflowDrafts,
    loadWorkflowDetail,
    navigateToTaskList: () => router.push("/video-tasks").then(() => undefined),
    openWorkflow,
    reloadCurrentWorkflow,
    selectedWorkflowId,
    showDetailLoadFailed,
    switchCanvasStage,
    switchWorkflowStage,
  };
}
