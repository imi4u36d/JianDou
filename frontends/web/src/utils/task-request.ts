/**
 * 任务请求相关工具方法。
 */
import type { TaskDetail, TaskRequestSnapshot } from "@/types";

/**
 * 处理cleanString。
 * @param value 待处理的值
 */
function cleanString(value: string | null | undefined) {
  return String(value ?? "").trim();
}

/**
 * 返回任务请求快照。
 * @param task 要处理的任务对象
 * @return 处理结果
 */
export function getTaskRequestSnapshot(task: Pick<TaskDetail, "requestSnapshot"> | null | undefined): TaskRequestSnapshot {
  return task?.requestSnapshot ?? {};
}

/**
 * 格式化任务模型值。
 * @param value 待处理的值
 */
export function formatTaskModelValue(value: string | null | undefined) {
  const normalized = cleanString(value);
  return normalized || "未选择";
}

/**
 * 格式化任务时长模式。
 * @param snapshot 快照值
 */
export function formatTaskDurationMode(snapshot: TaskRequestSnapshot | null | undefined) {
  return snapshot?.videoDurationSeconds === "auto" ? "自动" : "固定";
}

/**
 * 格式化任务Requested时长。
 * @param snapshot 快照值
 */
export function formatTaskRequestedDuration(snapshot: TaskRequestSnapshot | null | undefined) {
  if (snapshot?.videoDurationSeconds === "auto") {
    return "自动";
  }
  if (typeof snapshot?.videoDurationSeconds === "number" && Number.isFinite(snapshot.videoDurationSeconds)) {
    return `${Math.trunc(snapshot.videoDurationSeconds)}s`;
  }
  const minDuration = snapshot?.minDurationSeconds;
  const maxDuration = snapshot?.maxDurationSeconds;
  if (typeof minDuration === "number" && typeof maxDuration === "number") {
    return minDuration === maxDuration ? `${maxDuration}s` : `${minDuration}-${maxDuration}s`;
  }
  return "未设置";
}

/**
 * 格式化任务输出数量。
 * @param snapshot 快照值
 */
export function formatTaskOutputCount(snapshot: TaskRequestSnapshot | null | undefined) {
  if (snapshot?.outputCount === "auto") {
    return "自动";
  }
  if (typeof snapshot?.outputCount === "number" && Number.isFinite(snapshot.outputCount)) {
    return `${Math.trunc(snapshot.outputCount)} 条`;
  }
  return "自动";
}

/**
 * 格式化任务Resolved时长。
 * @param task 要处理的任务对象
 */
export function formatTaskResolvedDuration(task: Pick<TaskDetail, "minDurationSeconds" | "maxDurationSeconds"> | null | undefined) {
  const minDuration = task?.minDurationSeconds;
  const maxDuration = task?.maxDurationSeconds;
  if (typeof minDuration === "number" && typeof maxDuration === "number") {
    return minDuration === maxDuration ? `${maxDuration}s` : `${minDuration}-${maxDuration}s`;
  }
  return "未设置";
}

/**
 * 格式化任务正文摘要。
 * @param snapshot 快照值
 */
export function formatTaskTranscriptSummary(snapshot: TaskRequestSnapshot | null | undefined) {
  const transcriptText = cleanString(snapshot?.transcriptText);
  return transcriptText ? `${transcriptText.length} 字` : "未提供";
}

/**
 * 处理preview任务正文。
 * @param snapshot 快照值
 * @param limit 返回的最大条目数
 */
export function previewTaskTranscript(snapshot: TaskRequestSnapshot | null | undefined, limit = 220) {
  const transcriptText = cleanString(snapshot?.transcriptText);
  if (!transcriptText) {
    return "";
  }
  const normalized = transcriptText
    .split(/\r?\n/)
    .map((item) => item.trim())
    .filter(Boolean)
    .join(" ");
  if (normalized.length <= limit) {
    return normalized;
  }
  return `${normalized.slice(0, Math.max(0, limit - 3))}...`;
}

/**
 * 格式化任务StopBefore视频生成。
 * @param snapshot 快照值
 */
export function formatTaskStopBeforeVideoGeneration(snapshot: TaskRequestSnapshot | null | undefined) {
  return snapshot?.stopBeforeVideoGeneration ? "是" : "否";
}

/**
 * 格式化任务种子。
 * @param snapshot 快照值
 */
export function formatTaskSeed(snapshot: TaskRequestSnapshot | null | undefined) {
  const seed = snapshot?.seed;
  return typeof seed === "number" && Number.isFinite(seed) ? String(Math.trunc(seed)) : "未设置";
}

/**
 * 格式化任务效果评分。
 * @param value 待处理的值
 */
export function formatTaskEffectRating(value: number | null | undefined) {
  return typeof value === "number" && Number.isFinite(value) && value > 0 ? `${Math.trunc(value)}/5` : "未评分";
}
