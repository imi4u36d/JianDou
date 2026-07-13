import { formatTaskStatus } from "@/utils/task";
import type { TaskListItem } from "@/types";

export function activeTaskTimestamp(value?: string | null) {
  const timestamp = value ? new Date(value).getTime() : Number.NaN;
  return Number.isFinite(timestamp) ? timestamp : 0;
}

export function activeTaskProgress(task: TaskListItem) {
  return Math.max(0, Math.min(100, Math.round(task.progress ?? 0)));
}

export function formatActiveTaskTime(value?: string | null) {
  if (!value) return "暂无时间";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

export function activeTaskStageLabel(task: TaskListItem) {
  if (task.currentStage?.trim()) return task.currentStage.trim();
  if (task.status === "PENDING") {
    return typeof task.queuePosition === "number" && task.queuePosition > 0
      ? `队列第 ${task.queuePosition} 位`
      : "等待开始";
  }
  return formatTaskStatus(task.status);
}
