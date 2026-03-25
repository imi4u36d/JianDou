export type TaskStatus =
  | "PENDING"
  | "ANALYZING"
  | "PLANNING"
  | "RENDERING"
  | "COMPLETED"
  | "FAILED";

export interface TaskPlanClip {
  clipIndex: number;
  title: string;
  reason: string;
  startSeconds: number;
  endSeconds: number;
  durationSeconds: number;
}

export interface TaskSourceAssetSummary {
  assetId: string;
  originalFileName: string;
  storedFileName?: string;
  fileUrl: string;
  durationSeconds?: number | null;
  width?: number | null;
  height?: number | null;
  hasAudio?: boolean;
  mimeType?: string | null;
  sizeBytes?: number | null;
  sha256?: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface UploadResponse {
  assetId: string;
  fileName: string;
  fileUrl: string;
  sizeBytes: number;
}

export interface CreateTaskRequest {
  title: string;
  sourceAssetId: string;
  sourceFileName: string;
  platform: string;
  aspectRatio: "9:16" | "16:9";
  minDurationSeconds: number;
  maxDurationSeconds: number;
  outputCount: number;
  introTemplate: string;
  outroTemplate: string;
  creativePrompt?: string;
  transcriptText?: string;
}

export interface TaskPreset {
  key: string;
  name: string;
  description: string;
  defaultTitle: string;
  platform: string;
  aspectRatio: "9:16" | "16:9";
  minDurationSeconds: number;
  maxDurationSeconds: number;
  outputCount: number;
  introTemplate: string;
  outroTemplate: string;
  creativePrompt?: string;
}

export interface TaskCloneDraft {
  sourceTaskId: string;
  sourceAssetId: string;
  source?: TaskSourceAssetSummary | null;
  sourceFileName: string;
  title: string;
  platform: string;
  aspectRatio: "9:16" | "16:9";
  minDurationSeconds: number;
  maxDurationSeconds: number;
  outputCount: number;
  introTemplate: string;
  outroTemplate: string;
  creativePrompt?: string;
  transcriptText?: string;
  hasTimedTranscript?: boolean;
  transcriptCueCount?: number;
}

export interface TaskFilters {
  q?: string;
  status?: TaskStatus | "all";
  platform?: string | "all";
}

export interface TaskOutput {
  id: string;
  clipIndex: number;
  title: string;
  reason: string;
  startSeconds: number;
  endSeconds: number;
  durationSeconds: number;
  previewUrl: string;
  downloadUrl: string;
}

export interface TaskTraceEvent {
  timestamp: string;
  level: string;
  stage: string;
  event: string;
  message: string;
  payload: Record<string, unknown>;
}

export interface TaskListItem {
  id: string;
  title: string;
  status: TaskStatus;
  platform: string;
  progress: number;
  outputCount: number;
  createdAt: string;
  updatedAt: string;
  sourceFileName?: string;
  aspectRatio?: string;
  minDurationSeconds?: number;
  maxDurationSeconds?: number;
  retryCount?: number;
  startedAt?: string | null;
  finishedAt?: string | null;
  completedOutputCount?: number;
  hasTranscript?: boolean;
  hasTimedTranscript?: boolean;
}

export interface TaskDetail extends TaskListItem {
  sourceFileName: string;
  aspectRatio: string;
  minDurationSeconds: number;
  maxDurationSeconds: number;
  introTemplate: string;
  outroTemplate: string;
  creativePrompt?: string;
  errorMessage?: string | null;
  startedAt?: string | null;
  finishedAt?: string | null;
  retryCount?: number;
  completedOutputCount?: number;
  transcriptPreview?: string | null;
  hasTranscript?: boolean;
  hasTimedTranscript?: boolean;
  transcriptCueCount?: number;
  source?: TaskSourceAssetSummary | null;
  plan?: TaskPlanClip[];
  outputs: TaskOutput[];
}

export interface HealthModelSummary {
  provider: string;
  primary_model: string;
  fallback_model?: string | null;
  endpoint_host?: string;
  api_key_present: boolean;
  ready: boolean;
  temperature: number;
  max_tokens: number;
  config_errors: string[];
}

export interface HealthPlanningCapabilities {
  timed_transcript_supported: boolean;
  transcript_semantic_planning: boolean;
  fallback_heuristic_enabled: boolean;
}

export interface HealthRuntimeSummary {
  name: string;
  env: string;
  execution_mode: string;
  database_url: string;
  model_provider: string;
  storage_root: string;
  model: HealthModelSummary;
  planning_capabilities: HealthPlanningCapabilities;
}

export interface HealthResponse {
  ok: boolean;
  runtime: HealthRuntimeSummary;
}
