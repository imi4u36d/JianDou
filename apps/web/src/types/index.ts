/**
 * 任务状态。
 */
/**
 * 索引相关类型定义。
 */
export type UserRole = "ADMIN" | "USER";

/**
 * 用户状态。
 */
export type UserStatus = "ACTIVE" | "DISABLED";

/**
 * 邀请码状态。
 */
export type InviteStatus = "UNUSED" | "USED" | "REVOKED" | "EXPIRED";

/**
 * 当前登录用户接口定义。
 */
export interface AuthenticatedUser {
  id: number;
  username: string;
  displayName: string;
  role: UserRole;
}

/**
 * 登录态接口定义。
 */
export interface AuthSession {
  authenticated: boolean;
  user: AuthenticatedUser | null;
}

/**
 * 登录请求接口定义。
 */
export interface LoginRequest {
  username: string;
  password: string;
}

/**
 * 激活邀请码请求接口定义。
 */
export interface ActivateInviteRequest {
  code: string;
  username: string;
  displayName: string;
  password: string;
}

export type TaskStatus =
  | "PENDING"
  | "PAUSED"
  | "ANALYZING"
  | "PLANNING"
  | "RENDERING"
  | "COMPLETED"
  | "FAILED";

/**
 * 编辑模式。
 */
export type EditingMode = "drama";

/**
 * 任务规划片段接口定义。
 */
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

/**
 * 任务规划Segment接口定义。
 */
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

/**
 * 任务来源素材摘要接口定义。
 */
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

/**
 * 上传响应体。
 */
export interface UploadResponse {
  assetId: string;
  fileName: string;
  fileUrl: string;
  sizeBytes: number;
}

/**
 * Create生成任务请求体。
 */
export interface CreateGenerationTaskRequest {
  title: string;
  creativePrompt?: string | null;
  aspectRatio: "9:16" | "16:9";
  textAnalysisModel?: string | null;
  visionModel?: string | null;
  imageModel?: string | null;
  videoModel?: string | null;
  videoSize?: string | null;
  seed?: number | null;
  videoDurationSeconds?: number | "auto" | null;
  outputCount?: number | "auto" | null;
  minDurationSeconds?: number | null;
  maxDurationSeconds?: number | null;
  transcriptText?: string | null;
  stopBeforeVideoGeneration?: boolean | null;
}

/**
 * Generate创意提示词请求体。
 */
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

/**
 * Generate创意提示词响应体。
 */
export interface GenerateCreativePromptResponse {
  prompt: string;
  source: string;
}

/**
 * Generate脚本请求体。
 */
export interface GenerateScriptRequest {
  text: string;
  visualStyle?: string | null;
  textAnalysisModel?: string | null;
}

/**
 * Generate脚本响应体。
 */
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

/**
 * 探测文本分析模型请求体。
 */
export interface ProbeTextAnalysisModelRequest {
  textAnalysisModel?: string | null;
}

/**
 * 探测文本分析模型响应体。
 */
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

/**
 * 生成媒体类型。
 */
export type GenerationMediaKind = "image" | "video";

/**
 * 生成视频模型信息接口定义。
 */
export interface GenerationVideoModelInfo {
  value: string;
  label: string;
  description?: string | null;
  isDefault?: boolean;
  provider?: string | null;
  family?: string | null;
  supportsSeed?: boolean;
  generationMode?: "t2v" | "i2v" | "vl" | null;
  supportedSizes?: string[];
  supportedDurations?: number[];
  aliases?: string[];
}

/**
 * 生成文本分析模型信息接口定义。
 */
export interface GenerationTextAnalysisModelInfo {
  value: string;
  label: string;
  description?: string | null;
  isDefault?: boolean;
  provider?: string | null;
  family?: string | null;
  supportsSeed?: boolean;
  aliases?: string[];
}

/**
 * 视频模型UsageItem接口定义。
 */
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

/**
 * 视频模型Usage响应体。
 */
export interface VideoModelUsageResponse {
  items: VideoModelUsageItem[];
  generatedAt?: string | null;
  updatedAt?: string | null;
}

/**
 * 生成风格预设选项接口定义。
 */
export interface GenerationStylePresetOption {
  key: string;
  label: string;
  description?: string;
  mediaKinds?: GenerationMediaKind[];
}

/**
 * 生成AspectRatio选项接口定义。
 */
export interface GenerationAspectRatioOption {
  value: string;
  label: string;
}

/**
 * 生成图像Size选项接口定义。
 */
export interface GenerationImageSizeOption {
  value: string;
  label: string;
  width?: number;
  height?: number;
}

