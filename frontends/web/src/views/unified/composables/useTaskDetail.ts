/**
 * 任务详情组合式逻辑。
 * 管理统一任务详情的加载、展示和操作。
 */
import { computed, ref, watch } from "vue";
import { useConfirmDialog } from "@/composables/useConfirmDialog";
import type { TaskDetail, TaskListItem, TaskStatus } from "@/types";
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
import { useTaskDetailCommands } from "./useTaskDetailCommands";
import { useTaskDetailLoader } from "./useTaskDetailLoader";
import {
  assetUrlKey,
  buildImageTaskStages,
  buildVideoTaskStages,
  compactIdentifier,
  compactPath,
  firstNonBlank,
  formatMonitoringValue,
  isActiveTaskStatus,
  listValue,
  normalizedTaskType,
  stageStateClass,
  taskFailureContext,
  taskThumbnailUrl,
  taskTypeIcon,
  taskTypeLabel,
} from "../features/task-detail-presenters";

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
  const failureDetailsOpen = ref(false);

  const { confirmDialog, requestConfirm, acceptConfirm, cancelConfirm } = useConfirmDialog();

  const selectedTaskId = computed(() => options.selectedTaskId());
  const tasks = computed(() => options.tasks());

  const selectedTaskSummary = computed(() => {
    if (!selectedTaskId.value) return null;
    return tasks.value.find((task) => task.id === selectedTaskId.value) ?? null;
  });

  const {
    selectedTaskDetail,
    selectedTaskLoading,
    selectedTaskPreviewMedia,
    selectedTaskAwaitingCompletedPreview,
    loadSelectedTaskDetails,
    refreshSelectedTask,
    startDetailPolling,
    stopDetailPolling,
  } = useTaskDetailLoader({
    selectedTaskId: () => selectedTaskId.value,
    selectedTaskSummary: () => selectedTaskSummary.value,
  });
  const {
    managingTaskId,
    handleRetry,
    handlePause,
    handleContinueTask,
    handleTerminate,
    handleDelete,
  } = useTaskDetailCommands({
    selectedTaskId: () => selectedTaskId.value,
    reloadTasks: options.reloadTasks,
    reloadDetail: loadSelectedTaskDetails,
    requestConfirm,
    onDeleted: options.onDeleted,
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
  const selectedTaskPromptText = computed(() =>
    firstNonBlank(selectedTaskDetail.value?.creativePrompt, selectedTaskRequestSnapshot.value.creativePrompt)
  );
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

  const selectedTaskResultItems = computed(() => {
    const items: Array<{ title: string; url: string }> = [];
    const seenUrls = new Set<string>();
    const detail = selectedTaskDetail.value;
    if (!detail) return items;
    const pushUnique = (title: string, url: string) => {
      const key = assetUrlKey(url);
      if (!key || seenUrls.has(key)) return;
      seenUrls.add(key);
      items.push({ title, url });
    };
    for (const output of detail.outputs ?? []) {
      const url = firstNonBlank(output.downloadUrl, output.downloadPath, output.previewUrl, output.previewPath, output.remoteUrl);
      pushUnique(output.title || `结果 #${output.clipIndex || items.length + 1}`, url);
    }
    const latestJoinUrl = detail.monitoring?.latestJoinOutputUrl;
    pushUnique(detail.monitoring?.latestJoinName || "最新拼接结果", latestJoinUrl || "");
    const latestVideoUrl = detail.monitoring?.latestVideoOutputUrl;
    pushUnique("最新视频结果", latestVideoUrl || "");
    return items;
  });

  const selectedTaskReferenceItems = computed(() => {
    const detail = selectedTaskDetail.value;
    if (!detail) return [];
    const rows: Array<{ title: string; url: string; thumbnailUrl?: string | null }> = [];
    const seenUrls = new Set<string>();
    const pushUnique = (title: string, url: string, thumbnailUrl?: string | null) => {
      const key = assetUrlKey(url);
      if (!key || seenUrls.has(key)) return;
      seenUrls.add(key);
      rows.push({ title, url, thumbnailUrl });
    };
    if (detail.source?.fileUrl) {
      pushUnique(detail.source.originalFileName || "参考图", detail.source.fileUrl, detail.source.thumbnailUrl);
    }
    for (const source of detail.sourceAssets ?? []) {
      pushUnique(source.originalFileName || "参考图", source.fileUrl || "", source.thumbnailUrl);
    }
    for (const [index, url] of listValue(detail.requestSnapshot?.referenceImageUrls).entries()) {
      pushUnique(`参考图 ${index + 1}`, String(url ?? ""), null);
    }
    for (const [index, url] of listValue(detail.executionContext?.referenceImageUrls).entries()) {
      pushUnique(`参考图 ${index + 1}`, String(url ?? ""), null);
    }
    return rows;
  });

  const selectedTaskMaterialItems = computed(() => {
    const detail = selectedTaskDetail.value;
    if (!detail) return [];
    const rows: Array<{ title: string; url: string }> = [];
    const seenUrls = new Set(selectedTaskResultItems.value.map((item) => assetUrlKey(item.url)).filter(Boolean));
    const pushUnique = (title: string, url: string) => {
      const key = assetUrlKey(url);
      if (!key || seenUrls.has(key)) return;
      seenUrls.add(key);
      rows.push({ title, url });
    };
    for (const material of detail.materials ?? []) {
      const url = firstNonBlank(material.publicUrl, material.fileUrl);
      pushUnique(material.title || material.id || "任务素材", url);
    }
    return rows;
  });

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
    if (type !== "video_generation") return buildImageTaskStages(selectedTask.value, status, type);
    return buildVideoTaskStages(status);
  });

  // ── Watch: reset failure details when selection changes ──

  watch(selectedTaskId, () => {
    failureDetailsOpen.value = false;
  });

  return {
    // State
    selectedTaskDetail,
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
    selectedTaskPromptText,
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
    selectedTaskAwaitingCompletedPreview,
    selectedTaskResultItems,
    selectedTaskReferenceItems,
    selectedTaskMaterialItems,
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
    taskStatusTone: (status: TaskStatus) => getTaskStatusMeta(status).tone,
    stageStateClass,
    taskTypeIcon,
    taskThumbnailUrl: (task?: (TaskListItem | TaskDetail) | null) => taskThumbnailUrl(task),
    selectedTaskIsActive: computed(() => isActiveTaskStatus(selectedTaskDetail.value?.status ?? selectedTaskSummary.value?.status)),
    // Polling
    startDetailPolling,
    stopDetailPolling,
  };
}
