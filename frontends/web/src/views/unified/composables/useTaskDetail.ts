/**
 * 任务详情组合式逻辑。
 * 从 TasksView 中提取，管理任务详情的加载、展示和操作。
 */
import { computed, ref, watch } from "vue";
import { requireAuth } from "@/auth/modal";
import { usePolling } from "@/composables/usePolling";
import { useConfirmDialog } from "@/composables/useConfirmDialog";
import { continueTask, deleteTask, fetchTask, fetchTaskTrace, pauseTask, retryTask, terminateTask } from "@/features/tasks";
import { messageApi } from "@/composables/useMessage";
import type { TaskDetail, TaskListItem, TaskStatus, TaskTraceEvent } from "@/types";
import type { IconName } from "@/components/icons";
import {
  formatTaskDurationMode,
  formatTaskModelValue,
  formatTaskOutputCount,
  formatTaskRequestedDuration,
  formatTaskResolvedDuration,
  formatTaskSeed,
  formatTaskStopBeforeVideoGeneration,
  formatTaskTranscriptSummary,
  getTaskResolutionRow,
  getTaskRequestSnapshot,
  previewTaskTranscript,
} from "@/utils/task-request";
import { formatTaskStatus } from "@/utils/task";
import { getTaskStatusMeta } from "@/utils/presentation";
import { resolveTaskPreviewMedia, resolveTaskThumbnailUrl } from "@/utils/task-preview";

type TaskStageState = "pending" | "active" | "paused" | "done" | "failed";
const ACTIVE_TASK_STATUSES = new Set<TaskStatus>(["PENDING", "ANALYZING", "PLANNING", "RENDERING", "PAUSED"]);

interface TaskStageDisplayItem {
  key: string;
  label: string;
  state: TaskStageState;
  stateLabel: string;
}

const taskStageStateLabels: Record<TaskStageState, string> = {
  pending: "等待",
  active: "进行中",
  paused: "已暂停",
  done: "已完成",
  failed: "失败",
};

function withTaskStageLabels(items: Array<Omit<TaskStageDisplayItem, "stateLabel">>): TaskStageDisplayItem[] {
  return items.map((item) => ({ ...item, stateLabel: taskStageStateLabels[item.state] }));
}

function buildVideoTaskStages(status: TaskStatus): TaskStageDisplayItem[] {
  const stageOrder: TaskStatus[] = ["ANALYZING", "PLANNING", "RENDERING", "COMPLETED"];
  const pausedAtRender = status === "PAUSED";
  const currentIndex = pausedAtRender ? 2 : stageOrder.indexOf(status);
  const items = [
    { key: "ANALYZING", label: "素材分析", state: currentIndex > 0 ? "done" : currentIndex === 0 ? "active" : "pending" },
    { key: "PLANNING", label: "任务编排", state: currentIndex > 1 ? "done" : currentIndex === 1 ? "active" : "pending" },
    { key: "RENDERING", label: "视频生成", state: pausedAtRender ? "paused" : currentIndex > 2 ? "done" : currentIndex === 2 ? "active" : "pending" },
    { key: "COMPLETED", label: "任务完成", state: status === "COMPLETED" ? "done" : status === "FAILED" ? "failed" : "pending" },
  ] as Array<Omit<TaskStageDisplayItem, "stateLabel">>;
  return withTaskStageLabels(items);
}

function buildImageTaskStages(status: TaskStatus, taskType: string): TaskStageDisplayItem[] {
  const renderLabel = taskType === "character_sheet" ? "三视图生成" : "图片生成";
  const submitState: TaskStageState = ["RENDERING", "COMPLETED", "FAILED"].includes(status) ? "done" : status === "PAUSED" ? "paused" : "active";
  const renderState: TaskStageState =
    status === "COMPLETED" ? "done" :
    status === "FAILED" ? "failed" :
    status === "PAUSED" ? "paused" :
    status === "RENDERING" ? "active" :
    "pending";
  const completeState: TaskStageState = status === "COMPLETED" ? "done" : "pending";
  return withTaskStageLabels([
    { key: "PENDING", label: "提交任务", state: submitState },
    { key: "RENDERING", label: renderLabel, state: renderState },
    { key: "COMPLETED", label: "生成完成", state: completeState },
  ]);
}

