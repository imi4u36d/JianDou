import { deleteJson, getJson, postForm, postJson } from "./client";
import type {
  CreateGenerationTaskRequest,
  GenerateCreativePromptRequest,
  GenerateCreativePromptResponse,
  TaskDeleteResult,
  TaskDetail,
  TaskFilters,
  TaskListItem,
  SeeddanceTaskQueryResult,
  TaskTraceEvent,
  UploadResponse,
} from "@/types";

export function uploadText(file: File) {
  const form = new FormData();
  form.append("file", file);
  return postForm<UploadResponse>("/uploads/texts", form);
}

export function createGenerationTask(payload: CreateGenerationTaskRequest) {
  return postJson<TaskDetail>("/tasks/generation", payload);
}

export function generateCreativePrompt(payload: GenerateCreativePromptRequest) {
  return postJson<GenerateCreativePromptResponse>("/tasks/generate-prompt", payload);
}

export function fetchTasks(filters?: TaskFilters) {
  const params = new URLSearchParams();
  if (filters?.q?.trim()) {
    params.set("q", filters.q.trim());
  }
  if (filters?.status && filters.status !== "all") {
    params.set("status", filters.status);
  }
  const query = params.toString();
  return getJson<TaskListItem[]>(query ? `/tasks?${query}` : "/tasks");
}

export function fetchTask(taskId: string) {
  return getJson<TaskDetail>(`/tasks/${taskId}`);
}

export function fetchTaskTrace(taskId: string, limit = 500) {
  return getJson<TaskTraceEvent[]>(`/tasks/${taskId}/trace?limit=${limit}`);
}

export function fetchSeeddanceTaskResult(remoteTaskId: string) {
  return getJson<SeeddanceTaskQueryResult>(`/tasks/seeddance/${encodeURIComponent(remoteTaskId)}`);
}

export function retryTask(taskId: string) {
  return postJson<TaskDetail>(`/tasks/${taskId}/retry`, {});
}

export function pauseTask(taskId: string) {
  return postJson<TaskDetail>(`/tasks/${taskId}/pause`, {});
}

export function continueTask(taskId: string) {
  return postJson<TaskDetail>(`/tasks/${taskId}/continue`, {});
}

export function terminateTask(taskId: string) {
  return postJson<TaskDetail>(`/tasks/${taskId}/terminate`, {});
}

export function deleteTask(taskId: string) {
  return deleteJson<TaskDeleteResult>(`/tasks/${taskId}`);
}