/**
 * 生成视频Size选项接口定义。
 */
export interface GenerationVideoSizeOption {
  value: string;
  label: string;
  width?: number;
  height?: number;
  supportedModels?: string[];
}

/**
 * 生成视频时长选项接口定义。
 */
export interface GenerationVideoDurationOption {
  value: number;
  label: string;
  supportedModels?: string[];
}

/**
 * 生成选项响应体。
 */
export interface GenerationOptionsResponse {
  aspectRatios?: GenerationAspectRatioOption[];
  defaultAspectRatio?: string | null;
  stylePresets: GenerationStylePresetOption[];
  imageSizes: GenerationImageSizeOption[];
  videoModels: GenerationVideoModelInfo[];
  defaultVideoModel?: string | null;
  textAnalysisModels?: GenerationTextAnalysisModelInfo[];
  defaultTextAnalysisModel?: string | null;
  visionModels?: GenerationTextAnalysisModelInfo[];
  defaultVisionModel?: string | null;
  imageModels?: GenerationTextAnalysisModelInfo[];
  videoSizes: GenerationVideoSizeOption[];
  videoDurations: GenerationVideoDurationOption[];
  defaultStylePreset?: string | null;
  defaultImageSize?: string;
  defaultVideoSize?: string;
  defaultVideoDurationSeconds?: number | null;
}

/**
 * 管理端模型配置汇总接口定义。
 */
export interface AdminModelConfigSummary {
  providerCount: number;
  vendorCount: number;
  modelCount: number;
  readyModelCount: number;
  readyTextModelCount: number;
  readyVisionModelCount: number;
  readyImageModelCount: number;
  readyVideoModelCount: number;
}

/**
 * 管理端模型配置默认值接口定义。
 */
export interface AdminModelConfigDefaults {
  aspectRatio: string;
  stylePreset: string;
  imageSize: string;
  videoSize: string;
  videoDurationSeconds: number;
  timeoutSeconds: number;
  temperature: number;
  maxTokens: number;
}

/**
 * 管理端 provider 配置项接口定义。
 */
export interface AdminModelConfigProviderItem {
  key: string;
  provider: string;
  vendor: string;
  kinds: string[];
  baseUrl: string;
  taskBaseUrl: string;
  endpointHost: string;
  taskEndpointHost: string;
  apiKeyConfigured: boolean;
  baseUrlConfigured: boolean;
  taskBaseUrlConfigured: boolean;
  extras: Record<string, string>;
  modelNames: string[];
}

/**
 * 管理端模型配置项接口定义。
 */
export interface AdminModelConfigModelItem {
  name: string;
  label: string;
  kind: string;
  provider: string;
  vendor: string;
  family: string;
  description: string;
  fallbackModel: string;
  supportsSeed: boolean;
  supportsResponsesApi: boolean;
  prefersChatCompletionsForVision: boolean;
  generationMode: string;
  supportedSizes: string[];
  supportedDurations: number[];
  ready: boolean;
  configSource: string;
  endpointHost: string;
  taskEndpointHost: string;
  issues: string[];
}

/**
 * 管理端模型配置响应体接口定义。
 */
export interface AdminModelConfigResponse {
  configSource: string;
  summary: AdminModelConfigSummary;
  defaults: AdminModelConfigDefaults;
  providers: AdminModelConfigProviderItem[];
  models: AdminModelConfigModelItem[];
  configErrors: string[];
}

/**
 * 管理端模型配置 key 输入项接口定义。
 */
export interface AdminModelConfigProviderKeyInput {
  key: string;
  apiKey: string;
}

/**
 * 管理端模型配置 key 更新请求体接口定义。
 */
export interface AdminModelConfigKeyUpdateRequest {
  providers: AdminModelConfigProviderKeyInput[];
}

/**
 * 管理端模型配置校验响应体接口定义。
 */
export interface AdminModelConfigValidationResponse {
  valid: boolean;
  snapshot: AdminModelConfigResponse;
}

/**
 * Generate媒体请求体。
 */
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

/**
 * 生成模型信息接口定义。
 */
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

/**
 * 生成调用日志条目接口定义。
 */
export interface GenerationCallLogEntry {
  timestamp: string;
  stage: string;
  event: string;
  status: string;
  message: string;
  details?: Record<string, unknown>;
}

/**
 * Generate媒体响应体。
 */
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

/**
 * 任务删除接口定义。
 */
export interface TaskDeleteResult {
  taskId: string;
  deleted: boolean;
}

/**
 * 评分任务效果请求体。
 */
export interface RateTaskEffectRequest {
  effectRating: number;
  effectRatingNote?: string | null;
}

