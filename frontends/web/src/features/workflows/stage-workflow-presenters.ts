import type { StageVersion, WorkflowClipSlot, WorkflowSummary } from "@/types";
import {
  summaryFrameFailures,
  summaryNumberValue,
  summaryUrlValue,
} from "@/features/workflows/summary";
import { renderMarkdownToHtml } from "@/utils/markdown";

export interface WorkflowPreviewFrame {
  role: string;
  label: string;
  url: string;
  selected?: boolean;
  regenerable?: boolean;
  errorMessage?: string;
}

export function stageVersionDisplayTitle(version: StageVersion) {
  const rawTitle = (version.title || "").trim();
  const versionPrefixPattern = new RegExp(`^V${version.versionNo}[.、\\-_:：·\\s]*`, "i");
  const dedupedTitle = rawTitle.replace(versionPrefixPattern, "").trim();
  return dedupedTitle || rawTitle || "未命名版本";
}

export function compactModelLabel(value: string) {
  return value
    .replace(/\s*\([^)]*\)\s*/g, " ")
    .replace(/\bDoubao\s+/i, "")
    .replace(/\s+/g, " ")
    .trim();
}

export function compactVideoSizeLabel(sizeLabel: string, aspectRatio?: string | null) {
  const size = (sizeLabel || "未设置").trim();
  const ratio = (aspectRatio || "").trim();
  return !ratio || size.includes(ratio) ? size : `${size} · ${ratio}`;
}

export function formatWorkflowStatus(status?: string | null) {
  switch ((status || "").trim().toUpperCase()) {
    case "DRAFT":
      return "草稿";
    case "READY":
      return "可生成";
    case "RUNNING":
      return "执行中";
    case "PAUSED":
      return "已暂停";
    case "COMPLETED":
      return "已完成";
    case "FAILED":
      return "失败";
    default:
      return status || "等待更新";
  }
}

export function workflowNavStatusLabel(workflow: WorkflowSummary) {
  switch ((workflow.autoPilotState || "").trim().toUpperCase()) {
    case "QUEUED":
      return "排队中";
    case "RUNNING":
      return "自动执行";
    case "PAUSED":
      return "已暂停";
    case "FAILED":
      return "失败";
    case "COMPLETED":
      return "已完成";
    default:
      return formatWorkflowStatus(workflow.status);
  }
}

export function workflowNavStatusTone(workflow: WorkflowSummary) {
  const autoPilotState = (workflow.autoPilotState || "").trim().toUpperCase();
  const status = (autoPilotState || workflow.status || "").trim().toUpperCase();
  if (["READY", "RUNNING", "DRAFT", "QUEUED"].includes(status)) return "active";
  if (status === "COMPLETED") return "done";
  if (status === "FAILED") return "failed";
  if (status === "PAUSED") return "paused";
  return "idle";
}

export function workflowNavUpdatedLabel(value?: string | null, now = Date.now()) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  const diffMin = Math.floor((now - date.getTime()) / 60000);
  if (diffMin < 1) return "刚刚";
  if (diffMin < 60) return `${diffMin}分钟前`;
  const diffHour = Math.floor(diffMin / 60);
  if (diffHour < 24) return `${diffHour}小时前`;
  const diffDay = Math.floor(diffHour / 24);
  if (diffDay < 7) return `${diffDay}天前`;
  return new Intl.DateTimeFormat("zh-CN", { month: "2-digit", day: "2-digit" }).format(date);
}

export function normalizedStageVersionStatus(version: StageVersion) {
  return (version.status || "").trim().toUpperCase();
}

export function stageStatusLabel(status?: string | null) {
  switch ((status || "").trim().toUpperCase()) {
    case "SUCCEEDED":
    case "COMPLETED":
      return "可用";
    case "RUNNING":
    case "PROCESSING":
      return "生成中";
    case "FAILED":
      return "失败";
    case "PENDING":
      return "等待";
    default:
      return "未完成";
  }
}

export function videoVersionErrorMessage(version: StageVersion) {
  const outputSummary = version.outputSummary ?? {};
  const message = outputSummary.error || outputSummary.taskMessage || "";
  return typeof message === "string" ? message.trim() : "";
}

export function compactVideoVersionError(version: StageVersion) {
  const message = videoVersionErrorMessage(version);
  if (!message) return "";
  if (/inference limit|set inference limit/i.test(message)) return "模型额度已达上限";
  if (/safe experience mode|model service has been paused/i.test(message)) return "模型服务暂停";
  if (/timeout|timed out/i.test(message)) return "生成超时";
  if (/rate limit|too many requests/i.test(message)) return "请求过于频繁";
  return message.length > 42 ? `${message.slice(0, 42)}...` : message;
}

export function canSelectVideoVersion(version: StageVersion) {
  const status = normalizedStageVersionStatus(version);
  return status === "COMPLETED" && Boolean(
    version.downloadUrl
    || version.outputSummary?.fileUrl
    || version.asset?.publicUrl
    || version.asset?.fileUrl,
  );
}

export function videoVersionStatusLabel(version: StageVersion) {
  if (videoVersionErrorMessage(version)) return "生成失败";
  const taskStatus = typeof version.outputSummary?.taskStatus === "string"
    ? version.outputSummary.taskStatus.trim()
    : "";
  const status = normalizedStageVersionStatus(version);
  if (canSelectVideoVersion(version)) return version.selected ? "当前" : "可选";
  if (status === "FAILED" || taskStatus.toUpperCase() === "FAILED") return "生成失败";
  if (status === "RUNNING" || taskStatus) return taskStatus ? `生成中：${taskStatus}` : "生成中";
  return "未完成";
}

