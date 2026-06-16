export type UserRole = "ADMIN" | "USER";

export type UserStatus = "ACTIVE" | "DISABLED";

export type InviteStatus = "UNUSED" | "USED" | "REVOKED" | "EXPIRED";

export interface AuthenticatedUser {
  id: number;
  username: string;
  displayName: string;
  role: UserRole;
}

export interface AuthSession {
  authenticated: boolean;
  user: AuthenticatedUser | null;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface AdminUser {
  id: number;
  username: string;
  displayName: string;
  role: UserRole;
  status: UserStatus;
  taskConcurrencyLimit: number;
  runningTaskCount: number;
  queuedTaskCount: number;
  lastLoginAt?: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface AdminUserQuery {
  q?: string;
  role?: UserRole | "";
  status?: UserStatus | "";
}

export interface CreateAdminUserRequest {
  username: string;
  displayName: string;
  password: string;
  role: UserRole;
  status: UserStatus;
  taskConcurrencyLimit: number;
}

export interface UpdateAdminUserRequest {
  displayName: string;
  role: UserRole;
  status: UserStatus;
  taskConcurrencyLimit: number;
}

export interface UpdateAdminUserPasswordRequest {
  password: string;
}

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

export interface AdminModelConfigResponse {
  configSource: string;
  providers: AdminModelConfigProviderItem[];
}

export interface AdminModelConfigProviderKeyInput {
  key: string;
  apiKey: string;
}

export interface AdminModelConfigKeyUpdateRequest {
  providers: AdminModelConfigProviderKeyInput[];
}

export interface AdminCreditUser {
  id: number;
  userId?: number;
  username: string;
  displayName: string;
  role?: UserRole | string | null;
  status?: UserStatus | string | null;
  balance: number;
  totalConsumed: number;
  totalAdjusted: number;
  imageGenerationCount: number;
  videoGenerationCount: number;
  lastUsedAt?: string | null;
}

export interface AdminCreditUserQuery {
  q?: string;
}

export interface AdminCreditAdjustmentRequest {
  amount: number;
  reason: string;
}

export type AdminCreditTransactionType = "ADJUST" | "CONSUME" | "USAGE" | "REFUND" | string;

export interface AdminCreditTransaction {
  transactionId: string;
  userId: number;
  featureCode: string;
  transactionType: AdminCreditTransactionType;
  amountDelta: number;
  balanceBefore: number;
  balanceAfter: number;
  relatedRunId?: string | null;
  relatedTaskId?: string | null;
  relatedWorkflowId?: string | null;
  reason?: string | null;
  createdAt: string;
}

export interface AdminCreditRule {
  id: number;
  featureCode: string;
  displayName: string;
  cost: number;
  createdAt?: string | null;
  updatedAt?: string | null;
}

export interface AdminCreditRuleUpdateRequest {
  cost: number;
}

export interface AdminInviteActor {
  id: number;
  username: string;
  displayName: string;
}

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

export interface CreateAdminInviteRequest {
  role: UserRole;
}

export type TaskStatus =
  | "PENDING"
  | "PAUSED"
  | "ANALYZING"
  | "PLANNING"
  | "RENDERING"
  | "COMPLETED"
  | "FAILED";

export type AdminTaskSortMode =
  | "updated_desc"
  | "created_desc"
  | "progress_desc"
  | "status_desc"
  | "effect_rating_desc";

export interface AdminTaskListItem {
  id: string;
  title: string;
  status: TaskStatus;
  progress: number;
  createdAt: string;
  updatedAt: string;
  sourceFileName?: string | null;
  aspectRatio?: string | null;
  minDurationSeconds?: number | null;
  maxDurationSeconds?: number | null;
  retryCount?: number | null;
  startedAt?: string | null;
  finishedAt?: string | null;
  completedOutputCount?: number | null;
  taskSeed?: number | null;
  effectRating?: number | null;
  effectRatingNote?: string | null;
  ratedAt?: string | null;
  hasTranscript?: boolean;
  hasTimedTranscript?: boolean;
  sourceAssetCount?: number | null;
  editingMode?: string | null;
  isQueued?: boolean;
  queuePosition?: number | null;
  currentStage?: string | null;
  activeWorkerInstanceId?: string | null;
  plannedClipCount?: number | null;
  renderedClipCount?: number | null;
  diagnosisSeverity?: "info" | "low" | "medium" | "high";
  diagnosisCode?: string | null;
  diagnosisHint?: string | null;
  recommendedAction?: string | null;
  ownerUserId?: number | null;
  ownerUsername?: string | null;
  ownerDisplayName?: string | null;
  ownerRole?: UserRole | null | string;
}

export interface AdminTaskQuery {
  q?: string;
  status?: TaskStatus | "";
  sort?: AdminTaskSortMode;
}

export interface AdminTaskBatchFailure {
  taskId: string;
  reason: string;
}

export interface AdminTaskBatchResult {
  action: "terminate" | "retry" | "delete";
  requestedCount: number;
  succeededTaskIds: string[];
  failed: AdminTaskBatchFailure[];
}

export interface AdminOverviewCounts {
  totalTasks: number;
  queuedTasks: number;
  runningTasks: number;
  completedTasks: number;
  failedTasks: number;
  highRiskTasks: number;
  riskyTasks: number;
  semanticTasks: number;
  timedSemanticTasks: number;
  averageProgress: number;
}

export interface AdminOverviewQueue {
  generatedAt: string;
  queueLength: number;
  queueSnapshot: string[];
  runningWorkers: number;
  userQueues: AdminUserQueueOverview[];
  latestEvents: Array<Record<string, unknown>>;
  oldestQueuedTaskId: string;
  oldestQueuedTaskTitle: string;
  oldestQueuedTaskCreatedAt?: string | null;
}

export interface AdminUserQueueOverview {
  ownerUserId?: number | null;
  ownerUsername: string;
  ownerDisplayName: string;
  ownerRole: UserRole | "SYSTEM" | string;
  taskConcurrencyLimit: number;
  runningTaskCount: number;
  queuedTaskCount: number;
  oldestQueuedTaskId: string;
  oldestQueuedTaskTitle: string;
  oldestQueuedTaskCreatedAt?: string | null;
}

export interface AdminOverviewWorkers {
  items: Array<Record<string, unknown>>;
  onlineCount: number;
}

export interface AdminOverviewResponse {
  generatedAt: string;
  counts: AdminOverviewCounts;
  queue: AdminOverviewQueue;
  workers: AdminOverviewWorkers;
  recentTasks: AdminTaskListItem[];
  recentFailures: AdminTaskListItem[];
  recentRunningTasks: AdminTaskListItem[];
  recentTraceCount: number;
  modelReady: boolean;
  primaryModel?: string | null;
  textModel?: string | null;
}

// --- Task Detail types ---

export interface TaskPlanClip {
  clipIndex: number;
  title: string;
  reason: string;
  startSeconds: number;
  endSeconds: number;
  durationSeconds: number;
  sourceAssetId?: string | null;
  sourceFileName?: string | null;
}

export interface TaskTraceEvent {
  timestamp: string;
  level: string;
  stage: string;
  event: string;
  message: string;
  payload: Record<string, unknown>;
}

export interface AdminTraceEvent extends TaskTraceEvent {
  taskId: string;
  taskTitle?: string | null;
  taskStatus?: string | null;
}

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
  latestJoinName?: string | null;
  artifactDirectories?: TaskArtifactDirectories;
}

export interface TaskRequestSnapshot {
  taskType?: string | null;
  assetType?: string | null;
  title?: string | null;
  creativePrompt?: string | null;
  aspectRatio?: string | null;
  imageSize?: string | null;
  stylePreset?: string | null;
  textAnalysisModel?: string | null;
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
  referenceImageUrls?: string[] | null;
  referenceAssetIds?: string[] | null;
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
  thumbnailUrl?: string | null;
}

export interface TaskSourceAssetSummary {
  assetId: string;
  originalFileName: string;
  storedFileName?: string;
  fileUrl: string;
  thumbnailUrl?: string | null;
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

export interface TaskMaterial {
  id: string;
  kind: "source" | "output" | string;
  mediaType: "video" | "image" | "text" | string;
  title: string;
  fileUrl: string;
  previewUrl?: string | null;
  thumbnailUrl?: string | null;
  mimeType?: string | null;
  durationSeconds?: number | null;
  width?: number | null;
  height?: number | null;
  sizeBytes?: number | null;
  createdAt?: string | null;
}

export interface TaskDetail extends AdminTaskListItem {
  sourceFileName: string;
  sourceFileNames?: string[];
  sourceAssetIds?: string[];
  aspectRatio: string;
  minDurationSeconds: number;
  maxDurationSeconds: number;
  introTemplate: string;
  outroTemplate: string;
  creativePrompt?: string;
  errorMessage?: string | null;
  failureReason?: string | null;
  failureStage?: string | null;
  failureClipIndex?: number | null;
  startedAt?: string | null;
  finishedAt?: string | null;
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

export interface AdminTaskDiagnosisFinding {
  code: string;
  severity: "info" | "low" | "medium" | "high";
  title: string;
  detail: string;
}

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

// --- Health types ---

export interface HealthModelSummary {
  provider: string | null;
  primary_model: string | null;
  text_analysis_provider?: string | null;
  text_analysis_model?: string | null;
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
  model_provider: string | null;
  storage_root: string;
  model: HealthModelSummary;
  planning_capabilities: HealthPlanningCapabilities;
}

export interface HealthResponse {
  ok: boolean;
  runtime: HealthRuntimeSummary;
}
