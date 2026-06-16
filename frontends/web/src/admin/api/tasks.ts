import { deleteJson, getJson, postJson } from "@/api/client";
import type {
  AdminTaskBatchResult,
  AdminTaskDiagnosis,
  AdminTaskListItem,
  AdminTaskQuery,
  AdminTraceEvent,
  TaskDetail,
  TaskTraceEvent,
} from "@/types";

export async function fetchAdminTasks(query?: AdminTaskQuery) {
  const params = new URLSearchParams();
  if (query?.q?.trim()) {
    params.set("q", query.q.trim());
  }
  if (query?.status) {
    params.set("status", query.status);
  }
  if (query?.sort) {
    params.set("sort", query.sort);
  }
  const search = params.toString();
  return getJson<AdminTaskListItem[]>(search ? `/admin/tasks?${search}` : "/admin/tasks");
}

export async function fetchAdminTask(taskId: string) {
  return getJson<TaskDetail>(`/admin/tasks/${taskId}`);
}

export async function fetchAdminTaskTrace(taskId: string, limit?: number) {
  const params = limit ? `?limit=${limit}` : "";
  return getJson<TaskTraceEvent[]>(`/admin/tasks/${taskId}/trace${params}`);
}

export async function fetchAdminTaskDiagnosis(taskId: string) {
  return getJson<AdminTaskDiagnosis>(`/admin/tasks/${taskId}/diagnosis`);
}

export async function retryAdminTask(taskId: string) {
  return postJson<TaskDetail>(`/admin/tasks/${taskId}/retry`, {});
}

export async function deleteAdminTask(taskId: string) {
  return deleteJson<void>(`/admin/tasks/${taskId}`);
}

export async function terminateAdminTask(taskId: string) {
  return postJson<AdminTaskListItem>(`/admin/tasks/${taskId}/terminate`, {});
}

export async function bulkTerminateAdminTasks(taskIds: string[]) {
  return postJson<AdminTaskBatchResult>("/admin/tasks/bulk-terminate", { taskIds });
}

export async function fetchAdminTraces(params?: {
  limit?: number;
  taskId?: string;
  level?: string;
  stage?: string;
  q?: string;
}) {
  const searchParams = new URLSearchParams();
  if (params?.limit) searchParams.set("limit", String(params.limit));
  if (params?.taskId) searchParams.set("taskId", params.taskId);
  if (params?.level) searchParams.set("level", params.level);
  if (params?.stage) searchParams.set("stage", params.stage);
  if (params?.q) searchParams.set("q", params.q);
  const search = searchParams.toString();
  return getJson<AdminTraceEvent[]>(search ? `/admin/traces?${search}` : "/admin/traces");
}
