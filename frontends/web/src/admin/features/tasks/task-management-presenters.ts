import type { AdminTaskListItem, AdminTaskSortMode, TaskDetail, TaskStatus } from "@/types";

export const ADMIN_TASK_STATUS_OPTIONS: Array<{ label: string; value: TaskStatus }> = [
  { label: "排队中", value: "PENDING" },
  { label: "已暂停", value: "PAUSED" },
  { label: "分析中", value: "ANALYZING" },
  { label: "编排中", value: "PLANNING" },
  { label: "渲染中", value: "RENDERING" },
  { label: "已完成", value: "COMPLETED" },
  { label: "失败", value: "FAILED" },
];

export const ADMIN_TASK_SORT_OPTIONS: Array<{ label: string; value: AdminTaskSortMode }> = [
  { label: "最新创建", value: "created_desc" },
  { label: "最近更新", value: "updated_desc" },
  { label: "进度优先", value: "progress_desc" },
  { label: "状态优先", value: "status_desc" },
];

export function terminableTaskStatus(status: TaskStatus) {
  return ["PENDING", "ANALYZING", "PLANNING", "RENDERING"].includes(status);
}

export function createAdminTaskPresenters(
  getDetail: (task: AdminTaskListItem) => TaskDetail | undefined,
) {
  function formatDateTime(value?: string | null) {
    if (!value) {
      return "未记录";
    }
    return new Date(value).toLocaleString();
  }

  function statusLabel(status: TaskStatus) {
    switch (status) {
      case "PENDING":
        return "排队中";
      case "PAUSED":
        return "已暂停";
      case "ANALYZING":
        return "分析中";
      case "PLANNING":
        return "编排中";
      case "RENDERING":
        return "渲染中";
      case "COMPLETED":
        return "已完成";
      case "FAILED":
        return "失败";
      default:
        return status;
    }
  }

  function statusTagType(status: TaskStatus) {
    switch (status) {
      case "COMPLETED":
        return "success";
      case "FAILED":
        return "danger";
      case "RENDERING":
      case "ANALYZING":
      case "PLANNING":
        return "warning";
      case "PAUSED":
        return "info";
      default:
        return "primary";
    }
  }

  function durationLabel(task: AdminTaskListItem) {
    if (task.minDurationSeconds && task.maxDurationSeconds) {
      return `${task.minDurationSeconds}-${task.maxDurationSeconds} 秒`;
    }
    if (task.minDurationSeconds) {
      return `${task.minDurationSeconds} 秒`;
    }
    if (task.maxDurationSeconds) {
      return `${task.maxDurationSeconds} 秒`;
    }
    return "时长未记录";
  }

  function renderedClipLabel(task: AdminTaskListItem | TaskDetail) {
    const rendered = task.renderedClipCount ?? 0;
    const planned = task.plannedClipCount ?? 0;
    if (planned > 0) {
      return `${rendered}/${planned}`;
    }
    return `${rendered}`;
  }

  function progressHint(task: AdminTaskListItem | TaskDetail) {
    if (task.status === "FAILED") {
      return task.diagnosisHint || "任务执行失败";
    }
    if (task.status === "COMPLETED") {
      return `已产出 ${task.completedOutputCount ?? 0} 个结果`;
    }
    if (task.queuePosition && task.queuePosition > 0) {
      return `队列第 ${task.queuePosition} 位`;
    }
    return task.currentStage || "等待处理";
  }

  function terminableStatus(status: TaskStatus) {
    return terminableTaskStatus(status);
  }

  function expandedDetail(task: AdminTaskListItem) {
    return getDetail(task);
  }

  function requestSnapshot(task: AdminTaskListItem) {
    const detail = expandedDetail(task);
    return (detail?.requestSnapshot ?? detail ?? task) as Record<string, unknown>;
  }

  function formatDetailValue(value: unknown, fallback = "暂无") {
    if (value == null) return fallback;
    if (typeof value === "boolean") return value ? "是" : "否";
    if (typeof value === "number") return Number.isFinite(value) ? String(value) : fallback;
    const text = String(value).trim();
    return text || fallback;
  }

  function formatSecondsValue(value: unknown) {
    if (typeof value !== "number" || !Number.isFinite(value) || value <= 0) return "暂无";
    return `${Number.isInteger(value) ? value : value.toFixed(1)} 秒`;
  }

  function formatModelValue(value: unknown) {
    return formatDetailValue(value, "未指定");
  }

  function formatOutputCount(snapshot: Record<string, unknown>) {
    const count = snapshot.outputCount;
    if (count === "auto") return "自动";
    if (typeof count === "number" && count > 0) return String(count);
    if (count && typeof count === "object") {
      const value = count as { auto?: boolean; count?: number | string | null };
      if (value.auto) return "自动";
      return formatDetailValue(value.count, "默认");
    }
    return "默认";
  }

  function formatRequestedDuration(snapshot: Record<string, unknown>) {
    const value = snapshot.videoDurationSeconds;
    if (value === "auto") return "自动";
    if (typeof value === "number" && value > 0) return `${value} 秒`;
    return "未指定";
  }

  function formatSeed(task: AdminTaskListItem) {
    const detail = expandedDetail(task);
    const snapshot = requestSnapshot(task);
    const seed = detail?.taskSeed ?? task.taskSeed ?? snapshot.seed;
    if (typeof seed === "number" && Number.isFinite(seed)) return String(Math.trunc(seed));
    return "未设置";
  }

  function detailProgressValue(task: AdminTaskListItem) {
    const progress = expandedDetail(task)?.progress ?? task.progress ?? 0;
    return Math.min(100, Math.max(0, Math.trunc(progress)));
  }

  function requestDurationMode(task: AdminTaskListItem) {
    const mode = requestSnapshot(task).durationMode;
    return `时长模式 ${formatDetailValue(mode, "auto")}`;
  }

  function executionRows(task: AdminTaskListItem) {
    const detail = expandedDetail(task);
    const monitoring = detail?.monitoring;
    return [
      {
        label: "当前阶段",
        value: formatDetailValue(monitoring?.currentStage ?? detail?.currentStage ?? task.currentStage, "等待处理"),
      },
      { label: "Attempt 状态", value: formatDetailValue(monitoring?.activeAttemptStatus) },
      {
        label: "Worker",
        value: formatDetailValue(
          monitoring?.activeWorkerInstanceId ?? detail?.activeWorkerInstanceId ?? task.activeWorkerInstanceId,
        ),
      },
      {
        label: "队列位置",
        value:
          detail?.isQueued || task.isQueued
            ? formatDetailValue(detail?.queuePosition ?? task.queuePosition, "排队中")
            : "未排队",
      },
      { label: "恢复阶段", value: formatDetailValue(monitoring?.resumeFromStage) },
      { label: "恢复镜头", value: formatDetailValue(monitoring?.resumeFromClipIndex) },
      { label: "开始时间", value: formatDateTime(detail?.startedAt ?? task.startedAt) },
      { label: "结束时间", value: formatDateTime(detail?.finishedAt ?? task.finishedAt) },
    ];
  }

  function failureMessage(task: AdminTaskListItem) {
    const detail = expandedDetail(task);
    return formatDetailValue(detail?.failureReason || detail?.errorMessage || task.failureReason || "", "");
  }

  function failureStateLabel(task: AdminTaskListItem) {
    return failureMessage(task) ? "已记录" : "暂无";
  }

  function failureTagType(task: AdminTaskListItem) {
    return failureMessage(task) ? "danger" : "info";
  }

  function failureRows(task: AdminTaskListItem) {
    const detail = expandedDetail(task);
    return [
      { label: "错误消息", value: formatDetailValue(detail?.errorMessage || task.failureReason) },
      { label: "失败阶段", value: formatDetailValue(detail?.failureStage ?? task.failureStage) },
      { label: "失败镜头", value: formatDetailValue(detail?.failureClipIndex ?? task.failureClipIndex) },
      { label: "诊断提示", value: formatDetailValue(detail?.diagnosisHint ?? task.diagnosisHint) },
      { label: "推荐动作", value: formatDetailValue(detail?.recommendedAction ?? task.recommendedAction) },
    ];
  }

  function requestRows(task: AdminTaskListItem) {
    const detail = expandedDetail(task);
    const snapshot = requestSnapshot(task);
    return [
      { label: "任务类型", value: formatDetailValue(snapshot.taskType ?? detail?.taskType ?? task.taskType) },
      { label: "素材类型", value: formatDetailValue(snapshot.assetType) },
      { label: "画幅比例", value: formatDetailValue(snapshot.aspectRatio ?? detail?.aspectRatio ?? task.aspectRatio) },
      { label: "图片尺寸", value: formatModelValue(snapshot.imageSize) },
      { label: "视频清晰度", value: formatModelValue(snapshot.videoSize) },
      { label: "文本模型", value: formatModelValue(snapshot.textAnalysisModel) },
      { label: "关键帧模型", value: formatModelValue(snapshot.imageModel) },
      { label: "视频模型", value: formatModelValue(snapshot.videoModel) },
      { label: "输出数量", value: formatOutputCount(snapshot) },
      { label: "请求时长", value: formatRequestedDuration(snapshot) },
      { label: "生效时长", value: durationLabel(detail || task) },
      { label: "任务 Seed", value: formatSeed(task) },
      { label: "提前停止视频生成", value: snapshot.stopBeforeVideoGeneration ? "已启用" : "否" },
      { label: "文本输入", value: snapshot.transcriptText || detail?.transcriptPreview ? "已提供" : "无文本输入" },
    ];
  }

  function creativePrompt(task: AdminTaskListItem) {
    const detail = expandedDetail(task);
    return formatDetailValue(detail?.creativePrompt ?? requestSnapshot(task).creativePrompt, "");
  }

  function transcriptPreview(task: AdminTaskListItem) {
    const detail = expandedDetail(task);
    const text = formatDetailValue(detail?.transcriptPreview ?? requestSnapshot(task).transcriptText, "");
    return text.length > 220 ? `${text.slice(0, 220)}...` : text;
  }

  function requestSnapshotJson(task: AdminTaskListItem) {
    const snapshot = requestSnapshot(task);
    if (!Object.keys(snapshot).length) return "";
    return JSON.stringify(snapshot, null, 2);
  }

  function outputRows(task: AdminTaskListItem) {
    const detail = expandedDetail(task);
    const monitoring = detail?.monitoring;
    const directories = detail?.artifactDirectories ?? monitoring?.artifactDirectories;
    return [
      {
        label: "素材数量",
        value: formatDetailValue(detail?.sourceAssetCount ?? task.sourceAssetCount ?? detail?.sourceAssets?.length ?? 0),
      },
      {
        label: "结果数量",
        value: formatDetailValue(
          detail?.completedOutputCount ?? task.completedOutputCount ?? detail?.outputs?.length ?? 0,
        ),
      },
      {
        label: "计划镜头",
        value: formatDetailValue(monitoring?.plannedClipCount ?? detail?.plannedClipCount ?? task.plannedClipCount),
      },
      {
        label: "已生成镜头",
        value: formatDetailValue(monitoring?.renderedClipCount ?? detail?.renderedClipCount ?? task.renderedClipCount),
      },
      { label: "连续完成镜头", value: formatDetailValue(monitoring?.contiguousRenderedClipCount) },
      { label: "最新片段", value: formatDetailValue(monitoring?.latestRenderedClipIndex) },
      { label: "最新拼接", value: formatDetailValue(monitoring?.latestJoinName) },
      { label: "任务目录", value: formatDetailValue(directories?.baseRelativeDir ?? directories?.baseAbsoluteDir) },
      { label: "运行目录", value: formatDetailValue(directories?.runningRelativeDir ?? directories?.runningAbsoluteDir) },
      { label: "脚本文件", value: formatDetailValue(directories?.storyboardFileName) },
      { label: "源文件", value: formatDetailValue(detail?.sourceFileName ?? task.sourceFileName) },
      { label: "源文件列表", value: formatDetailValue(detail?.sourceFileNames?.join("、")) },
      {
        label: "输出时长",
        value: formatSecondsValue(
          (monitoring?.latestVideoOutput as { durationSeconds?: number } | undefined)?.durationSeconds,
        ),
      },
    ];
  }

  return {
    formatDateTime,
    statusLabel,
    statusTagType,
    durationLabel,
    renderedClipLabel,
    progressHint,
    terminableStatus,
    expandedDetail,
    detailProgressValue,
    requestDurationMode,
    executionRows,
    failureMessage,
    failureStateLabel,
    failureTagType,
    failureRows,
    requestRows,
    creativePrompt,
    transcriptPreview,
    requestSnapshotJson,
    outputRows,
  };
}
