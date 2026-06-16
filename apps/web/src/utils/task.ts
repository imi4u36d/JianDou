/**
 * 任务相关工具方法。
 */
export {
  TASK_LIFECYCLE_GROUP_LABELS,
  TASK_STATUS_LABELS,
  TERMINAL_TASK_STATUSES,
} from "@jiandou/domain";
import {
  formatTaskProgress as sharedFormatTaskProgress,
  formatTaskRange as sharedFormatTaskRange,
  formatTaskStatus as sharedFormatTaskStatus,
  getTaskLifecycleGroup as sharedGetTaskLifecycleGroup,
  isTerminalTaskStatus as sharedIsTerminalTaskStatus,
} from "@jiandou/domain";
import type { TaskStatus } from "@/types";

/**
 * 检查是否终态任务状态。
 * @param status 状态值
 */
export function isTerminalTaskStatus(status: TaskStatus) {
  return sharedIsTerminalTaskStatus(status);
}

/**
 * 格式化任务状态。
 * @param status 状态值
 */
export function formatTaskStatus(status: TaskStatus) {
  return sharedFormatTaskStatus(status);
}

/**
 * 返回任务生命周期分组。
 * @param status 状态值
 */
export function getTaskLifecycleGroup(status: TaskStatus) {
  return sharedGetTaskLifecycleGroup(status);
}

/**
 * 格式化任务范围。
 * @param minDuration 最小时长值
 * @param maxDuration 最大时长值
 */
export function formatTaskRange(minDuration: number, maxDuration: number) {
  return sharedFormatTaskRange(minDuration, maxDuration);
}

/**
 * 格式化任务进度。
 * @param progress 进度值
 */
export function formatTaskProgress(progress: number) {
  return sharedFormatTaskProgress(progress);
}
