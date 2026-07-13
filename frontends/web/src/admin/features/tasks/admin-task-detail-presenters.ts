import { computed, type Ref } from "vue";
import type {
  AdminTaskDiagnosis,
  TaskDetail,
  TaskDurationDiagnosticClip,
  TaskTraceEvent,
} from "@/types";

interface AdminTaskDetailPresenterState {
  task: Ref<TaskDetail | null>;
  traceEvents: Ref<TaskTraceEvent[]>;
  diagnosis: Ref<AdminTaskDiagnosis | null>;
}

export function useAdminTaskDetailPresenters({
  task,
  traceEvents,
  diagnosis,
}: AdminTaskDetailPresenterState) {
  const runningTask = computed(() => Boolean(task.value && (task.value.status === "ANALYZING" || task.value.status === "PLANNING" || task.value.status === "RENDERING")));

  const planningSummary = computed(() => {
    if (!task.value?.plan?.length) {
      return { label: "暂无计划", title: "待生成", detail: "待生成" };
    }
    if (task.value.hasTimedTranscript) {
      return { label: "时间轴输入", title: "按时间轴推进", detail: "按时间轴推进。" };
    }
    return { label: "任务生成", title: "标准生成链路", detail: "标准生成链路。" };
  });

  const requestSnapshot = computed(() => {
    return (task.value?.requestSnapshot ?? task.value) as Record<string, unknown>;
  });

  const requestDurationMode = computed(() => formatTaskDurationMode(requestSnapshot.value));

  const requestTranscriptPreview = computed(() => previewTaskTranscript(requestSnapshot.value));

  const requestRows = computed(() => {
    if (!task.value) return [];
    return [
      { label: "文本模型", value: formatTaskModelValue(requestSnapshot.value.textAnalysisModel) },
      { label: "关键帧模型", value: formatTaskModelValue(requestSnapshot.value.imageModel) },
      { label: "视频模型", value: formatTaskModelValue(requestSnapshot.value.videoModel) },
      { label: "清晰度 / 画幅", value: formatTaskModelValue(requestSnapshot.value.videoSize) },
      { label: "输出数量", value: formatTaskOutputCount(requestSnapshot.value) },
      { label: "请求时长", value: formatTaskRequestedDuration(requestSnapshot.value) },
      { label: "生效时长", value: formatTaskResolvedDuration(task.value) },
      { label: "任务 Seed", value: taskSeedLabel.value },
      { label: "提前停止视频生成", value: formatTaskStopBeforeVideoGeneration(requestSnapshot.value) },
      { label: "文本输入", value: formatTaskTranscriptSummary(requestSnapshot.value) },
    ];
  });

  const compactRequestRows = computed(() => requestRows.value.slice(0, 6));

  const taskSeedLabel = computed(() => {
    const topLevelSeed = task.value?.taskSeed;
    if (typeof topLevelSeed === "number" && Number.isFinite(topLevelSeed)) {
      return String(Math.trunc(topLevelSeed));
    }
    return formatTaskSeed(requestSnapshot.value);
  });

  const monitoringStageLabel = computed(() => formatMonitoringValue(task.value?.monitoring?.currentStage));
  const monitoringWorkerLabel = computed(() => formatMonitoringValue(task.value?.monitoring?.activeWorkerInstanceId));
  const artifactDirectories = computed(() => task.value?.artifactDirectories ?? task.value?.monitoring?.artifactDirectories ?? null);
  const artifactDirectoryHint = computed(() => formatMonitoringValue(artifactDirectories.value?.baseRelativeDir));
  const durationDiagnostics = computed(() => task.value?.durationDiagnostics ?? []);

  const monitoringRows = computed(() => {
    const monitoring = task.value?.monitoring;
    if (!monitoring) return [];
    return [
      { label: "Attempt 状态", value: formatMonitoringValue(monitoring.activeAttemptStatus) },
      { label: "恢复阶段", value: formatMonitoringValue(monitoring.resumeFromStage) },
      { label: "恢复镜头", value: formatMonitoringValue(monitoring.resumeFromClipIndex) },
      { label: "计划镜头数", value: formatMonitoringValue(monitoring.plannedClipCount) },
      { label: "已生成镜头数", value: formatMonitoringValue(monitoring.renderedClipCount) },
      { label: "连续完成镜头", value: formatMonitoringValue(monitoring.contiguousRenderedClipCount) },
      { label: "最新片段", value: formatMonitoringValue(monitoring.latestRenderedClipIndex) },
      { label: "最新拼接", value: formatMonitoringValue(monitoring.latestJoinName) },
    ].filter((item) => item.value !== "暂无");
  });

  const artifactRows = computed(() => {
    const value = artifactDirectories.value;
    if (!value) return [];
    return [
      { label: "Storage 根目录", value: formatMonitoringValue(value.storageRoot) },
      { label: "任务基目录", value: formatMonitoringValue(value.baseAbsoluteDir || value.baseRelativeDir) },
      { label: "运行目录", value: formatMonitoringValue(value.runningAbsoluteDir || value.runningRelativeDir) },
      { label: "拼接目录", value: formatMonitoringValue(value.joinedAbsoluteDir || value.joinedRelativeDir) },
      { label: "脚本文件", value: formatMonitoringValue(value.storyboardFileName) },
      { label: "首帧命名", value: formatMonitoringValue(value.firstFramePattern) },
      { label: "尾帧命名", value: formatMonitoringValue(value.lastFramePattern) },
      { label: "片段命名", value: formatMonitoringValue(value.clipPattern) },
      { label: "拼接命名", value: formatMonitoringValue(value.joinPattern) },
    ].filter((item) => item.value !== "暂无");
  });

  const orderedTraceEvents = computed(() => [...traceEvents.value].reverse());
  const traceFocus = computed(() => orderedTraceEvents.value[0] ?? null);
  const tracePreview = computed(() => orderedTraceEvents.value.slice(0, 5));
  const diagnosisSeverityLabel = computed(() => diagnosisSeverityText(diagnosis.value?.severity || "info"));
  const diagnosisSeverityTag = computed(() => severityTag(diagnosis.value?.severity || "info"));
  const diagnosisRecoveryAction = computed(() => formatDiagnosisValue(diagnosis.value?.recovery?.recommendedAction));
  const diagnosisRecoveryStart = computed(() => {
    if (!diagnosis.value) return "暂无";
    return `${formatDiagnosisValue(diagnosis.value.recovery?.resumeFromStage)} / 镜头 ${formatDiagnosisValue(diagnosis.value.recovery?.resumeFromClipIndex)}`;
  });
  const diagnosisContinuitySummary = computed(() => {
    if (!diagnosis.value) return "暂无";
    return `计划 ${formatDiagnosisValue(diagnosis.value.continuity?.plannedClipCount)}，连续完成 ${formatDiagnosisValue(diagnosis.value.continuity?.contiguousRenderedClipCount)}，缺失 ${formatDiagnosisValue((diagnosis.value.continuity?.missingClipIndices as unknown[] | undefined)?.join(", "))}`;
  });
  const diagnosisQueueSummary = computed(() => {
    if (!diagnosis.value) return "暂无";
    return `排队 ${formatDiagnosisValue(diagnosis.value.queue?.isQueued)}，位置 ${formatDiagnosisValue(diagnosis.value.queue?.queuePosition)}，Attempt ${formatDiagnosisValue(diagnosis.value.queue?.activeAttemptStatus)}`;
  });

  function logLevelTag(level: string) {
    if (level === "ERROR") return "danger";
    if (level === "WARN") return "warning";
    return "info";
  }

  function severityTag(severity: string) {
    switch (severity) {
      case "high": return "danger";
      case "medium": return "warning";
      case "low": return "info";
      default: return "success";
    }
  }

  function formatTime(value: string) {
    return new Date(value).toLocaleString();
  }

  function formatMonitoringValue(value: unknown) {
    if (value == null) return "暂无";
    if (typeof value === "number") return value > 0 ? String(value) : "暂无";
    const text = String(value).trim();
    return text || "暂无";
  }

  function formatDiagnosisValue(value: unknown) {
    if (typeof value === "boolean") return value ? "是" : "否";
    return formatMonitoringValue(value);
  }

  function diagnosisSeverityText(severity: string) {
    switch (severity) {
      case "high": return "高风险";
      case "medium": return "中风险";
      case "low": return "低风险";
      default: return "正常";
    }
  }

  function findingSeverityTag(severity: string) {
    switch (severity) {
      case "high": return "danger";
      case "medium": return "warning";
      case "low": return "info";
      default: return "success";
    }
  }

  function formatSecondsValue(value: number | null | undefined) {
    if (typeof value !== "number" || !Number.isFinite(value) || value <= 0) return "暂无";
    return `${Number.isInteger(value) ? value : value.toFixed(1)}s`;
  }

  function formatSecondsRange(minValue: number | null | undefined, maxValue: number | null | undefined, targetValue?: number | null) {
    const min = typeof minValue === "number" && Number.isFinite(minValue) && minValue > 0 ? minValue : null;
    const max = typeof maxValue === "number" && Number.isFinite(maxValue) && maxValue > 0 ? maxValue : null;
    const target = typeof targetValue === "number" && Number.isFinite(targetValue) && targetValue > 0 ? targetValue : null;
    if (min == null && max == null) return "暂无";
    if (min != null && max != null && min === max) return formatSecondsValue(target ?? min);
    const range = `${formatSecondsValue(min)} - ${formatSecondsValue(max)}`;
    return target != null ? `${range} (目标 ${formatSecondsValue(target)})` : range;
  }

  function durationSourceLabel(item: TaskDurationDiagnosticClip) {
    switch (item.durationSource) {
      case "storyboard": return "分镜";
      case "task_average": return "任务均分";
      default: return "未知";
    }
  }

  function durationStatusLabel(status: TaskDurationDiagnosticClip["status"]) {
    switch (status) {
      case "rendered": return "已生成";
      case "pending": return "待生成";
      default: return "未知";
    }
  }

  function formatTaskModelValue(value: unknown) {
    if (!value || typeof value !== "string") return "未指定";
    return value;
  }

  function formatTaskDurationMode(snapshot: Record<string, unknown>) {
    const mode = snapshot.durationMode as string | undefined;
    return mode || "auto";
  }

  function formatTaskOutputCount(snapshot: Record<string, unknown>) {
    const count = snapshot.outputCount;
    if (count === "auto") return "自动";
    if (typeof count === "number" && count > 0) return String(count);
    return "默认";
  }

  function formatTaskRequestedDuration(snapshot: Record<string, unknown>) {
    const mode = snapshot.videoDurationSeconds;
    if (mode === "auto") return "自动";
    if (typeof mode === "number" && mode > 0) return `${mode}s`;
    return "未指定";
  }

  function formatTaskResolvedDuration(task: TaskDetail) {
    const min = task.minDurationSeconds;
    const max = task.maxDurationSeconds;
    if (min && max) return `${min}-${max}s`;
    if (min) return `${min}s`;
    if (max) return `${max}s`;
    return "未指定";
  }

  function formatTaskSeed(value: unknown) {
    if (typeof value === "number" && Number.isFinite(value)) return String(Math.trunc(value));
    return "未设置";
  }

  function formatTaskStopBeforeVideoGeneration(snapshot: Record<string, unknown>) {
    return snapshot.stopBeforeVideoGeneration ? "已启用" : "否";
  }

  function formatTaskTranscriptSummary(snapshot: Record<string, unknown>) {
    return snapshot.transcriptText ? "已提供" : "无文本输入";
  }

  function previewTaskTranscript(snapshot: Record<string, unknown>) {
    const text = snapshot.transcriptText as string | undefined;
    if (!text) return null;
    return text.length > 200 ? text.slice(0, 200) + "..." : text;
  }

  return {
    runningTask,
    planningSummary,
    requestDurationMode,
    requestTranscriptPreview,
    compactRequestRows,
    monitoringStageLabel,
    monitoringWorkerLabel,
    artifactDirectoryHint,
    durationDiagnostics,
    monitoringRows,
    artifactRows,
    orderedTraceEvents,
    traceFocus,
    tracePreview,
    diagnosisSeverityLabel,
    diagnosisSeverityTag,
    diagnosisRecoveryAction,
    diagnosisRecoveryStart,
    diagnosisContinuitySummary,
    diagnosisQueueSummary,
    logLevelTag,
    findingSeverityTag,
    diagnosisSeverityText,
    formatSecondsRange,
    formatSecondsValue,
    durationSourceLabel,
    durationStatusLabel,
    formatTime,
  };
}
