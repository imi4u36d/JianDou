/**
 * 任务相关 API 请求封装。
 */
import type {
  CreateGenerationTaskRequest,
  GenerateCreativePromptRequest,
  GenerateCreativePromptResponse,
} from "@/types/generation";
import type {
  RateTaskEffectRequest,
  SeedanceTaskQueryResult,
  TaskDeleteResult,
  TaskDetail,
  TaskFilters,
  TaskListItem,
  TaskPaginatedResponse,
  TaskTraceEvent,
} from "@/types/tasks";
import type { UploadResponse } from "@/types/uploads";

import { deleteJson, getJson, postForm, postJson } from "./client";
import { withQuery } from "./query";

function taskFilterQuery(filters?: TaskFilters) {
  return {
    q: filters?.q,
    status: filters?.status && filters.status !== "all" ? filters.status : undefined,
    sort: filters?.sort,
    taskType: filters?.taskType,
    excludeTaskType: filters?.excludeTaskType,
  };
}

/** 上传文本。 */
export function uploadText(file: File) {
  const form = new FormData();
  form.append("file", file);
  return postForm<UploadResponse>("/uploads/texts", form);
}

/** 创建生成任务。 */
export function createGenerationTask(payload: CreateGenerationTaskRequest) {
  return postJson<TaskDetail>("/tasks/generation", payload);
}

/** 生成创意提示词。 */
export function generateCreativePrompt(payload: GenerateCreativePromptRequest) {
  return postJson<GenerateCreativePromptResponse>("/tasks/generate-prompt", payload);
}

/** 获取全部任务。 */
export function fetchAllTasks(filters?: TaskFilters) {
  return getJson<TaskListItem[]>(withQuery("/tasks", taskFilterQuery(filters)));
}

/** 分页获取任务。 */
export function fetchTaskPage(filters: TaskFilters & { offset: number; limit: number }) {
  return getJson<TaskPaginatedResponse>(
    withQuery("/tasks", {
      ...taskFilterQuery(filters),
      offset: filters.offset,
      limit: filters.limit,
    }),
  );
}

/** 获取任务详情。 */
export function fetchTask(taskId: string) {
  return getJson<TaskDetail>(`/tasks/${encodeURIComponent(taskId)}`);
}

/** 获取任务追踪。 */
export function fetchTaskTrace(taskId: string, limit = 500) {
  return getJson<TaskTraceEvent[]>(
    withQuery(`/tasks/${encodeURIComponent(taskId)}/trace`, {
      limit,
    }),
  );
}

/** 获取 Seedance 任务结果。 */
export function fetchSeedanceTaskResult(remoteTaskId: string) {
  return getJson<SeedanceTaskQueryResult>(`/tasks/seedance/${encodeURIComponent(remoteTaskId)}`);
}

/** 重试任务。 */
export function retryTask(taskId: string) {
  return postJson<TaskDetail>(`/tasks/${encodeURIComponent(taskId)}/retry`, {});
}

/** 暂停任务。 */
export function pauseTask(taskId: string) {
  return postJson<TaskDetail>(`/tasks/${encodeURIComponent(taskId)}/pause`, {});
}

/** 继续任务。 */
export function continueTask(taskId: string) {
  return postJson<TaskDetail>(`/tasks/${encodeURIComponent(taskId)}/continue`, {});
}

/** 终止任务。 */
export function terminateTask(taskId: string) {
  return postJson<TaskDetail>(`/tasks/${encodeURIComponent(taskId)}/terminate`, {});
}

/** 评分任务效果。 */
export function rateTaskEffect(taskId: string, payload: RateTaskEffectRequest) {
  return postJson<TaskDetail>(`/tasks/${encodeURIComponent(taskId)}/effect-rating`, payload);
}

/** 删除任务。 */
export function deleteTask(taskId: string) {
  return deleteJson<TaskDeleteResult>(`/tasks/${encodeURIComponent(taskId)}`);
}