export function videoSlotStatusLabel(slot: WorkflowClipSlot) {
  if (slot.videoVersions.some((version) => version.selected)) return "当前";
  if (slot.videoVersions.some(canSelectVideoVersion)) return "待选择";
  if (slot.videoVersions.some(
    (version) => normalizedStageVersionStatus(version) === "FAILED" || videoVersionErrorMessage(version),
  )) return "生成失败";
  return slot.videoVersions.length ? "生成中" : "未生成";
}

export function parseStoryboardDurationSeconds(value?: string | null) {
  if (value === undefined || value === null) return null;
  const raw = String(value).trim();
  if (!raw) return null;
  const numericValue = Number(raw);
  return Number.isFinite(numericValue) && Number.isInteger(numericValue) ? Math.trunc(numericValue) : null;
}

export function versionSeed(version: StageVersion) {
  const seed = (version.inputSummary ?? {}).seed;
  if (seed === undefined || seed === null || seed === "") return null;
  const numericValue = Number(seed);
  return Number.isFinite(numericValue) ? numericValue : null;
}

export function durationLabel(value?: number | null) {
  return typeof value === "number" && Number.isFinite(value) && value > 0 ? `${value.toFixed(1)}s` : "-";
}

export function clipSceneText(slot: WorkflowClipSlot) {
  return slot.scene?.trim() || "暂无场景描述";
}

export function clipSceneSummary(slot: WorkflowClipSlot) {
  const text = clipSceneText(slot);
  return text.length > 120 ? `${text.slice(0, 120)}...` : text;
}

export function formatDateTime(value?: string | null) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

export function storyboardPreview(version: StageVersion) {
  const outputSummary = version.outputSummary ?? {};
  const scriptMarkdown = typeof outputSummary.scriptMarkdown === "string" ? outputSummary.scriptMarkdown : "";
  const previewText = typeof outputSummary.previewText === "string" ? outputSummary.previewText : "";
  return scriptMarkdown || previewText || "暂无分镜预览";
}

export function storyboardPreviewHtml(version: StageVersion) {
  return renderMarkdownToHtml(storyboardPreview(version));
}

export function isLandscapeKeyframeVersion(version: StageVersion, aspectRatio = "") {
  const outputSummary = version.outputSummary ?? {};
  const width = summaryNumberValue(outputSummary, "width") || Number(version.asset?.width ?? 0);
  const height = summaryNumberValue(outputSummary, "height") || Number(version.asset?.height ?? 0);
  if (Number.isFinite(width) && Number.isFinite(height) && width > 0 && height > 0) return width > height;
  return aspectRatio.trim().startsWith("16:");
}

export function keyframePreviewFrames(
  version: StageVersion,
  slot?: WorkflowClipSlot,
): WorkflowPreviewFrame[] {
  const outputSummary = version.outputSummary ?? {};
  const firstFrameUrl = summaryUrlValue(outputSummary, "startFrameUrl", "firstFrameUrl");
  const frameFailures = summaryFrameFailures(outputSummary);
  const lastFailure = frameFailures.find((item) => item.role === "last");
  const lastFrameUrl = summaryUrlValue(outputSummary, "endFrameUrl", "lastFrameUrl")
    || (!lastFailure
      ? summaryUrlValue(outputSummary, "fileUrl") || (typeof version.previewUrl === "string" ? version.previewUrl : "")
      : "");
  const hasExplicitFirstSelection = slot
    ? slot.keyframeVersions.some((item) => Boolean(item.outputSummary?.selectedFirstFrame))
    : false;
  const hasExplicitLastSelection = slot
    ? slot.keyframeVersions.some((item) => Boolean(item.outputSummary?.selectedLastFrame))
    : false;
  const frames: WorkflowPreviewFrame[] = [];
  if (firstFrameUrl) {
    frames.push({
      role: "first",
      label: "首帧",
      url: firstFrameUrl,
      selected: Boolean(outputSummary.selectedFirstFrame || (!hasExplicitFirstSelection && version.selected)),
      regenerable: version.clipIndex <= 1,
    });
  }
  const firstFailure = frameFailures.find((item) => item.role === "first");
  if (!firstFrameUrl && firstFailure) {
    frames.push({
      role: "first",
      label: "首帧",
      url: "",
      selected: false,
      regenerable: version.clipIndex <= 1,
      errorMessage: firstFailure.message,
    });
  }
  if (lastFrameUrl && (!firstFrameUrl || lastFrameUrl !== firstFrameUrl || version.clipIndex === 1)) {
    frames.push({
      role: "last",
      label: "尾帧",
      url: lastFrameUrl,
      selected: Boolean(outputSummary.selectedLastFrame || (!hasExplicitLastSelection && version.selected)),
      regenerable: true,
    });
  }
  if (!lastFrameUrl && lastFailure) {
    frames.push({
      role: "last",
      label: "尾帧",
      url: "",
      selected: false,
      regenerable: true,
      errorMessage: lastFailure.message,
    });
  }
  return frames;
}

export function keyframeVersionHasSelectedFrame(version: StageVersion) {
  const outputSummary = version.outputSummary ?? {};
  return Boolean(version.selected || outputSummary.selectedFirstFrame || outputSummary.selectedLastFrame);
}
