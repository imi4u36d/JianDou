import type { IconName } from "@/components/icons";
import type { TaskAttempt, TaskDetail, TaskListItem, TaskStageRun, TaskStatus } from "@/types";
import { resolveTaskThumbnailUrl } from "@/utils/task-preview";

export type TaskStageState = "pending" | "active" | "paused" | "done" | "failed";
type TaskStageIconState = TaskStageState;

export interface TaskStageDisplayItem {
  key: string;
  label: string;
  state: TaskStageState;
  iconState: TaskStageIconState;
  stateLabel: string;
  durationLabel: string;
}

type TaskStageTimingTask = Pick<TaskListItem, "createdAt" | "updatedAt" | "startedAt" | "finishedAt"> & {
  attempts?: TaskAttempt[];
  stageRuns?: TaskStageRun[];
};

const ACTIVE_TASK_STATUSES = new Set<TaskStatus>(["PENDING", "ANALYZING", "PLANNING", "RENDERING", "PAUSED"]);
const taskStageStateLabels: Record<TaskStageState, string> = {
  pending: "等待",
  active: "进行中",
  paused: "已暂停",
  done: "已完成",
  failed: "失败",
};

function withTaskStageLabels(
  items: Array<Omit<TaskStageDisplayItem, "stateLabel" | "iconState" | "durationLabel"> & Partial<Pick<TaskStageDisplayItem, "iconState" | "durationLabel">>>,
): TaskStageDisplayItem[] {
  return items.map((item) => ({
    ...item,
    iconState: item.iconState ?? item.state,
    stateLabel: taskStageStateLabels[item.state],
    durationLabel: item.durationLabel ?? "",
  }));
}

export function buildVideoTaskStages(status: TaskStatus): TaskStageDisplayItem[] {
  const stageOrder: TaskStatus[] = ["ANALYZING", "PLANNING", "RENDERING", "COMPLETED"];
  const pausedAtRender = status === "PAUSED";
  const currentIndex = pausedAtRender ? 2 : stageOrder.indexOf(status);
  const items = [
    { key: "ANALYZING", label: "素材分析", state: currentIndex > 0 ? "done" : currentIndex === 0 ? "active" : "pending" },
    { key: "PLANNING", label: "任务编排", state: currentIndex > 1 ? "done" : currentIndex === 1 ? "active" : "pending" },
    { key: "RENDERING", label: "视频生成", state: pausedAtRender ? "paused" : currentIndex > 2 ? "done" : currentIndex === 2 ? "active" : "pending" },
    { key: "COMPLETED", label: "任务完成", state: status === "COMPLETED" ? "done" : status === "FAILED" ? "failed" : "pending" },
  ] as Array<Omit<TaskStageDisplayItem, "stateLabel" | "iconState" | "durationLabel">>;
  return withTaskStageLabels(items);
}

function timeValue(raw?: string | null): number | null {
  if (!raw) return null;
  const value = new Date(raw).getTime();
  return Number.isNaN(value) ? null : value;
}

function elapsedMs(start?: string | null, end?: string | null): number | null {
  const startValue = timeValue(start);
  const endValue = timeValue(end);
  if (startValue == null || endValue == null || endValue < startValue) return null;
  return endValue - startValue;
}

function elapsedUntil(start?: string | null, endValue: number | null = Date.now()): number | null {
  const startValue = timeValue(start);
  if (startValue == null || endValue == null || endValue < startValue) return null;
  return endValue - startValue;
}

function formatStageDuration(ms: number | null): string {
  if (ms == null) return "";
  const totalSeconds = Math.max(0, Math.floor(ms / 1000));
  const seconds = totalSeconds % 60;
  const totalMinutes = Math.floor(totalSeconds / 60);
  const minutes = totalMinutes % 60;
  const hours = Math.floor(totalMinutes / 60);
  if (hours > 0) return `${hours}h ${minutes > 0 ? `${minutes}分` : ""}${seconds}秒`;
  if (minutes > 0) return `${minutes}分${String(seconds).padStart(2, "0")}秒`;
  return `00:${String(seconds).padStart(2, "0")}秒`;
}

function stageRunDurationMs(run?: TaskStageRun | null): number | null {
  if (!run) return null;
  if (typeof run.durationMs === "number" && Number.isFinite(run.durationMs) && run.durationMs > 0) return run.durationMs;
  return elapsedMs(run.startedAt, run.finishedAt);
}

function latestAttempt(task: TaskStageTimingTask | null | undefined): TaskAttempt | null {
  const attempts = task?.attempts ?? [];
  if (!attempts.length) return null;
  return [...attempts].sort((a, b) => {
    const attemptDifference = Number(a.attemptNo ?? 0) - Number(b.attemptNo ?? 0);
    if (attemptDifference) return attemptDifference;
    return (timeValue(a.queueEnteredAt) ?? timeValue(a.startedAt) ?? 0) - (timeValue(b.queueEnteredAt) ?? timeValue(b.startedAt) ?? 0);
  }).at(-1) ?? null;
}

function latestStageRun(
  task: TaskStageTimingTask | null | undefined,
  matcher: (stageName: string) => boolean,
): TaskStageRun | null {
  const attemptId = String(latestAttempt(task)?.attemptId ?? "").trim();
  const matched = (task?.stageRuns ?? []).filter((run) => {
    const runAttemptId = String(run.attemptId ?? "").trim();
    return (!attemptId || !runAttemptId || runAttemptId === attemptId) && matcher(String(run.stageName ?? "").trim().toLowerCase());
  });
  return matched.sort((a, b) => {
    const sequenceDifference = Number(a.stageSeq ?? 0) - Number(b.stageSeq ?? 0);
    return sequenceDifference || (timeValue(a.startedAt) ?? 0) - (timeValue(b.startedAt) ?? 0);
  }).at(-1) ?? null;
}

