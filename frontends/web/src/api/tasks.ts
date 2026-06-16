/**
 * 任务相关 API 请求封装。
 */
import { deleteJson, getJson, postForm, postJson } from "./client";
import type {
  CreateGenerationTaskRequest,
  GenerateCreativePromptRequest,
  GenerateCreativePromptResponse,
  RateTaskEffectRequest,
  TaskDeleteResult,
  TaskDetail,
  TaskFilters,
  TaskListItem,
  SeedanceTaskQueryResult,
  TaskTraceEvent,
  UploadResponse,
} from "@/types";

/**
 * 上传文本。
 * @param file 待上传的文件
 */
export function uploadText(file: File) {
  const form = new FormData();
  form.append("file", file);
  return postForm<UploadResponse>("/uploads/texts", form);
}

/**
 * 创建生成任务。
 * @param payload 附加负载数据
 */
export function createGenerationTask(payload: CreateGenerationTaskRequest) {
  return postJson<TaskDetail>("/tasks/generation", payload);
}

/**
 * 生成创意提示词。
 * @param payload 附加负载数据
 */
export function generateCreativePrompt(payload: GenerateCreativePromptRequest) {
  return postJson<GenerateCreativePromptResponse>("/tasks/generate-prompt", payload);
}

/**
 * 获取任务。
 * @param filters 筛选条件值
 */
export function fetchTasks(filters?: TaskFilters) {
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
  return getJson<TaskListItem[]>(query ? `/tasks?${query}` : "/tasks");
}

/**
 * 获取任务。
 * @param taskId 任务标识
 */
export function fetchTask(taskId: string) {
  return getJson<TaskDetail>(`/tasks/${taskId}`);
}

/**
 * 获取任务追踪。
 * @param taskId 任务标识
 * @param limit 返回的最大条目数
 */
export function fetchTaskTrace(taskId: string, limit = 500) {
  return getJson<TaskTraceEvent[]>(`/tasks/${taskId}/trace?limit=${limit}`);
}

/**
 * 获取Seedance任务结果。
 * @param remoteTaskId 远程任务标识值
 */
export function fetchSeedanceTaskResult(remoteTaskId: string) {
  return getJson<SeedanceTaskQueryResult>(`/tasks/seedance/${encodeURIComponent(remoteTaskId)}`);
}

/**
 * 重试任务。
 * @param taskId 任务标识
 */
export function retryTask(taskId: string) {
  return postJson<TaskDetail>(`/tasks/${taskId}/retry`, {});
}

/**
 * 暂停任务。
 * @param taskId 任务标识
 */
export function pauseTask(taskId: string) {
  return postJson<TaskDetail>(`/tasks/${taskId}/pause`, {});
}

/**
 * 处理继续任务。
 * @param taskId 任务标识
 */
export function continueTask(taskId: string) {
  return postJson<TaskDetail>(`/tasks/${taskId}/continue`, {});
}

/**
 * 终止任务。
 * @param taskId 任务标识
 */
export function terminateTask(taskId: string) {
  return postJson<TaskDetail>(`/tasks/${taskId}/terminate`, {});
}

/**
 * 处理评分任务效果。
 * @param taskId 任务标识
 * @param payload 附加负载数据
 */
export function rateTaskEffect(taskId: string, payload: RateTaskEffectRequest) {
  return postJson<TaskDetail>(`/tasks/${taskId}/effect-rating`, payload);
}

/**
 * 删除任务。
 * @param taskId 任务标识
 */
export function deleteTask(taskId: string) {
  return deleteJson<TaskDeleteResult>(`/tasks/${taskId}`);
}