function formatMonitoringValue(value: unknown): string {
  if (value == null) return "暂无";
  if (typeof value === "number") return value > 0 ? String(value) : "暂无";
  const text = String(value).trim();
  return text ? text : "暂无";
}

function compactIdentifier(value: string, keep = 8): string {
  const text = String(value ?? "").trim();
  if (!text || text === "暂无") return text || "暂无";
  if (text.length <= keep + 2) return text;
  return `#${text.slice(-keep)}`;
}

function compactPath(value: string): string {
  const text = String(value ?? "").trim();
  if (!text || text === "等待任务创建" || text.length <= 28) return text || "等待任务创建";
  const parts = text.split(/[\\/]/).filter(Boolean);
  if (parts.length >= 2) return `.../${parts.slice(-2).join("/")}`;
  return `...${text.slice(-24)}`;
}

function normalizedTaskType(task?: Pick<TaskListItem, "taskType"> & { requestSnapshot?: { taskType?: string | null } } | null): string {
  return String(task?.requestSnapshot?.taskType || task?.taskType || "video_generation").trim() || "video_generation";
}

function taskTypeLabel(task?: Pick<TaskListItem, "taskType"> & { requestSnapshot?: { taskType?: string | null } } | null): string {
  switch (normalizedTaskType(task)) {
    case "image_generation": return "文生图";
    case "image_to_image": return "图生图";
    case "character_sheet": return "角色三视图";
    case "video_generation": return "视频生成";
    default: return "生成任务";
  }
}

function taskTypeIcon(task?: Pick<TaskListItem, "taskType"> & { requestSnapshot?: { taskType?: string | null } } | null): IconName {
  switch (normalizedTaskType(task)) {
    case "image_generation":
    case "image_to_image": return "image";
    case "character_sheet": return "character";
    case "video_generation": return "video";
    default: return "task";
  }
}

function isActiveTaskStatus(status?: TaskStatus | null): boolean {
  return Boolean(status && ACTIVE_TASK_STATUSES.has(status));
}

function firstNonBlank(...values: Array<string | null | undefined>): string {
  for (const value of values) {
    const normalized = String(value ?? "").trim();
    if (normalized) return normalized;
  }
  return "";
}

function listValue(value: unknown): unknown[] {
  return Array.isArray(value) ? value : [];
}

function taskFailureContext(task?: Pick<TaskListItem, "failureStage" | "failureClipIndex"> | null): string {
  if (!task) return "";
  const parts: string[] = [];
  if (task.failureStage) parts.push(`阶段 ${task.failureStage}`);
  if (typeof task.failureClipIndex === "number" && task.failureClipIndex > 0) parts.push(`镜头 #${task.failureClipIndex}`);
  return parts.join(" · ");
}

function taskThumbnailUrl(task?: (TaskListItem | TaskDetail) | null): string {
  return resolveTaskThumbnailUrl(task);
}

function stageStateClass(state: TaskStageState): string {
  switch (state) {
    case "done": return "task-stage-row--done";
    case "active": return "task-stage-row--active";
    case "paused": return "task-stage-row--paused";
    case "failed": return "task-stage-row--failed";
    default: return "task-stage-row--pending";
  }
}

function formatDateTime(value?: string | null): string {
  if (!value) return "-";
  const timestamp = new Date(value).getTime();
  if (!Number.isFinite(timestamp)) return value;
  return new Date(timestamp).toLocaleString();
}

/**
 * 将追踪事件的 stage 值映射为可读中文标签。
 */
const TRACE_STAGE_LABELS: Record<string, string> = {
  api: "接口",
  analysis: "分析",
  planning: "编排",
  rendering: "渲染",
  pipeline: "流水线",
  feedback: "反馈",
  dispatch: "调度",
};

function formatTraceStage(stage: string): string {
  if (!stage) return "系统";
  const lower = stage.toLowerCase();
  return TRACE_STAGE_LABELS[lower] ?? stage;
}

