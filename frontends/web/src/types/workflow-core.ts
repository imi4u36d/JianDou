import type { MaterialAssetLibraryItem } from "./workflow-material";
import type { StageVersion, WorkflowCharacterSheet, WorkflowClipSlot } from "./workflow-stage";

export interface CreateWorkflowRequest {
  title: string;
  transcriptText?: string | null;
  aspectRatio: string;
  textAnalysisModel: string;
  imageModel: string;
  videoModel: string;
  videoSize?: string | null;
  keyframeSeed?: number | null;
  videoSeed?: number | null;
  seed?: number | null;
  durationMode?: "auto" | "manual" | string | null;
  minDurationSeconds?: number | null;
  maxDurationSeconds?: number | null;
  executionMode?: "auto" | "manual" | string | null;
}

export interface UpdateWorkflowSettingsRequest {
  aspectRatio: string;
  textAnalysisModel: string;
  imageModel: string;
  videoModel: string;
  videoSize: string;
  keyframeSeed?: number | null;
  videoSeed?: number | null;
  durationMode?: "auto" | "manual" | string | null;
  minDurationSeconds?: number | null;
  maxDurationSeconds?: number | null;
}

export interface RateWorkflowRequest {
  effectRating: number;
  effectRatingNote?: string | null;
}

export interface WorkflowSummary {
  id: string;
  title: string;
  status: string;
  currentStage: string;
  aspectRatio: string;
  effectRating?: number | null;
  createdAt: string;
  updatedAt: string;
  storyboardVersionCount: number;
  characterSheetCount?: number;
  selectedCharacterSheetCount?: number;
  characterSheetVersionCount?: number;
  keyframeVersionCount: number;
  videoVersionCount: number;
  executionMode?: string | null;
  autoPilotState?: string | null;
  nextStage?: string | null;
  errorMessage?: string | null;
}

export interface WorkflowPaginatedResponse {
  items: WorkflowSummary[];
  total: number;
  offset: number;
  limit: number;
}

export interface WorkflowFilters {
  q?: string;
  status?: "all" | "active" | "ready" | "done" | string;
  sort?: "updated_desc" | "created_desc" | "status_desc";
  offset?: number;
  limit?: number;
}

export interface WorkflowDeleteResult {
  workflowId: string;
  deleted: boolean;
}

export interface WorkflowDetail extends Omit<WorkflowSummary, "storyboardVersionCount" | "keyframeVersionCount" | "videoVersionCount"> {
  transcriptText?: string | null;
  textAnalysisModel: string;
  imageModel: string;
  videoModel: string;
  videoSize?: string | null;
  keyframeSeed?: number | null;
  videoSeed?: number | null;
  seed?: number | null;
  durationMode?: string | null;
  minDurationSeconds?: number | null;
  maxDurationSeconds?: number | null;
  selectedStoryboardVersionId?: string | null;
  effectRatingNote?: string | null;
  ratedAt?: string | null;
  storyboardVersions: StageVersion[];
  characterSheets?: WorkflowCharacterSheet[] | null;
  clipSlots: WorkflowClipSlot[];
  finalResult?: MaterialAssetLibraryItem | null;
  autoPilotNextStage?: string | null;
  autoPilotErrorMessage?: string | null;
  autoPilotStartedAt?: string | null;
  autoPilotPausedAt?: string | null;
  autoPilotCurrentTask?: string | null;
  queuePosition?: number | null;
  queueSize?: number | null;
}
