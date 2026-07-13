export type TaskStatus = "PENDING" | "PAUSED" | "ANALYZING" | "PLANNING" | "RENDERING" | "COMPLETED" | "FAILED";
export type EditingMode = "drama";

export interface TaskPlanClip {
  clipIndex: number; title: string; reason: string; startSeconds: number; endSeconds: number; durationSeconds: number;
  sourceAssetId?: string | null; sourceFileName?: string | null; segments?: TaskPlanSegment[];
  transitionStyle?: string | null; layoutStyle?: string | null; effectStyle?: string | null;
}

export interface TaskPlanSegment {
  sourceAssetId: string; sourceFileName: string; startSeconds: number; endSeconds: number; durationSeconds: number;
  shotRole?: string | null; segmentKind?: string | null; segmentRole?: string | null;
  frameTimestampSeconds?: number | null; framePreviewUrl?: string | null;
}

export interface TaskSourceAssetSummary {
  assetId: string; originalFileName: string; storedFileName?: string; fileUrl: string; thumbnailUrl?: string | null;
  durationSeconds?: number | null; width?: number | null; height?: number | null; hasAudio?: boolean;
  mimeType?: string | null; sizeBytes?: number | null; sha256?: string | null; createdAt: string; updatedAt: string;
}

export interface TaskDeleteResult { taskId: string; deleted: boolean; }
export interface RateTaskEffectRequest { effectRating: number; effectRatingNote?: string | null; }

export interface TaskFilters {
  q?: string;
  status?: TaskStatus | "all" | "active" | "pending" | "completed" | "failed";
  sort?: "updated_desc" | "created_desc" | "progress_desc" | "semantic_desc" | "status_desc" | "effect_rating_desc";
  taskType?: string; excludeTaskType?: string; offset?: number; limit?: number;
}

export interface TaskPaginatedResponse { items: TaskListItem[]; total: number; offset: number; limit: number; }

export interface TaskListItem {
  id: string;
  taskType?: "image_generation" | "image_to_image" | "character_sheet" | "video_generation" | string | null;
  title: string; status: TaskStatus; progress: number; createdAt: string; updatedAt: string;
  sourceFileName?: string; aspectRatio?: string; minDurationSeconds?: number; maxDurationSeconds?: number;
  retryCount?: number; taskSeed?: number | null; effectRating?: number | null; effectRatingNote?: string | null;
  ratedAt?: string | null; startedAt?: string | null; finishedAt?: string | null; completedOutputCount?: number;
  hasTranscript?: boolean; hasTimedTranscript?: boolean; sourceAssetCount?: number; editingMode?: EditingMode;
  isQueued?: boolean; queuePosition?: number | null; currentStage?: string | null; activeWorkerInstanceId?: string | null;
  plannedClipCount?: number; renderedClipCount?: number; diagnosisSeverity?: "info" | "low" | "medium" | "high";
  diagnosisCode?: string | null; diagnosisHint?: string | null; recommendedAction?: string | null;
  failureReason?: string | null; failureStage?: string | null; failureClipIndex?: number | null; thumbnailUrl?: string | null;
}
