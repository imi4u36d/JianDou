import { useWorkflowPreviewInteractions as useSharedWorkflowPreviewInteractions } from "@/composables/workflow/useWorkflowPreviewInteractions";
import {
  keyframePreviewFrames,
  stageVersionDisplayTitle,
} from "../features/workflow-detail-presenters";

export function useWorkflowPreviewInteractions() {
  return useSharedWorkflowPreviewInteractions({
    keyframePreviewFrames,
    stageVersionDisplayTitle,
  });
}
