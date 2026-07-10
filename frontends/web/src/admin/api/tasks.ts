import type {
  AdminPaginatedResponse,
  AdminTaskBatchResult,
  AdminTaskDiagnosis,
  AdminTaskListItem,
  AdminTaskQuery,
  AdminTraceEvent,
} from "@/types/admin";
import type { TaskDetail, TaskTraceEvent } from "@/types/tasks";

import { deleteJson, getJson, postJson } from "@/api/client";
import { withQuery } from "@/api/query";

export async function fetchAdminTasks(query?: AdminTaskQuery) {
  return getJson<AdminPaginatedResponse<AdminTaskListItem>>(
    withQuery("/admin/tasks", {
      q: query?.q,
      status: query?.status,
      sort: query?.sort,
      offset: query?.offset != null && query.offset > 0 ? query.offset : undefined,
      limit: query?.limit,
    }),
  );
}

export async function fetchAdminTask(taskId: string) {
  return getJson<TaskDetail>(`/admin/tasks/${taskId}`);
}

export async function fetchAdminTaskTrace(taskId: string, limit?: number) {
  return getJson<TaskTraceEvent[]>(
    withQuery(`/admin/tasks/${taskId}/trace`, {
      limit: limit && limit > 0 ? limit : undefined,
    }),
  );
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

export async function bulkDeleteAdminTasks(taskIds: string[]) {
  return postJson<AdminTaskBatchResult>("/admin/tasks/bulk-delete", { taskIds });
}

export async function fetchAdminTraces(params?: {
  limit?: number;
  taskId?: string;
  level?: string;
  stage?: string;
  q?: string;
}) {
  return getJson<AdminTraceEvent[]>(
    withQuery("/admin/traces", {
      limit: params?.limit,
      taskId: params?.taskId,
      level: params?.level,
      stage: params?.stage,
      q: params?.q,
    }),
  );
}
