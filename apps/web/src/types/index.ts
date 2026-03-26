export type TaskStatus =
  | "PENDING"
  | "ANALYZING"
  | "PLANNING"
  | "RENDERING"
  | "COMPLETED"
  | "FAILED";

export type EditingMode = "drama" | "mixcut";

export interface TaskPlanClip {
  clipIndex: number;
  title: string;
  reason: string;
  startSeconds: number;
  endSeconds: number;
  durationSeconds: number;
  sourceAssetId?: string | null;
  sourceFileName?: string | null;
  segments?: TaskPlanSegment[];
  transitionStyle?: string | null;
  layoutStyle?: string | null;
  effectStyle?: string | null;
  mixcutTemplate?: string | null;
}

export interface TaskPlanSegment {
  sourceAssetId: string;
  sourceFileName: string;
  startSeconds: number;
  endSeconds: number;
  durationSeconds: number;
  shotRole?: string | null;
  segmentKind?: string | null;
  segmentRole?: string | null;
  frameTimestampSeconds?: number | null;
  framePreviewUrl?: string | null;
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
  sourceAssetId?: string;
  sourceFileName?: string;
  sourceAssetIds: string[];
  sourceFileNames: string[];
  editingMode?: EditingMode;
  mixcutContentType?: string;
  mixcutStylePreset?: string;
  platform: string;
  aspectRatio: "9:16" | "16:9";
  minDurationSeconds: number;
  maxDurationSeconds: number;
  outputCount: number;
  introTemplate: string;
  outroTemplate: string;
  creativePrompt?: string;
  transcriptText?: string;
  mixcutEnabled?: boolean;
}

export interface GenerateCreativePromptRequest {
  title: string;
  platform: string;
  aspectRatio: "9:16" | "16:9";
  minDurationSeconds: number;
  maxDurationSeconds: number;
  outputCount: number;
  introTemplate: string;
  outroTemplate: string;
  transcriptText?: string;
  sourceFileNames?: string[];
  editingMode?: EditingMode;
  mixcutEnabled?: boolean;
  mixcutContentType?: string;
  mixcutStylePreset?: string;
}

export interface GenerateCreativePromptResponse {
  prompt: string;
  source: string;
}

export interface TaskPreset {
  key: string;
  name: string;
  description: string;
  defaultTitle: string;
  editingMode?: EditingMode;
  platform: string;
  aspectRatio: "9:16" | "16:9";
  minDurationSeconds: number;
  maxDurationSeconds: number;
  outputCount: number;
  introTemplate: string;
  outroTemplate: string;
  creativePrompt?: string;
  mixcutContentType?: string;
  mixcutStylePreset?: string;
}

export interface TaskCloneDraft {
  sourceTaskId: string;
  sourceAssetId: string;
  sourceAssetIds?: string[];
  source?: TaskSourceAssetSummary | null;
  sourceFileName: string;
  sourceFileNames?: string[];
  sourceAssetCount?: number;
  editingMode?: EditingMode;
  mixcutEnabled?: boolean;
  mixcutContentType?: string;
  mixcutStylePreset?: string;
  mixcutTransitionStyle?: string;
  mixcutLayoutStyle?: string;
  mixcutEffectStyle?: string;
  mixcutTemplate?: string;
  sourceAssets?: TaskSourceAssetSummary[];
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

export interface TaskDeleteResult {
  taskId: string;
  deleted: boolean;
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
  sourceAssetCount?: number;
  editingMode?: EditingMode;
  mixcutEnabled?: boolean;
}

export interface TaskDetail extends TaskListItem {
  sourceFileName: string;
  sourceFileNames?: string[];
  sourceAssetIds?: string[];
  editingMode?: EditingMode;
  mixcutContentType?: string;
  mixcutStylePreset?: string;
  mixcutTransitionStyle?: string;
  mixcutLayoutStyle?: string;
  mixcutEffectStyle?: string;
  mixcutTemplate?: string;
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
  sourceAssets?: TaskSourceAssetSummary[];
  plan?: TaskPlanClip[];
  outputs: TaskOutput[];
}

export interface HealthModelSummary {
  provider: string;
  primary_model: string;
  fallback_model?: string | null;
  vision_model?: string | null;
  vision_fallback_model?: string | null;
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
  visual_content_analysis: boolean;
  visual_event_reasoning: boolean;
  subtitle_visual_fusion: boolean;
  audio_peak_signal: boolean;
  scene_boundary_signal: boolean;
  fusion_timeline_planning: boolean;
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

export interface AdminOverviewCounts {
  totalTasks: number;
  runningTasks: number;
  queuedTasks: number;
  completedTasks: number;
  failedTasks: number;
  semanticTasks: number;
  timedSemanticTasks: number;
  averageProgress: number;
}

export interface AdminOverview {
  generatedAt: string;
  counts: AdminOverviewCounts;
  modelReady: boolean;
  primaryModel: string;
  visionModel?: string | null;
  recentTasks: TaskListItem[];
  recentFailures: TaskListItem[];
  recentRunningTasks: TaskListItem[];
  recentTraceCount: number;
}

export interface AdminTraceEvent extends TaskTraceEvent {
  taskId: string;
  taskTitle?: string | null;
  taskStatus?: string | null;
}

export interface AdminTaskFilters extends TaskFilters {
  sort?: "updated_desc" | "created_desc" | "progress_desc" | "semantic_desc" | "status_desc";
}

export interface AdminTaskBatchFailure {
  taskId: string;
  reason: string;
}

export interface AdminTaskBatchResult {
  action: "retry" | "delete";
  requestedCount: number;
  succeededTaskIds: string[];
  failed: AdminTaskBatchFailure[];
}