/**
 * 任务筛选条件接口定义。
 */
export interface TaskFilters {
  q?: string;
  status?: TaskStatus | "all";
  sort?: "updated_desc" | "created_desc" | "progress_desc" | "semantic_desc" | "status_desc" | "effect_rating_desc";
}

/**
 * 任务输出接口定义。
 */
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

/**
 * 任务素材接口定义。
 */
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

/**
 * 任务追踪事件接口定义。
 */
export interface TaskTraceEvent {
  timestamp: string;
  level: string;
  stage: string;
  event: string;
  message: string;
  payload: Record<string, unknown>;
}

/**
 * Seedance任务查询接口定义。
 */
export interface SeedanceTaskQueryResult {
  taskId: string;
  status: string;
  videoUrl?: string | null;
  message?: string | null;
  payload: Record<string, unknown>;
}

/**
 * 任务列表Item接口定义。
 */
export interface TaskListItem {
  id: string;
  title: string;
  status: TaskStatus;
  progress: number;
  createdAt: string;
  updatedAt: string;
  sourceFileName?: string;
  aspectRatio?: string;
  minDurationSeconds?: number;
  maxDurationSeconds?: number;
  retryCount?: number;
  taskSeed?: number | null;
  effectRating?: number | null;
  effectRatingNote?: string | null;
  ratedAt?: string | null;
  startedAt?: string | null;
  finishedAt?: string | null;
  completedOutputCount?: number;
  hasTranscript?: boolean;
  hasTimedTranscript?: boolean;
  sourceAssetCount?: number;
  editingMode?: EditingMode;
  isQueued?: boolean;
  queuePosition?: number | null;
  currentStage?: string | null;
  activeWorkerInstanceId?: string | null;
  plannedClipCount?: number;
  renderedClipCount?: number;
  diagnosisSeverity?: "info" | "low" | "medium" | "high";
  diagnosisCode?: string | null;
  diagnosisHint?: string | null;
  recommendedAction?: string | null;
}

/**
 * 任务监控摘要接口定义。
 */
export interface TaskMonitoringSummary {
  currentStage?: string | null;
  activeAttemptStatus?: string | null;
  activeWorkerInstanceId?: string | null;
  resumeFromStage?: string | null;
  resumeFromClipIndex?: number | null;
  plannedClipCount?: number;
  renderedClipCount?: number;
  contiguousRenderedClipCount?: number;
  latestRenderedClipIndex?: number;
  latestVideoOutputUrl?: string | null;
  latestJoinName?: string | null;
  latestJoinOutputUrl?: string | null;
  latestJoinClipIndex?: number | null;
  latestJoinClipIndices?: unknown[];
  latestTrace?: Record<string, unknown>;
  latestStageRun?: Record<string, unknown>;
  latestVideoOutput?: Record<string, unknown>;
  latestJoinOutput?: Record<string, unknown>;
  activeAttempt?: Record<string, unknown>;
  storyboardFileUrl?: string | null;
  artifactDirectories?: TaskArtifactDirectories;
}

/**
 * 任务时长诊断片段接口定义。
 */
export interface TaskDurationDiagnosticClip {
  clipIndex: number;
  durationSource?: string | null;
  scriptMinDurationSeconds?: number | null;
  scriptMaxDurationSeconds?: number | null;
  plannedTargetDurationSeconds?: number | null;
  plannedMinDurationSeconds?: number | null;
  plannedMaxDurationSeconds?: number | null;
  requestedDurationSeconds?: number | null;
  appliedDurationSeconds?: number | null;
  actualDurationSeconds?: number | null;
  status?: "pending" | "rendered" | string | null;
}

/**
 * 任务产物Directories接口定义。
 */
export interface TaskArtifactDirectories {
  storageRoot?: string | null;
  baseRelativeDir?: string | null;
  baseAbsoluteDir?: string | null;
  runningRelativeDir?: string | null;
  runningAbsoluteDir?: string | null;
  joinedRelativeDir?: string | null;
  joinedAbsoluteDir?: string | null;
  runningPublicBaseUrl?: string | null;
  joinedPublicBaseUrl?: string | null;
  storyboardFileName?: string | null;
  firstFramePattern?: string | null;
  lastFramePattern?: string | null;
  clipPattern?: string | null;
  joinPattern?: string | null;
}

/**
 * 管理任务诊断Finding接口定义。
 */
export interface AdminTaskDiagnosisFinding {
  code: string;
  severity: "info" | "low" | "medium" | "high";
  title: string;
  detail: string;
}

/**
 * 管理任务诊断接口定义。
 */