function imageSubmitStageDuration(task: TaskStageTimingTask | null | undefined): number | null {
  const attempt = latestAttempt(task);
  const attemptStart = attempt?.startedAt ?? attempt?.claimedAt ?? attempt?.queueLeftAt ?? null;
  const attemptQueuedAt = attempt?.queueEnteredAt ?? null;
  if (attemptStart) {
    return elapsedMs(attemptQueuedAt, attemptStart) ?? elapsedMs(task?.updatedAt, attemptStart) ?? elapsedMs(task?.createdAt, attemptStart);
  }
  if (attemptQueuedAt) return elapsedUntil(attemptQueuedAt, Date.now());
  return elapsedMs(task?.createdAt, task?.startedAt ?? task?.updatedAt);
}

function imageRenderStageDuration(task: TaskStageTimingTask | null | undefined, status: TaskStatus): number | null {
  const renderRun = latestStageRun(task, (stageName) =>
    stageName.includes("render") || stageName.includes("planning") || stageName.includes("image") || stageName.includes("character")
  );
  const fallbackEnd = task?.finishedAt ? timeValue(task.finishedAt) : status === "RENDERING" ? Date.now() : timeValue(task?.updatedAt);
  return stageRunDurationMs(renderRun) ?? elapsedUntil(task?.startedAt, fallbackEnd);
}

export function buildImageTaskStages(
  task: TaskStageTimingTask | null,
  status: TaskStatus,
  taskType: string,
): TaskStageDisplayItem[] {
  const renderLabel = taskType === "character_sheet" ? "三视图生成" : "图片生成";
  const submitState: TaskStageState = ["RENDERING", "COMPLETED", "FAILED", "PAUSED"].includes(status) ? "done" : "active";
  const renderState: TaskStageState = status === "COMPLETED" ? "done" : status === "FAILED" ? "failed" : status === "PAUSED" ? "paused" : status === "RENDERING" ? "active" : "pending";
  const submitDuration = imageSubmitStageDuration(task);
  const renderDuration = imageRenderStageDuration(task, status);
  const completeDuration = status === "COMPLETED" ? elapsedMs(task?.startedAt, task?.finishedAt) : null;
  return withTaskStageLabels([
    { key: "PENDING", label: "提交任务", state: submitState, durationLabel: formatStageDuration(submitDuration) },
    { key: "RENDERING", label: renderLabel, state: renderState, durationLabel: formatStageDuration(renderDuration) },
    { key: "COMPLETED", label: "生成完成", state: status === "COMPLETED" ? "done" : "pending", durationLabel: status === "COMPLETED" ? formatStageDuration(completeDuration) || "--" : "" },
  ]);
}

export function formatMonitoringValue(value: unknown): string {
  if (value == null) return "暂无";
  if (typeof value === "number") return value > 0 ? String(value) : "暂无";
  return String(value).trim() || "暂无";
}

export function compactIdentifier(value: string, keep = 8): string {
  const text = String(value ?? "").trim();
  if (!text || text === "暂无") return text || "暂无";
  return text.length <= keep + 2 ? text : `#${text.slice(-keep)}`;
}

export function compactPath(value: string): string {
  const text = String(value ?? "").trim();
  if (!text || text === "等待任务创建" || text.length <= 28) return text || "等待任务创建";
  const parts = text.split(/[\\/]/).filter(Boolean);
  return parts.length >= 2 ? `.../${parts.slice(-2).join("/")}` : `...${text.slice(-24)}`;
}

export function normalizedTaskType(task?: Pick<TaskListItem, "taskType"> & { requestSnapshot?: { taskType?: string | null } } | null): string {
  return String(task?.requestSnapshot?.taskType || task?.taskType || "video_generation").trim() || "video_generation";
}

export function taskTypeLabel(task?: Pick<TaskListItem, "taskType"> & { requestSnapshot?: { taskType?: string | null } } | null): string {
  switch (normalizedTaskType(task)) {
    case "image_generation": return "文生图";
    case "image_to_image": return "图生图";
    case "character_sheet": return "角色三视图";
    case "video_generation": return "视频生成";
    default: return "生成任务";
  }
}

export function taskTypeIcon(task?: Pick<TaskListItem, "taskType"> & { requestSnapshot?: { taskType?: string | null } } | null): IconName {
  switch (normalizedTaskType(task)) {
    case "image_generation":
    case "image_to_image": return "image";
    case "character_sheet": return "character";
    case "video_generation": return "video";
    default: return "task";
  }
}

export function isActiveTaskStatus(status?: TaskStatus | null): boolean {
  return Boolean(status && ACTIVE_TASK_STATUSES.has(status));
}

export function firstNonBlank(...values: Array<string | null | undefined>): string {
  return values.map((value) => String(value ?? "").trim()).find(Boolean) ?? "";
}

export function assetUrlKey(url: string): string {
  return String(url ?? "").trim();
}

export function listValue(value: unknown): unknown[] {
  return Array.isArray(value) ? value : [];
}

export function taskFailureContext(task?: Pick<TaskListItem, "failureStage" | "failureClipIndex"> | null): string {
  if (!task) return "";
  const parts: string[] = [];
  if (task.failureStage) parts.push(`阶段 ${task.failureStage}`);
  if (typeof task.failureClipIndex === "number" && task.failureClipIndex > 0) parts.push(`镜头 #${task.failureClipIndex}`);
  return parts.join(" · ");
}

export function taskThumbnailUrl(task?: (TaskListItem | TaskDetail) | null): string {
  return resolveTaskThumbnailUrl(task);
}

export function stageStateClass(state: TaskStageState): string {
  return `task-stage-row--${state}`;
}
