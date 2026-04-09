import type { TaskStatus } from "@/types";

export const TERMINAL_TASK_STATUSES: TaskStatus[] = ["COMPLETED", "FAILED"];

export const TASK_STATUS_LABELS: Record<TaskStatus, string> = {
  PENDING: "排队等待",
  PAUSED: "已暂停",
  ANALYZING: "分析素材",
  PLANNING: "生成方案",
  RENDERING: "渲染导出",
  COMPLETED: "已完成",
  FAILED: "失败"
};

export const TASK_LIFECYCLE_GROUP_LABELS = {
  queued: "排队中",
  paused: "已暂停",
  running: "处理中",
  completed: "已完成",
  failed: "失败"
} as const;

export function isTerminalTaskStatus(status: TaskStatus) {
  return TERMINAL_TASK_STATUSES.includes(status);
}

export function formatTaskStatus(status: TaskStatus) {
  return TASK_STATUS_LABELS[status] ?? status;
}

export function getTaskLifecycleGroup(status: TaskStatus) {
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

export function formatTaskRange(minDuration: number, maxDuration: number) {
  return `${minDuration}-${maxDuration}s`;
}

export function formatTaskProgress(progress: number) {
  return `${Math.max(0, Math.min(100, progress))}%`;
}
