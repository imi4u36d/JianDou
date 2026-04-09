export type TaskStatus =
  | "PENDING"
  | "PAUSED"
  | "ANALYZING"
  | "PLANNING"
  | "RENDERING"
  | "COMPLETED"
  | "FAILED";

export type EditingMode = "drama";

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

export interface CreateGenerationTaskRequest {
  title: string;
  creativePrompt?: string | null;
  aspectRatio: "9:16" | "16:9";
  textAnalysisModel?: string | null;
  videoModel?: string | null;
  videoSize?: string | null;
  videoDurationSeconds?: number | "auto" | null;
  minDurationSeconds?: number | null;
  maxDurationSeconds?: number | null;
  transcriptText?: string | null;
  stopBeforeVideoGeneration?: boolean | null;
}

export interface GenerateCreativePromptRequest {
  title: string;
  aspectRatio: "9:16" | "16:9";
  minDurationSeconds: number;
  maxDurationSeconds: number;
  introTemplate: string;
  outroTemplate: string;
  transcriptText?: string;
  sourceFileNames?: string[];
  editingMode?: EditingMode;
}

export interface GenerateCreativePromptResponse {
  prompt: string;
  source: string;
}

export interface GenerateScriptRequest {
  text: string;
  visualStyle?: string | null;
  textAnalysisModel?: string | null;
}

export interface GenerateScriptResponse {
  id: string;
  sourceText: string;
  visualStyle: string;
  outputFormat?: "markdown";
  scriptMarkdown: string;
  markdownFilePath?: string | null;
  markdownFileUrl?: string | null;
  downloadUrl?: string | null;
  source: string;
  createdAt: string;
  modelInfo?: GenerationModelInfo | null;
  callChain?: GenerationCallLogEntry[];
  metadata?: Record<string, unknown>;
}

export interface ProbeTextAnalysisModelRequest {
  textAnalysisModel?: string | null;
}

export interface ProbeTextAnalysisModelResponse {
  ready: boolean;
  requestedModel: string;
  resolvedModel: string;
  provider: string;
  family?: string | null;
  mode: string;
  endpointHost: string;
  latencyMs: number;
  messagePreview?: string | null;
  checkedAt: string;
}

export type GenerationMediaKind = "image" | "video";

export interface GenerationVersionInfo {
  version: number;
  label: string;
  isDefault?: boolean;
  supportedKinds?: GenerationMediaKind[];
  description?: string | null;
}

export interface GenerationVideoModelInfo {
  value: string;
  label: string;
  description?: string | null;
  isDefault?: boolean;
  provider?: string | null;
  family?: string | null;
  generationMode?: "t2v" | "i2v" | "vl" | null;
  supportedSizes?: string[];
  supportedDurations?: number[];
  aliases?: string[];
}

export interface GenerationTextAnalysisModelInfo {
  value: string;
  label: string;
  description?: string | null;
  isDefault?: boolean;
  provider?: string | null;
  family?: string | null;
  aliases?: string[];
}

export interface VideoModelUsageItem {
  model: string;
  label?: string | null;
  used: number;
  unit?: string | null;
  remaining: number | null;
  remainingUnit?: string | null;
  remainingLabel?: string | null;
  quota?: number | null;
  usedDurationSeconds?: number | null;
  provider?: string | null;
  source?: string | null;
  note?: string | null;
  updatedAt?: string | null;
}

export interface VideoModelUsageResponse {
  items: VideoModelUsageItem[];
  generatedAt?: string | null;
  updatedAt?: string | null;
}

export interface GenerationStylePresetOption {
  key: string;
  label: string;
  description?: string;
  mediaKinds?: GenerationMediaKind[];
}

export interface GenerationImageSizeOption {
  value: string;
  label: string;
  width?: number;
  height?: number;
}

export interface GenerationVideoSizeOption {
  value: string;
  label: string;
  width?: number;
  height?: number;
  supportedModels?: string[];
}

export interface GenerationVideoDurationOption {
  value: number;
  label: string;
  supportedModels?: string[];
}

