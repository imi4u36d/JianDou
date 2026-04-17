/**
 * 管理相关 API 请求封装。
 */
import { deleteJson, getJson, postJson } from "./client";
import type {
  AdminInvite,
  AdminModelConfigKeyUpdateRequest,
  AdminModelConfigResponse,
  AdminModelConfigValidationResponse,
  AdminOverview,
  AdminTaskDiagnosis,
  AdminTaskBatchResult,
  AdminTaskFilters,
  AdminTraceEvent,
  AdminUser,
  CreateAdminInviteRequest,
  RateTaskEffectRequest,
  TaskDeleteResult,
  TaskDetail,
  TaskListItem,
  TaskTraceEvent,
} from "@/types";

export async function fetchAdminOverview() {
  return getJson<AdminOverview>("/admin/overview");
}

export async function fetchAdminModelConfig() {
  return getJson<AdminModelConfigResponse>("/admin/model-config");
}

export async function validateAdminModelConfig(payload: AdminModelConfigKeyUpdateRequest) {
  return postJson<AdminModelConfigValidationResponse>("/admin/model-config/validate", payload);
}

export async function saveAdminModelConfigKeys(payload: AdminModelConfigKeyUpdateRequest) {
  return postJson<AdminModelConfigResponse>("/admin/model-config/keys", payload);
}

/**
 * 获取管理任务。
 * @param filters 筛选条件值
 */
export function fetchAdminTasks(filters?: AdminTaskFilters) {
  const params = new URLSearchParams();
  if (filters?.q?.trim()) {
    params.set("q", filters.q.trim());
  }
  if (filters?.status && filters.status !== "all") {
    params.set("status", filters.status);
  }
  if (filters?.sort?.trim()) {
    params.set("sort", filters.sort.trim());
  }
  const query = params.toString();
  return getJson<TaskListItem[]>(query ? `/admin/tasks?${query}` : "/admin/tasks");
}

/**
 * 获取管理任务。
 * @param taskId 任务标识
 */
export function fetchAdminTask(taskId: string) {
  return getJson<TaskDetail>(`/admin/tasks/${taskId}`);
}

/**
 * 获取管理任务诊断。
 * @param taskId 任务标识
 */
export function fetchAdminTaskDiagnosis(taskId: string) {
  return getJson<AdminTaskDiagnosis>(`/admin/tasks/${taskId}/diagnosis`);
}

/**
 * 获取管理任务追踪。
 * @param taskId 任务标识
 * @param limit 返回的最大条目数
 */
export function fetchAdminTaskTrace(taskId: string, limit = 500) {
  return getJson<TaskTraceEvent[]>(`/admin/tasks/${taskId}/trace?limit=${limit}`);
}

/**
 * 获取管理Traces。
 */
export function fetchAdminTraces(params?: {
  limit?: number;
  taskId?: string;
  stage?: string;
  level?: string;
  q?: string;
}) {
  const query = new URLSearchParams();
  if (params?.limit) {
    query.set("limit", String(params.limit));
  }
  if (params?.taskId?.trim()) {
    query.set("task_id", params.taskId.trim());
  }
  if (params?.stage?.trim()) {
    query.set("stage", params.stage.trim());
  }
  if (params?.level?.trim()) {
    query.set("level", params.level.trim());
  }
  if (params?.q?.trim()) {
    query.set("q", params.q.trim());
  }
  const search = query.toString();
  return getJson<AdminTraceEvent[]>(search ? `/admin/traces?${search}` : "/admin/traces");
}

/**
 * 重试管理任务。
 * @param taskId 任务标识
 */
export function retryAdminTask(taskId: string) {
  return postJson<TaskDetail>(`/admin/tasks/${taskId}/retry`, {});
}

/**
 * 终止管理任务。
 * @param taskId 任务标识
 */
export function terminateAdminTask(taskId: string) {
  return postJson<TaskDetail>(`/admin/tasks/${taskId}/terminate`, {});
}

/**
 * 删除管理任务。
 * @param taskId 任务标识
 */
export function deleteAdminTask(taskId: string) {
  return deleteJson<TaskDeleteResult>(`/admin/tasks/${taskId}`);
}

/**
 * 处理评分管理任务效果。
 * @param taskId 任务标识
 * @param payload 附加负载数据
 */
export function rateAdminTaskEffect(taskId: string, payload: RateTaskEffectRequest) {
  return postJson<TaskDetail>(`/admin/tasks/${taskId}/effect-rating`, payload);
}

/**
 * 处理批量删除管理任务。
 * @param taskIds 任务标识列表值
 */
export function bulkDeleteAdminTasks(taskIds: string[]) {
  return postJson<AdminTaskBatchResult>("/admin/tasks/bulk-delete", { taskIds });
}

/**
 * 处理批量重试管理任务。
 * @param taskIds 任务标识列表值
 */
export function bulkRetryAdminTasks(taskIds: string[]) {
  return postJson<AdminTaskBatchResult>("/admin/tasks/bulk-retry", { taskIds });
}

export function fetchAdminUsers() {
  return getJson<AdminUser[]>("/admin/users");
}

export function disableAdminUser(id: number) {
  return postJson<AdminUser>(`/admin/users/${id}/disable`, {});
}

export function enableAdminUser(id: number) {
  return postJson<AdminUser>(`/admin/users/${id}/enable`, {});
}

export function fetchAdminInvites() {
  return getJson<AdminInvite[]>("/admin/invites");
}

export function createAdminInvite(payload: CreateAdminInviteRequest) {
  return postJson<AdminInvite>("/admin/invites", payload);
}

export function revokeAdminInvite(id: number) {
  return postJson<AdminInvite>(`/admin/invites/${id}/revoke`, {});
}