/**
 * 将追踪事件的 event 值映射为可读中文标签。
 */
const TRACE_EVENT_LABELS: Record<string, string> = {
  "task.created": "创建任务",
  "task.enqueued": "加入队列",
  "task.claimed": "领取任务",
  "task.analyzing": "开始分析",
  "task.planning": "开始编排",
  "task.rendering": "开始渲染",
  "task.completed": "任务完成",
  "task.failed": "任务失败",
  "task.paused": "暂停任务",
  "task.continued": "继续任务",
  "task.terminated": "终止任务",
  "task.retried": "重试任务",
  "task.deleted": "删除任务",
  "task.effect_rated": "效果评分",
  "analysis.reused": "复用已有分析",
  "planning.shots_resolved": "镜头解析完成",
  "planning.keyframe_reused_for_resume": "恢复已有进度",
  "planning.keyframe_reused_from_last_frame": "复用上一镜尾帧",
  "generation.call": "调用生成服务",
};

function formatTraceEvent(event: string): string {
  if (!event) return "事件";
  return TRACE_EVENT_LABELS[event] ?? event;
}

export interface UseTaskDetailOptions {
  /** 当前选中的任务 ID */
  selectedTaskId: () => string;
  /** 任务列表引用（用于获取列表中的摘要数据） */
  tasks: () => TaskListItem[];
  /** 列表重新加载回调 */
  reloadTasks: () => Promise<void>;
  /** 任务删除成功后的回调（用于通知父组件清除选中状态） */
  onDeleted?: (taskId: string) => void;
}