export interface GenerationOptionsResponse {
  versions: number[];
  versionDetails?: GenerationVersionInfo[];
  defaultVersion?: number | null;
  stylePresets: GenerationStylePresetOption[];
  imageSizes: GenerationImageSizeOption[];
  videoModels: GenerationVideoModelInfo[];
  defaultVideoModel?: string | null;
  textAnalysisModels?: GenerationTextAnalysisModelInfo[];
  defaultTextAnalysisModel?: string | null;
  videoSizes: GenerationVideoSizeOption[];
  videoDurations: GenerationVideoDurationOption[];
  defaultStylePreset?: string | null;
  defaultImageSize?: string;
  defaultVideoSize?: string;
  defaultVideoDurationSeconds?: number | null;
}

export interface GenerateMediaRequest {
  prompt: string;
  mediaKind: GenerationMediaKind;
  version: number;
  stylePreset?: string | null;
  textAnalysisModel?: string | null;
  providerModel?: string | null;
  imageSize?: string;
  videoSize?: string;
  videoDurationSeconds?: number;
  minDurationSeconds?: number;
  maxDurationSeconds?: number;
}

export interface GenerationModelInfo {
  provider?: string | null;
  modelName?: string | null;
  providerModel?: string | null;
  requestedModel?: string | null;
  resolvedModel?: string | null;
  textAnalysisModel?: string | null;
  endpointHost?: string | null;
  temperature?: number | null;
  maxTokens?: number | null;
  timeoutSeconds?: number | null;
  strategyVersion?: number | null;
  strategyVersionLabel?: string | null;
  strategySummary?: string | null;
  mediaKind?: GenerationMediaKind | null;
}

export interface GenerationCallLogEntry {
  timestamp: string;
  stage: string;
  event: string;
  status: string;
  message: string;
  details?: Record<string, unknown>;
}

export interface GenerateMediaResponse {
  id: string;
  mediaKind: GenerationMediaKind;
  prompt: string;
  version: number;
  outputUrl: string;
  thumbnailUrl?: string | null;
  stylePreset?: string | null;
  providerModel?: string | null;
  mimeType?: string | null;
  width?: number | null;
  height?: number | null;
  durationSeconds?: number | null;
  createdAt?: string | null;
  modelInfo?: GenerationModelInfo | null;
  callChain?: GenerationCallLogEntry[];
  metadata?: Record<string, unknown>;
}

export interface TaskDeleteResult {
  taskId: string;
  deleted: boolean;
}

export interface TaskFilters {
  q?: string;
  status?: TaskStatus | "all";
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

export interface TaskMaterial {
  id: string;
  kind: "source" | "output";
  mediaType: "video" | "image" | "text";
  title: string;
  fileUrl: string;
  previewUrl?: string | null;
  mimeType?: string | null;
  durationSeconds?: number | null;
  width?: number | null;
  height?: number | null;
  sizeBytes?: number | null;
  createdAt?: string | null;
}

export interface TaskTraceEvent {
  timestamp: string;
  level: string;
  stage: string;
  event: string;
  message: string;
  payload: Record<string, unknown>;
}

export interface SeeddanceTaskQueryResult {
  taskId: string;
  status: string;
  videoUrl?: string | null;
  message?: string | null;
  payload: Record<string, unknown>;
}

export interface TaskListItem {
  id: string;
  title: string;
  status: TaskStatus;
  platform: string;
  progress: number;
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
}

export interface TaskDetail extends TaskListItem {
  sourceFileName: string;
  sourceFileNames?: string[];
  sourceAssetIds?: string[];
  editingMode?: EditingMode;
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
  storyboardScript?: string | null;
  materials?: TaskMaterial[];
  plan?: TaskPlanClip[];
  outputs: TaskOutput[];
}

export interface HealthModelSummary {
  provider: string;
  primary_model: string;
  fallback_model?: string | null;
  text_analysis_provider?: string | null;
  text_analysis_model?: string | null;
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
  textModel?: string | null;
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
