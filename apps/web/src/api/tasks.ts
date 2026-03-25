import { getJson, postForm, postJson } from "./client";
import type { CreateTaskRequest, TaskDetail, TaskListItem, UploadResponse } from "@/types";

export function uploadVideo(file: File) {
  const form = new FormData();
  form.append("file", file);
  return postForm<UploadResponse>("/uploads/videos", form);
}

export function createTask(payload: CreateTaskRequest) {
  return postJson<TaskDetail>("/tasks", payload);
}

export function fetchTasks() {
  return getJson<TaskListItem[]>("/tasks");
}

export function fetchTask(taskId: string) {
  return getJson<TaskDetail>(`/tasks/${taskId}`);
}

export function retryTask(taskId: string) {
  return postJson<TaskDetail>(`/tasks/${taskId}/retry`, {});
}