export function useTaskDetail(options: UseTaskDetailOptions) {
  const selectedTaskDetail = ref<TaskDetail | null>(null);
  const selectedTaskTrace = ref<TaskTraceEvent[]>([]);
  const selectedTaskLoading = ref(false);
  const managingTaskId = ref("");
  const failureDetailsOpen = ref(false);

  const { confirmDialog, requestConfirm, acceptConfirm, cancelConfirm } = useConfirmDialog();

  const selectedTaskId = computed(() => options.selectedTaskId());
  const tasks = computed(() => options.tasks());

  const selectedTaskSummary = computed(() => {
    if (!selectedTaskId.value) return null;
    return tasks.value.find((task) => task.id === selectedTaskId.value) ?? null;
  });

  const selectedTask = computed(() => selectedTaskDetail.value ?? selectedTaskSummary.value);
  const selectedTaskActionTask = computed(() => selectedTaskDetail.value ?? selectedTaskSummary.value);
  const selectedTaskTypeLabel = computed(() => taskTypeLabel(selectedTask.value));
  const selectedTaskShortId = computed(() => compactIdentifier(selectedTaskId.value, 8));

  const selectedTaskStageLabel = computed(() => {
    if (selectedTaskDetail.value) return formatTaskStatus(selectedTaskDetail.value.status);
    if (selectedTaskSummary.value) return formatTaskStatus(selectedTaskSummary.value.status);
    return "等待更新";
  });

  const selectedTaskRequestSnapshot = computed(() => getTaskRequestSnapshot(selectedTaskDetail.value));
  const selectedTaskDurationModeLabel = computed(() => formatTaskDurationMode(selectedTaskRequestSnapshot.value));
  const selectedTaskTranscriptPreview = computed(() => previewTaskTranscript(selectedTaskRequestSnapshot.value));

  const selectedReferenceImageCount = computed(() => {
    const snapshotCount = listValue(selectedTaskDetail.value?.requestSnapshot?.referenceImageUrls).length;
    const contextCount = listValue(selectedTaskDetail.value?.executionContext?.referenceImageUrls).length;
    const sourceCount = selectedTaskDetail.value?.sourceAssetCount ?? selectedTaskSummary.value?.sourceAssetCount ?? 0;
    return Math.max(snapshotCount, contextCount, sourceCount);
  });

  const selectedTaskSeedLabel = computed(() => {
    const detailSeed = selectedTaskDetail.value?.taskSeed;
    if (typeof detailSeed === "number" && Number.isFinite(detailSeed)) return String(Math.trunc(detailSeed));
    const summarySeed = selectedTaskSummary.value?.taskSeed;
    if (typeof summarySeed === "number" && Number.isFinite(summarySeed)) return String(Math.trunc(summarySeed));
    return formatTaskSeed(selectedTaskRequestSnapshot.value);
  });

  const selectedTaskParameterRows = computed(() => {
    const task = selectedTaskDetail.value;
    if (!task) return [];
    const snapshot = selectedTaskRequestSnapshot.value;
    return [
      { label: "文本模型", value: formatTaskModelValue(snapshot.textAnalysisModel) },
      { label: "关键帧模型", value: formatTaskModelValue(snapshot.imageModel) },
      { label: "视频模型", value: formatTaskModelValue(snapshot.videoModel) },
      getTaskResolutionRow(snapshot, task.executionContext),
      { label: "输出数量", value: formatTaskOutputCount(snapshot) },
      { label: "请求时长", value: formatTaskRequestedDuration(snapshot) },
      { label: "生效时长", value: formatTaskResolvedDuration(task) },
      { label: "任务种子", value: selectedTaskSeedLabel.value },
      { label: "提前停止视频生成", value: formatTaskStopBeforeVideoGeneration(snapshot) },
      { label: "文本输入", value: formatTaskTranscriptSummary(snapshot) },
      { label: "画幅比例", value: formatTaskModelValue(snapshot.aspectRatio || task.aspectRatio) },
    ];
  });

  const selectedTaskCompactParameterRows = computed(() => selectedTaskParameterRows.value.slice(0, 6));

  const selectedTaskJoinProgressPercent = computed(() => {
    const status = selectedTaskDetail.value?.status ?? selectedTaskSummary.value?.status;
    if (status === "COMPLETED") return 100;
    const progress = selectedTaskDetail.value?.progress ?? selectedTaskSummary.value?.progress ?? 0;
    return Math.max(0, Math.min(100, Math.round(progress)));
  });

  const selectedTaskMonitoringRows = computed(() => {
    const monitoring = selectedTaskDetail.value?.monitoring;
    if (!monitoring) return [];
    return [
      { label: "当前阶段", value: formatMonitoringValue(monitoring.currentStage) },
      { label: "尝试状态", value: formatMonitoringValue(monitoring.activeAttemptStatus) },
      { label: "恢复阶段", value: formatMonitoringValue(monitoring.resumeFromStage) },
      { label: "恢复镜头", value: formatMonitoringValue(monitoring.resumeFromClipIndex) },
      { label: "计划镜头数", value: formatMonitoringValue(monitoring.plannedClipCount) },
      { label: "已生成镜头数", value: formatMonitoringValue(monitoring.renderedClipCount) },
      { label: "连续完成镜头", value: formatMonitoringValue(monitoring.contiguousRenderedClipCount) },
      { label: "最新片段", value: formatMonitoringValue(monitoring.latestRenderedClipIndex) },
    ].filter((item) => item.value !== "暂无");
  });

  const selectedTaskWorkerLabel = computed(() => formatMonitoringValue(selectedTaskDetail.value?.monitoring?.activeWorkerInstanceId));
  const selectedTaskShortWorkerLabel = computed(() => compactIdentifier(selectedTaskWorkerLabel.value, 10));
  const selectedTaskCompactMonitoringRows = computed(() => selectedTaskMonitoringRows.value.slice(0, 5));

  const selectedTaskFailureReason = computed(() =>
    selectedTaskDetail.value?.failureReason || selectedTaskSummary.value?.failureReason || ""
  );
  const selectedTaskFailureContext = computed(() =>
    taskFailureContext(selectedTaskDetail.value ?? selectedTaskSummary.value)
  );

  const selectedTaskThumbnailUrl = computed(() =>
    taskThumbnailUrl(selectedTaskDetail.value ?? selectedTaskSummary.value)
  );

  const selectedTaskPreviewMedia = computed(() =>
    resolveTaskPreviewMedia(selectedTaskDetail.value ?? selectedTaskSummary.value)
  );

  const selectedTaskResultItems = computed(() => {
    const items: Array<{ title: string; url: string }> = [];
    const detail = selectedTaskDetail.value;
    if (!detail) return items;
    for (const output of detail.outputs ?? []) {
      const url = firstNonBlank(output.downloadUrl, output.downloadPath, output.previewUrl, output.previewPath, output.remoteUrl);
      if (url) items.push({ title: output.title || `结果 #${output.clipIndex || items.length + 1}`, url });
    }
    const latestJoinUrl = detail.monitoring?.latestJoinOutputUrl;
    if (latestJoinUrl && !items.some((item) => item.url === latestJoinUrl)) {
      items.push({ title: detail.monitoring?.latestJoinName || "最新拼接结果", url: latestJoinUrl });
    }
    const latestVideoUrl = detail.monitoring?.latestVideoOutputUrl;
    if (latestVideoUrl && !items.some((item) => item.url === latestVideoUrl)) {
      items.push({ title: "最新视频结果", url: latestVideoUrl });
    }
    return items;
  });

  const selectedTaskMaterialItems = computed(() => {
    const detail = selectedTaskDetail.value;
    if (!detail) return [];
    const rows: Array<{ title: string; url: string }> = [];
    for (const material of detail.materials ?? []) {
      const url = firstNonBlank(material.fileUrl, material.previewUrl, material.thumbnailUrl);
      if (url) rows.push({ title: material.title || material.id || "任务素材", url });
    }
    if (detail.source?.fileUrl) {
      rows.push({ title: detail.source.originalFileName || "来源素材", url: detail.source.fileUrl });
    }
    for (const source of detail.sourceAssets ?? []) {
      if (source.fileUrl && !rows.some((item) => item.url === source.fileUrl)) {
        rows.push({ title: source.originalFileName || "来源素材", url: source.fileUrl });
      }
    }
    return rows;
  });

  const selectedTaskTracePreview = computed(() => selectedTaskTrace.value.slice(0, 16));

  const materialLibraryLink = computed(() => {
    const assetType = selectedTaskDetail.value?.requestSnapshot?.assetType;
    return assetType ? `/materials?assetType=${encodeURIComponent(assetType)}` : "/materials";
  });

  const selectedTaskArtifactDirectories = computed(() =>
    selectedTaskDetail.value?.artifactDirectories ?? selectedTaskDetail.value?.monitoring?.artifactDirectories ?? null
  );

  const selectedTaskArtifactDirectoryHint = computed(() => {
    const dirs = selectedTaskArtifactDirectories.value;
    if (!dirs?.baseRelativeDir) return "等待任务创建";
    return dirs.baseRelativeDir;
  });

  const selectedTaskShortArtifactDirectoryHint = computed(() => compactPath(selectedTaskArtifactDirectoryHint.value));

  const selectedTaskArtifactRows = computed(() => {
    const dirs = selectedTaskArtifactDirectories.value;
    if (!dirs) return [];
    return [
      { label: "存储根目录", value: formatMonitoringValue(dirs.storageRoot) },
      { label: "任务基目录", value: formatMonitoringValue(dirs.baseAbsoluteDir || dirs.baseRelativeDir) },
      { label: "运行目录", value: formatMonitoringValue(dirs.runningAbsoluteDir || dirs.runningRelativeDir) },
      { label: "拼接目录", value: formatMonitoringValue(dirs.joinedAbsoluteDir || dirs.joinedRelativeDir) },
      { label: "脚本文件", value: formatMonitoringValue(dirs.storyboardFileName) },
      { label: "首帧命名", value: formatMonitoringValue(dirs.firstFramePattern) },
      { label: "尾帧命名", value: formatMonitoringValue(dirs.lastFramePattern) },
      { label: "片段命名", value: formatMonitoringValue(dirs.clipPattern) },
      { label: "拼接命名", value: formatMonitoringValue(dirs.joinPattern) },
    ].filter((item) => item.value !== "暂无");
  });

  const selectedTaskCompactArtifactRows = computed(() => selectedTaskArtifactRows.value.slice(0, 5));

  const selectedTaskStages = computed(() => {
    const status = selectedTaskDetail.value?.status ?? selectedTaskSummary.value?.status ?? "PENDING";
    const type = normalizedTaskType(selectedTask.value);
    if (type !== "video_generation") return buildImageTaskStages(status, type);
    return buildVideoTaskStages(status);
  });

  // ── Data loading ──

  async function loadSelectedTaskDetails(opts: { silent?: boolean; includeTrace?: boolean } = {}) {
    if (!selectedTaskId.value) {
      selectedTaskDetail.value = null;
      selectedTaskTrace.value = [];
      return;
    }
    if (!opts.silent) selectedTaskLoading.value = true;
    try {
      const previousStatus = selectedTaskDetail.value?.status ?? selectedTaskSummary.value?.status;
      const includeTrace = opts.includeTrace ?? (!opts.silent || isActiveTaskStatus(previousStatus));
      const detailPromise = fetchTask(selectedTaskId.value);
      const tracePromise = includeTrace ? fetchTaskTrace(selectedTaskId.value, 120) : Promise.resolve(null);
      const [detail, trace] = await Promise.all([detailPromise, tracePromise]);
      selectedTaskDetail.value = detail;
      if (trace) {
        selectedTaskTrace.value = [...trace].reverse();
      }
      if (!isActiveTaskStatus(detail.status)) {
        detailPolling.stop();
      }
    } catch (error) {
      if (!opts.silent) {
        messageApi.error(error instanceof Error ? error.message : "任务详情加载失败");
      }
    } finally {
      if (!opts.silent) selectedTaskLoading.value = false;
    }
  }

  async function refreshSelectedTask() {
    await loadSelectedTaskDetails();
  }

  // ── Action handlers ──

  async function handleRetry(task: TaskListItem) {
    if (managingTaskId.value) return;
    const authenticated = await requireAuth({ title: "登录后操作任务", message: "任务重试会重新加入队列，请先登录或使用邀请码注册。" });
    if (!authenticated) { messageApi.error("登录后可继续操作任务"); return; }
    managingTaskId.value = task.id;
    try {
      await retryTask(task.id);
      await Promise.all([
        options.reloadTasks(),
        task.id === selectedTaskId.value ? loadSelectedTaskDetails() : Promise.resolve(),
      ]);
    } catch (error) {
      messageApi.error(error instanceof Error ? error.message : "重试任务失败");
    } finally {
      managingTaskId.value = "";
    }
  }

  async function handlePause(task: TaskListItem) {
    if (managingTaskId.value) return;
    const authenticated = await requireAuth({ title: "登录后操作任务", message: "任务操作会修改你的任务状态，请先登录或使用邀请码注册。" });
    if (!authenticated) { messageApi.error("登录后可继续操作任务"); return; }
    managingTaskId.value = task.id;
    try {
      await pauseTask(task.id);
      await Promise.all([options.reloadTasks(), loadSelectedTaskDetails()]);
    } catch (error) {
      messageApi.error(error instanceof Error ? error.message : "暂停任务失败");
    } finally {
      managingTaskId.value = "";
    }
  }

  async function handleContinueTask(task: TaskListItem) {
    if (managingTaskId.value) return;
    const authenticated = await requireAuth({ title: "登录后操作任务", message: "任务操作会修改你的任务状态，请先登录或使用邀请码注册。" });
    if (!authenticated) { messageApi.error("登录后可继续操作任务"); return; }
    managingTaskId.value = task.id;
    try {
      await continueTask(task.id);
      await Promise.all([options.reloadTasks(), loadSelectedTaskDetails()]);
    } catch (error) {
      messageApi.error(error instanceof Error ? error.message : "继续任务失败");
    } finally {
      managingTaskId.value = "";
    }
  }

  async function handleTerminate(task: TaskListItem) {
    if (managingTaskId.value) return;
    const authenticated = await requireAuth({ title: "登录后操作任务", message: "任务操作会修改你的任务状态，请先登录或使用邀请码注册。" });
    if (!authenticated) { messageApi.error("登录后可继续操作任务"); return; }
    const ok = await requestConfirm({
      title: "终止任务",
      message: `任务会变为失败状态，可再删除或重试：${task.title || "未命名任务"}`,
      confirmText: "终止",
    });
    if (!ok) return;
    managingTaskId.value = task.id;
    try {
      await terminateTask(task.id);
      await Promise.all([options.reloadTasks(), loadSelectedTaskDetails()]);
    } catch (error) {
      messageApi.error(error instanceof Error ? error.message : "终止任务失败");
    } finally {
      managingTaskId.value = "";
    }
  }

  async function handleDelete(task: TaskListItem) {
    if (managingTaskId.value) return;
    const authenticated = await requireAuth({ title: "登录后操作任务", message: "任务删除后无法恢复，请先登录或使用邀请码注册。" });
    if (!authenticated) { messageApi.error("登录后可继续操作任务"); return; }
    const ok = await requestConfirm({
      title: "删除任务",
      message: `删除后无法恢复：${task.title || "未命名任务"}`,
      confirmText: "删除",
    });
    if (!ok) return;
    managingTaskId.value = task.id;
    try {
      await deleteTask(task.id);
      await options.reloadTasks();
      messageApi.success("任务已删除");
      options.onDeleted?.(task.id);
    } catch (error) {
      messageApi.error(error instanceof Error ? error.message : "删除任务失败");
    } finally {
      managingTaskId.value = "";
    }
  }

  // ── Polling for detail refresh ──

  const detailPolling = usePolling(async () => {
    const status = selectedTaskDetail.value?.status ?? selectedTaskSummary.value?.status;
    if (!isActiveTaskStatus(status)) {
      detailPolling.stop();
      return;
    }
    await loadSelectedTaskDetails({ silent: true });
  }, 5000);

  // ── Watch: reset failure details when selection changes ──

  watch(selectedTaskId, () => {
    failureDetailsOpen.value = false;
  });

  return {
    // State
    selectedTaskDetail,
    selectedTaskTrace,
    selectedTaskLoading,
    managingTaskId,
    failureDetailsOpen,
    // Confirm dialog
    confirmDialog,
    requestConfirm,
    acceptConfirm,
    cancelConfirm,
    // Computed - display
    selectedTask,
    selectedTaskActionTask,
    selectedTaskTypeLabel,
    selectedTaskShortId,
    selectedTaskStageLabel,
    selectedTaskDurationModeLabel,
    selectedTaskTranscriptPreview,
    selectedReferenceImageCount,
    selectedTaskSeedLabel,
    selectedTaskParameterRows,
    selectedTaskCompactParameterRows,
    selectedTaskJoinProgressPercent,
    selectedTaskMonitoringRows,
    selectedTaskShortWorkerLabel,
    selectedTaskCompactMonitoringRows,
    selectedTaskFailureReason,
    selectedTaskFailureContext,
    selectedTaskThumbnailUrl,
    selectedTaskPreviewMedia,
    selectedTaskResultItems,
    selectedTaskMaterialItems,
    selectedTaskTracePreview,
    materialLibraryLink,
    selectedTaskArtifactRows,
    selectedTaskShortArtifactDirectoryHint,
    selectedTaskCompactArtifactRows,
    selectedTaskArtifactDirectoryHint,
    selectedTaskStages,
    // Functions
    loadSelectedTaskDetails,
    refreshSelectedTask,
    handleRetry,
    handlePause,
    handleContinueTask,
    handleTerminate,
    handleDelete,
    formatDateTime,
    formatTraceStage,
    formatTraceEvent,
    taskStatusTone: (status: TaskStatus) => getTaskStatusMeta(status).tone,
    stageStateClass,
    taskTypeIcon,
    taskThumbnailUrl: (task?: (TaskListItem | TaskDetail) | null) => taskThumbnailUrl(task),
    selectedTaskIsActive: computed(() => isActiveTaskStatus(selectedTaskDetail.value?.status ?? selectedTaskSummary.value?.status)),
    // Polling
    startDetailPolling: () => detailPolling.start(false),
    stopDetailPolling: () => detailPolling.stop(),
  };
}
