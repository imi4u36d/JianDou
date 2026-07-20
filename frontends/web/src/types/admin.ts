/** Administrative users, tasks, model configuration, and credit contracts. */
import type { InviteStatus, UserRole, UserStatus } from "./auth";
import type { TaskFilters, TaskListItem, TaskStatus, TaskTraceEvent } from "./task";

export type {
  AdminModelConfigDefaults,
  AdminModelConfigKeyUpdateRequest,
  AdminModelConfigModelItem,
  AdminModelConfigProviderItem,
  AdminModelConfigProviderKeyInput,
  AdminModelConfigResponse,
  AdminModelConfigSummary,
  AdminModelConfigValidationResponse,
} from "./generation-model-config";
export type { AdminTaskDiagnosis, AdminTaskDiagnosisFinding } from "./task-execution";

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
  totalUsers: number;
  activeUsers: number;
  adminUsers: number;
  disabledUsers: number;
}

export interface AdminOverview {
  generatedAt: string;
  counts: AdminOverviewCounts;
  modelReady: boolean;
  primaryModel: string | null;
  textModel?: string | null;
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

export type AdminTaskFilters = TaskFilters;

export interface AdminUser {
  id: number;
  username: string;
  role: UserRole;
  status: UserStatus;
  taskConcurrencyLimit?: number | null;
  runningTaskCount?: number | null;
  queuedTaskCount?: number | null;
  lastLoginAt?: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface AdminInviteActor { id: number; username: string; }

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

export interface CreateAdminInviteRequest { role: UserRole; expiresAt?: string | null; }
export interface AdminTaskBatchFailure { taskId: string; error: string; }

export interface AdminTaskBatchResult {
  action: "retry" | "delete" | "terminate";
  requestedCount: number;
  succeededTaskIds: string[];
  failed: AdminTaskBatchFailure[];
}

export interface AdminTaskListItem extends TaskListItem {
  ownerUserId?: number | null;
  ownerUsername?: string | null;
  ownerRole?: UserRole | null | string;
  ownerStatus?: UserStatus | null | string;
  taskConcurrencyLimit?: number | null;
  runningTaskCount?: number | null;
  queuedTaskCount?: number | null;
}

export type AdminTaskSortMode = "updated_desc" | "created_desc" | "progress_desc" | "status_desc" | "effect_rating_desc";
export interface AdminTaskQuery { q?: string; status?: TaskStatus | ""; sort?: AdminTaskSortMode; offset?: number; limit?: number; }
export interface AdminUserQuery { q?: string; role?: UserRole | ""; status?: UserStatus | ""; offset?: number; limit?: number; }
export interface AdminPaginatedResponse<T> { items: T[]; total: number; offset: number; limit: number; }
export interface CreateAdminUserRequest { username: string; password: string; role: UserRole; status: UserStatus; taskConcurrencyLimit: number; }
export interface UpdateAdminUserRequest { role: UserRole; status: UserStatus; taskConcurrencyLimit: number; }
export interface UpdateAdminUserPasswordRequest { password: string; }

export interface AdminCreditUser {
  id: number;
  userId?: number;
  username: string;
  role?: UserRole | string | null;
  status?: UserStatus | string | null;
  balance: number;
  totalConsumed: number;
  totalAdjusted: number;
  imageGenerationCount: number;
  videoGenerationCount: number;
  lastUsedAt?: string | null;
}

export interface AdminCreditUserQuery { q?: string; }
export interface AdminCreditAdjustmentRequest { amount: number; reason: string; }
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

export interface AdminCreditRuleUpdateRequest { cost: number; }

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
  ownerRole: UserRole | "SYSTEM" | string;
  taskConcurrencyLimit: number;
  runningTaskCount: number;
  queuedTaskCount: number;
  oldestQueuedTaskId: string;
  oldestQueuedTaskTitle: string;
  oldestQueuedTaskCreatedAt?: string | null;
}

export interface AdminOverviewWorkers { items: Array<Record<string, unknown>>; onlineCount: number; }

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
