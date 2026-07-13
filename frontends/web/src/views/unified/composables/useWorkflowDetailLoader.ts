import type { ComputedRef, Ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { messageApi } from "@/composables/useMessage";
import { hasMissingCharacterSheets } from "@/composables/workflow/useCharacterSheetUtils";
import { fetchWorkflow } from "@/features/workflows";
import {
  normalizeWorkflowCanvasStage,
  workflowCanvasStageFromCurrent,
  type WorkflowCanvasStageKey,
} from "@/features/workflows/summary";
import {
  workflowSettingsDraftFromDetail,
  type WorkflowSettingsDraft,
} from "@/features/workflows/workflow-settings";
import type { WorkflowDetail } from "@/types";

interface WorkflowDetailLoaderOptions {
  selectedWorkflowId: ComputedRef<string>;
  selectedWorkflow: Ref<WorkflowDetail | null>;
  loadingDetail: Ref<boolean>;
  activeCanvasStage: Ref<WorkflowCanvasStageKey>;
  selectedCanvasClipIndex: Ref<number | null>;
  workflowSettingsOpen: Ref<boolean>;
  workflowSettingsDraft: WorkflowSettingsDraft;
  applyPreviewSelections: (workflow: WorkflowDetail) => void;
  syncVideoSizeSelection: (target: WorkflowSettingsDraft, preferred?: string | null) => void;
  closeCharacterAssetPicker: () => void;
  reloadWorkflows: () => Promise<void>;
}

export function useWorkflowDetailLoader(options: WorkflowDetailLoaderOptions) {
  const route = useRoute();
  const router = useRouter();

  function syncWorkflowSettingsDraft(workflow: WorkflowDetail) {
    Object.assign(options.workflowSettingsDraft, workflowSettingsDraftFromDetail(workflow));
    options.syncVideoSizeSelection(options.workflowSettingsDraft, workflow.videoSize);
  }

  function applyWorkflowDrafts(workflow: WorkflowDetail | null) {
    if (!workflow) {
      options.workflowSettingsOpen.value = false;
      return;
    }
    syncWorkflowSettingsDraft(workflow);
    options.applyPreviewSelections(workflow);
  }

  async function loadWorkflowDetail(workflowId: string, loadOptions?: { quiet?: boolean }) {
    if (!(loadOptions?.quiet ?? false)) options.loadingDetail.value = true;
    try {
      options.selectedWorkflow.value = await fetchWorkflow(workflowId);
      const routeStage = normalizeWorkflowCanvasStage(route.query.stage);
      const resolvedStage = routeStage
        ?? workflowCanvasStageFromCurrent(options.selectedWorkflow.value, hasMissingCharacterSheets);
      options.activeCanvasStage.value = resolvedStage;
      if (resolvedStage !== "final" && routeStage !== resolvedStage) {
        router.replace({ query: { ...route.query, stage: resolvedStage } }).catch(() => {});
      }
      applyWorkflowDrafts(options.selectedWorkflow.value);
      const clipSlots = options.selectedWorkflow.value.clipSlots ?? [];
      if (clipSlots.length) {
        if (!clipSlots.some((slot) => slot.clipIndex === options.selectedCanvasClipIndex.value)) {
          options.selectedCanvasClipIndex.value = clipSlots[0].clipIndex;
        }
      } else {
        options.selectedCanvasClipIndex.value = null;
      }
    } catch (error) {
      messageApi.error(error instanceof Error ? error.message : "工作流详情加载失败");
      options.selectedWorkflow.value = null;
    } finally {
      options.loadingDetail.value = false;
    }
  }

  async function reloadCurrentWorkflow() {
    if (!options.selectedWorkflowId.value) return;
    await loadWorkflowDetail(options.selectedWorkflowId.value);
    await options.reloadWorkflows();
  }

  async function pollCurrentWorkflow() {
    if (!options.selectedWorkflowId.value) return;
    try {
      const data = await fetchWorkflow(options.selectedWorkflowId.value);
      if (options.selectedWorkflow.value) Object.assign(options.selectedWorkflow.value, data);
      else options.selectedWorkflow.value = data;
    } catch {
      // Polling is best-effort; the next explicit action reports any error.
    }
  }

  function switchCanvasStage(stage: string) {
    const normalizedStage = normalizeWorkflowCanvasStage(stage) ?? "storyboard";
    options.activeCanvasStage.value = normalizedStage;
    if (normalizedStage !== "final") {
      router.replace({ query: { ...route.query, stage: normalizedStage } }).catch(() => {});
    }
  }

  return {
    applyWorkflowDrafts,
    loadWorkflowDetail,
    pollCurrentWorkflow,
    reloadCurrentWorkflow,
    switchCanvasStage,
  };
}
