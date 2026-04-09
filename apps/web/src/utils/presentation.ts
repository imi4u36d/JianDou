import type { TaskDetail, TaskListItem, TaskStatus } from "@/types";

type StatusMeta = {
  label: string;
  tone: "neutral" | "info" | "warning" | "success" | "danger";
};

export const TASK_STATUS_META: Record<TaskStatus, StatusMeta> = {
  PENDING: { label: "排队中", tone: "neutral" },
  PAUSED: { label: "已暂停", tone: "warning" },
  ANALYZING: { label: "解析中", tone: "info" },
  PLANNING: { label: "规划中", tone: "warning" },
  RENDERING: { label: "生成中", tone: "warning" },
  COMPLETED: { label: "已完成", tone: "success" },
  FAILED: { label: "失败", tone: "danger" },
};

export function getTaskStatusMeta(status: TaskStatus) {
  return TASK_STATUS_META[status] ?? TASK_STATUS_META.PENDING;
}

export function clampProgress(value: number | null | undefined) {
  if (!Number.isFinite(value)) {
    return 0;
  }
  return Math.max(0, Math.min(100, Math.round(Number(value))));
}

export function formatDateTime(value: string | null | undefined) {
  if (!value) {
    return "暂无";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

export function formatLongDateTime(value: string | null | undefined) {
  if (!value) {
    return "暂无";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return new Intl.DateTimeFormat("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).format(date);
}

export function formatDurationLabel(minSeconds?: number | null, maxSeconds?: number | null) {
  if (!minSeconds && !maxSeconds) {
    return "未设置";
  }
  if (minSeconds && maxSeconds && minSeconds !== maxSeconds) {
    return `${minSeconds}-${maxSeconds}s`;
  }
  return `${maxSeconds ?? minSeconds ?? 0}s`;
}

export function formatAspectRatioLabel(value?: string | null) {
  if (!value) {
    return "未指定比例";
  }
  return value === "9:16" ? "竖屏 9:16" : value === "16:9" ? "横屏 16:9" : value;
}

export function formatTaskOutputs(task: TaskListItem | TaskDetail | null | undefined) {
  if (!task) {
    return "暂无结果";
  }
  const detailOutputCount = "outputs" in task && Array.isArray(task.outputs) ? task.outputs.length : 0;
  const completed = Math.max(0, task.completedOutputCount ?? detailOutputCount);
  if (completed <= 0) {
    return "暂无结果";
  }
  return `${completed} 条结果`;
}

export function summarizeTask(task: TaskListItem) {
  return [formatAspectRatioLabel(task.aspectRatio), formatDurationLabel(task.minDurationSeconds, task.maxDurationSeconds)]
    .filter(Boolean)
    .join(" · ");
}
