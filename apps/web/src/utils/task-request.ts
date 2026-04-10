import type { TaskDetail, TaskRequestSnapshot } from "@/types";

function cleanString(value: string | null | undefined) {
  return String(value ?? "").trim();
}

export function getTaskRequestSnapshot(task: Pick<TaskDetail, "requestSnapshot"> | null | undefined): TaskRequestSnapshot {
  return task?.requestSnapshot ?? {};
}

export function formatTaskModelValue(value: string | null | undefined) {
  const normalized = cleanString(value);
  return normalized || "未选择";
}

export function formatTaskDurationMode(snapshot: TaskRequestSnapshot | null | undefined) {
  return snapshot?.videoDurationSeconds === "auto" ? "自动" : "固定";
}

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

export function formatTaskResolvedDuration(task: Pick<TaskDetail, "minDurationSeconds" | "maxDurationSeconds"> | null | undefined) {
  const minDuration = task?.minDurationSeconds;
  const maxDuration = task?.maxDurationSeconds;
  if (typeof minDuration === "number" && typeof maxDuration === "number") {
    return minDuration === maxDuration ? `${maxDuration}s` : `${minDuration}-${maxDuration}s`;
  }
  return "未设置";
}

export function formatTaskTranscriptSummary(snapshot: TaskRequestSnapshot | null | undefined) {
  const transcriptText = cleanString(snapshot?.transcriptText);
  return transcriptText ? `${transcriptText.length} 字` : "未提供";
}

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

export function formatTaskStopBeforeVideoGeneration(snapshot: TaskRequestSnapshot | null | undefined) {
  return snapshot?.stopBeforeVideoGeneration ? "是" : "否";
}
