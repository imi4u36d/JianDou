import { deleteJson, getJson, postJson } from "./client";
import type {
  AdminOverview,
  AdminTaskBatchResult,
  AdminTaskFilters,
  AdminTraceEvent,
  TaskDeleteResult,
  TaskDetail,
  TaskListItem,
  TaskTraceEvent,
} from "@/types";

export async function fetchAdminOverview() {
  return getJson<AdminOverview>("/admin/overview");
}

export function fetchAdminTasks(filters?: AdminTaskFilters) {
  const params = new URLSearchParams();
  if (filters?.q?.trim()) {
    params.set("q", filters.q.trim());
  }
  if (filters?.status && filters.status !== "all") {
    params.set("status", filters.status);
  }
  const query = params.toString();
  return getJson<TaskListItem[]>(query ? `/admin/tasks?${query}` : "/admin/tasks");
}

export function fetchAdminTask(taskId: string) {
  return getJson<TaskDetail>(`/admin/tasks/${taskId}`);
}

export function fetchAdminTaskTrace(taskId: string, limit = 500) {
  return getJson<TaskTraceEvent[]>(`/admin/tasks/${taskId}/trace?limit=${limit}`);
}

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

export function retryAdminTask(taskId: string) {
  return postJson<TaskDetail>(`/admin/tasks/${taskId}/retry`, {});
}

export function terminateAdminTask(taskId: string) {
  return postJson<TaskDetail>(`/admin/tasks/${taskId}/terminate`, {});
}

export function deleteAdminTask(taskId: string) {
  return deleteJson<TaskDeleteResult>(`/admin/tasks/${taskId}`);
}

export function bulkDeleteAdminTasks(taskIds: string[]) {
  return postJson<AdminTaskBatchResult>("/admin/tasks/bulk-delete", { taskIds });
}

export function bulkRetryAdminTasks(taskIds: string[]) {
  return postJson<AdminTaskBatchResult>("/admin/tasks/bulk-retry", { taskIds });
}
