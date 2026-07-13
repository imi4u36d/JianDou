import { computed, type Ref } from "vue";
import { useAutoPilot } from "@/composables/workflow/useAutoPilot";
import type { WorkflowDetail } from "@/types";
import { useWorkflowAutoPilotSync } from "./useWorkflowAutoPilotSync";
import {
  workflowHeaderTags,
  workflowProgressPercent,
} from "../features/workflow-detail-presenters";

interface WorkflowStageReadiness {
  ready: boolean;
}

export interface WorkflowDetailHeaderOptions {
  workflowId: () => string;
  workflow: Ref<WorkflowDetail | null>;
  stages: Ref<WorkflowStageReadiness[]>;
  pollWorkflow: () => Promise<void>;
  showReturnButton: () => boolean;
  returnButtonLabel: () => string | undefined;
}

export function useWorkflowDetailHeader(options: WorkflowDetailHeaderOptions) {
  const autoPilot = useAutoPilot(options.workflowId);
  const { executionMode, recentLog } = useWorkflowAutoPilotSync({
    workflowId: options.workflowId,
    workflow: options.workflow,
    autoPilot,
    pollWorkflow: options.pollWorkflow,
  });
  const showReturnButton = computed(options.showReturnButton);
  const returnButtonLabel = computed(() => options.returnButtonLabel() || "任务详情");
  const canOpenResultView = computed(
    () => !showReturnButton.value && Boolean(options.workflow.value),
  );
  const progressPercent = computed(() =>
    workflowProgressPercent(options.workflow.value, options.stages.value),
  );
  const headerTags = computed(() =>
    workflowHeaderTags(options.workflow.value, progressPercent.value),
  );

  return {
    autoPilot,
    executionMode,
    recentLog,
    showReturnButton,
    returnButtonLabel,
    canOpenResultView,
    workflowProgressPercent: progressPercent,
    workflowHeaderTags: headerTags,
  };
}