export interface AdminTaskDiagnosis {
  taskId: string;
  title: string;
  status: TaskStatus;
  severity: "info" | "low" | "medium" | "high";
  summary: string;
  findings: AdminTaskDiagnosisFinding[];
  recovery: Record<string, unknown>;
  continuity: Record<string, unknown>;
  outputs: Record<string, unknown>;
  queue: Record<string, unknown>;
}

/**
 * 任务请求快照对象。
 */
export interface TaskRequestSnapshot {
  taskType?: string | null;
  title?: string | null;
  creativePrompt?: string | null;
  aspectRatio?: string | null;
  stylePreset?: string | null;
  textAnalysisModel?: string | null;
  visionModel?: string | null;
  imageModel?: string | null;
  videoModel?: string | null;
  videoSize?: string | null;
  seed?: number | null;
  videoDurationSeconds?: number | "auto" | null;
  outputCount?: number | "auto" | null;
  minDurationSeconds?: number | null;
  maxDurationSeconds?: number | null;
  transcriptText?: string | null;
  stopBeforeVideoGeneration?: boolean | null;
}

/**
 * 任务接口定义。
 */
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
  artifactDirectories?: TaskArtifactDirectories;
  executionContext?: Record<string, unknown>;
  requestSnapshot?: TaskRequestSnapshot;
  durationDiagnostics?: TaskDurationDiagnosticClip[];
  plan?: TaskPlanClip[];
  monitoring?: TaskMonitoringSummary;
  outputs: TaskOutput[];
}

/**
 * 健康检查模型摘要接口定义。
 */
export interface HealthModelSummary {
  provider: string | null;
  primary_model: string | null;
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

/**
 * 健康检查规划能力接口定义。
 */
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

/**
 * 健康检查运行时摘要接口定义。
 */
export interface HealthRuntimeSummary {
  name: string;
  env: string;
  execution_mode: string;
  database_url: string;
  model_provider: string | null;
  storage_root: string;
  model: HealthModelSummary;
  planning_capabilities: HealthPlanningCapabilities;
}

/**
 * 健康检查响应体。
 */
export interface HealthResponse {
  ok: boolean;
  runtime: HealthRuntimeSummary;
}

/**
 * 管理概览Counts接口定义。
 */
export interface AdminOverviewCounts {
  totalTasks: number;
  runningTasks: number;
  queuedTasks: number;
  completedTasks: number;
  failedTasks: number;
  highRiskTasks: number;
  riskyTasks: number;
  semanticTasks: number;
  timedSemanticTasks: number;
  averageProgress: number;
}

/**
 * 管理概览接口定义。
 */
export interface AdminOverview {
  generatedAt: string;
  counts: AdminOverviewCounts;
  modelReady: boolean;
  primaryModel: string | null;
  textModel?: string | null;
  visionModel?: string | null;
  recentTasks: TaskListItem[];
  recentFailures: TaskListItem[];
  recentRunningTasks: TaskListItem[];
  recentTraceCount: number;
}

/**
 * 管理追踪事件接口定义。
 */
export interface AdminTraceEvent extends TaskTraceEvent {
  taskId: string;
  taskTitle?: string | null;
  taskStatus?: string | null;
}

/**
 * 管理任务筛选条件接口定义。
 */
export interface AdminTaskFilters extends TaskFilters {
}

/**
 * 管理端用户接口定义。
 */
export interface AdminUser {
  id: number;
  username: string;
  displayName: string;
  role: UserRole;
  status: UserStatus;
  lastLoginAt?: string | null;
  createdAt: string;
  updatedAt: string;
}

/**
 * 管理端邀请码参与人接口定义。
 */
export interface AdminInviteActor {
  id: number;
  username: string;
  displayName: string;
}

/**
 * 管理端邀请码接口定义。
 */
export interface AdminInvite {
  id: number;
  code: string;
  role: UserRole;
  status: InviteStatus;
  expiresAt?: string | null;
  createdBy?: AdminInviteActor | null;
  usedBy?: AdminInviteActor | null;
  usedAt?: string | null;
  createdAt: string;
  updatedAt: string;
}

/**
 * 创建管理端邀请码请求接口定义。
 */
export interface CreateAdminInviteRequest {
  role: UserRole;
  expiresAt?: string | null;
}

/**
 * 管理任务批量失败接口定义。
 */
export interface AdminTaskBatchFailure {
  taskId: string;
  reason: string;
}

/**
 * 管理任务批量接口定义。
 */
export interface AdminTaskBatchResult {
  action: "retry" | "delete";
  requestedCount: number;
  succeededTaskIds: string[];
  failed: AdminTaskBatchFailure[];
}
