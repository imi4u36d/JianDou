export type TaskStatus =
  | "PENDING"
  | "PAUSED"
  | "ANALYZING"
  | "PLANNING"
  | "RENDERING"
  | "COMPLETED"
  | "FAILED";

export type TaskLifecycleGroup = "queued" | "paused" | "running" | "completed" | "failed";

export interface TaskProgressLike {
  status?: TaskStatus | string | null;
  progress?: number | null;
}

export const TERMINAL_TASK_STATUSES: readonly TaskStatus[] = ["COMPLETED", "FAILED"];

export const TASK_STATUS_LABELS: Record<TaskStatus, string> = {
  PENDING: "排队等待",
  PAUSED: "已暂停",
  ANALYZING: "分析素材",
  PLANNING: "生成方案",
  RENDERING: "渲染导出",
  COMPLETED: "已完成",
  FAILED: "失败"
};

export const TASK_LIFECYCLE_GROUP_LABELS: Record<TaskLifecycleGroup, string> = {
  queued: "排队中",
  paused: "已暂停",
  running: "处理中",
  completed: "已完成",
  failed: "失败"
};

export function isTaskStatus(value: string | null | undefined): value is TaskStatus {
  if (!value) {
    return false;
  }
  return Object.prototype.hasOwnProperty.call(TASK_STATUS_LABELS, value);
}

export function isTerminalTaskStatus(status: TaskStatus | string | null | undefined) {
  return isTaskStatus(status) && TERMINAL_TASK_STATUSES.includes(status);
}

export function formatTaskStatus(status: TaskStatus | string | null | undefined) {
  if (!status) {
    return "未知状态";
  }
  return isTaskStatus(status) ? TASK_STATUS_LABELS[status] : status;
}

export function getTaskLifecycleGroup(status: TaskStatus | string | null | undefined): TaskLifecycleGroup {
  switch (status) {
    case "COMPLETED":
      return "completed";
    case "FAILED":
      return "failed";
    case "PAUSED":
      return "paused";
    case "ANALYZING":
    case "PLANNING":
    case "RENDERING":
      return "running";
    default:
      return "queued";
  }
}

export function clampPercent(value: number | null | undefined, fallback = 0) {
  const nextValue = typeof value === "number" && Number.isFinite(value) ? value : fallback;
  return Math.max(0, Math.min(100, Math.round(nextValue)));
}

export function formatPercent(value: number | null | undefined, fallback = 0) {
  return `${clampPercent(value, fallback)}%`;
}

export function formatTaskRange(minDuration: number | null | undefined, maxDuration: number | null | undefined) {
  if (typeof minDuration !== "number" || typeof maxDuration !== "number") {
    return "未设置";
  }
  return `${minDuration}-${maxDuration}s`;
}

export function formatTaskProgress(progress: number | null | undefined) {
  return formatPercent(progress);
}

export function resolveTaskProgress(task: TaskProgressLike | null | undefined) {
  if (!task) {
    return 0;
  }
  if (task.status === "COMPLETED") {
    return 100;
  }
  return clampPercent(task.progress);
}
