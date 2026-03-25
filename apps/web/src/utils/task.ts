import type { TaskStatus } from "@/types";

export const TERMINAL_TASK_STATUSES: TaskStatus[] = ["COMPLETED", "FAILED"];

export const TASK_STATUS_LABELS: Record<TaskStatus, string> = {
  PENDING: "排队中",
  ANALYZING: "分析中",
  PLANNING: "规划中",
  RENDERING: "渲染中",
  COMPLETED: "已完成",
  FAILED: "失败"
};

export function isTerminalTaskStatus(status: TaskStatus) {
  return TERMINAL_TASK_STATUSES.includes(status);
}

export function formatTaskStatus(status: TaskStatus) {
  return TASK_STATUS_LABELS[status] ?? status;
}
