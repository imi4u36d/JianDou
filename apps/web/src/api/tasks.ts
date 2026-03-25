import { getJson, postForm, postJson } from "./client";
import type {
  CreateTaskRequest,
  TaskCloneDraft,
  TaskDetail,
  TaskFilters,
  TaskListItem,
  TaskPreset,
  TaskTraceEvent,
  UploadResponse
} from "@/types";

export function uploadVideo(file: File) {
  const form = new FormData();
  form.append("file", file);
  return postForm<UploadResponse>("/uploads/videos", form);
}

export function createTask(payload: CreateTaskRequest) {
  return postJson<TaskDetail>("/tasks", payload);
}

export function fetchTasks(filters?: TaskFilters) {
  const params = new URLSearchParams();
  if (filters?.q?.trim()) {
    params.set("q", filters.q.trim());
  }
  if (filters?.status && filters.status !== "all") {
    params.set("status", filters.status);
  }
  if (filters?.platform && filters.platform !== "all") {
    params.set("platform", filters.platform);
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

export function retryTask(taskId: string) {
  return postJson<TaskDetail>(`/tasks/${taskId}/retry`, {});
}

export function cloneTask(taskId: string) {
  return postJson<TaskCloneDraft>(`/tasks/${taskId}/clone`, {});
}

export function fetchPresets() {
  return getJson<TaskPreset[]>("/presets");
}
