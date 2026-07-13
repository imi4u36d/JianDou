import {
  summaryFrameFailures,
  summaryNumberValue,
  summaryUrlValue,
} from "@/features/workflows/summary";
import { renderMarkdownToHtml } from "@/utils/markdown";
import type { StageVersion, WorkflowClipSlot, WorkflowDetail } from "@/types";

export interface WorkflowHeaderTag {
  label: string;
  value: string;
}

export function workflowStatusLabel(status?: string | null): string {
  switch (String(status || "").trim().toUpperCase()) {
    case "DRAFT": return "草稿";
    case "READY": return "可生成";
    case "RUNNING": return "执行中";
    case "PAUSED": return "已暂停";
    case "COMPLETED": return "已完成";
    case "FAILED": return "失败";
    default: return status || "等待更新";
  }
}

export function workflowProgressPercent(
  workflow: WorkflowDetail | null,
  stages: Array<{ ready: boolean }>,
): number {
  if (!workflow) return 0;
  if (workflow.finalResult || String(workflow.status || "").toUpperCase() === "COMPLETED") return 100;
  if (!stages.length) return 0;
  return Math.max(0, Math.min(100, Math.round((stages.filter((stage) => stage.ready).length / stages.length) * 100)));
}

export function workflowHeaderTags(
  workflow: WorkflowDetail | null,
  progressPercent: number,
): WorkflowHeaderTag[] {
  if (!workflow) return [];
  return [
    { label: "类型", value: "视频生成" },
    { label: "状态", value: workflowStatusLabel(workflow.status) },
    { label: "画幅", value: workflow.aspectRatio || "未设置" },
    { label: "进度", value: `${progressPercent}%` },
  ];
}

export interface WorkflowPreviewFrame {
  role: string;
  label: string;
  url: string;
  selected?: boolean;
  regenerable?: boolean;
  errorMessage?: string;
}

export function compactModelLabel(value: string): string {
  return value.replace(/\s*\([^)]*\)\s*/g, " ").replace(/\bDoubao\s+/i, "").replace(/\s+/g, " ").trim();
}

export function compactVideoSizeLabel(sizeLabel: string, aspectRatio?: string | null): string {
  const size = (sizeLabel || "未设置").trim();
  const ratio = (aspectRatio || "").trim();
  return !ratio || size.includes(ratio) ? size : `${size} · ${ratio}`;
}

export function normalizedStageVersionStatus(version: StageVersion): string {
  return (version.status || "").trim().toUpperCase();
}

export function stageStatusLabel(status?: string | null): string {
  switch ((status || "").trim().toUpperCase()) {
    case "SUCCEEDED": case "COMPLETED": return "可用";
    case "RUNNING": case "PROCESSING": return "生成中";
    case "FAILED": return "失败";
    case "PENDING": return "等待";
    default: return "未完成";
  }
}

export function stageVersionDisplayTitle(version: StageVersion): string {
  const rawTitle = (version.title || "").trim();
  const deduped = rawTitle.replace(new RegExp(`^V${version.versionNo}[.、\\-_:：·\\s]*`, "i"), "").trim();
  return deduped || rawTitle || "未命名版本";
}

export function videoVersionErrorMessage(version: StageVersion): string {
  const message = version.outputSummary?.error || version.outputSummary?.taskMessage || "";
  return typeof message === "string" ? message.trim() : "";
}

export function compactVideoVersionError(version: StageVersion): string {
  const message = videoVersionErrorMessage(version);
  if (!message) return "";
  if (/inference limit|set inference limit/i.test(message)) return "模型额度已达上限";
  if (/safe experience mode|model service has been paused/i.test(message)) return "模型服务暂停";
  if (/timeout|timed out/i.test(message)) return "生成超时";
  if (/rate limit|too many requests/i.test(message)) return "请求过于频繁";
  return message.length > 42 ? `${message.slice(0, 42)}...` : message;
}

export function canSelectVideoVersion(version: StageVersion): boolean {
  return normalizedStageVersionStatus(version) === "COMPLETED" && Boolean(
    version.downloadUrl || version.outputSummary?.fileUrl || version.asset?.publicUrl || version.asset?.fileUrl
  );
}

export function videoVersionStatusLabel(version: StageVersion): string {
  if (videoVersionErrorMessage(version)) return "生成失败";
  const taskStatus = typeof version.outputSummary?.taskStatus === "string" ? version.outputSummary.taskStatus.trim() : "";
  const status = normalizedStageVersionStatus(version);
  if (canSelectVideoVersion(version)) return version.selected ? "当前" : "可选";
  if (status === "FAILED" || taskStatus.toUpperCase() === "FAILED") return "生成失败";
  if (status === "RUNNING" || taskStatus) return taskStatus ? `生成中：${taskStatus}` : "生成中";
  return "未完成";
}

export function videoSlotStatusLabel(slot: WorkflowClipSlot): string {
  if (slot.videoVersions.some((version) => version.selected)) return "当前";
  if (slot.videoVersions.some(canSelectVideoVersion)) return "待选择";
  if (slot.videoVersions.some((version) => normalizedStageVersionStatus(version) === "FAILED" || videoVersionErrorMessage(version))) return "生成失败";
  return slot.videoVersions.length ? "生成中" : "未生成";
}

export function storyboardPreviewHtml(version: StageVersion): string {
  const output = version.outputSummary ?? {};
  const markdown = (typeof output.scriptMarkdown === "string" ? output.scriptMarkdown : "")
    || (typeof output.previewText === "string" ? output.previewText : "")
    || "暂无分镜预览";
  return renderMarkdownToHtml(markdown);
}

export function isLandscapeKeyframeVersion(version: StageVersion, aspectRatio?: string | null): boolean {
  const output = version.outputSummary ?? {};
  const width = summaryNumberValue(output, "width") || Number(version.asset?.width ?? 0);
  const height = summaryNumberValue(output, "height") || Number(version.asset?.height ?? 0);
  return Number.isFinite(width) && Number.isFinite(height) && width > 0 && height > 0
    ? width > height
    : (aspectRatio || "").trim().startsWith("16:");
}

export function keyframePreviewFrames(version: StageVersion, slot?: WorkflowClipSlot): WorkflowPreviewFrame[] {
  const output = version.outputSummary ?? {};
  const firstUrl = summaryUrlValue(output, "startFrameUrl", "firstFrameUrl");
  const failures = summaryFrameFailures(output);
  const firstFailure = failures.find((item) => item.role === "first");
  const lastFailure = failures.find((item) => item.role === "last");
  const lastUrl = summaryUrlValue(output, "endFrameUrl", "lastFrameUrl")
    || (!lastFailure ? summaryUrlValue(output, "fileUrl") || (typeof version.previewUrl === "string" ? version.previewUrl : "") : "");
  const explicitFirst = slot?.keyframeVersions.some((item) => Boolean(item.outputSummary?.selectedFirstFrame)) ?? false;
  const explicitLast = slot?.keyframeVersions.some((item) => Boolean(item.outputSummary?.selectedLastFrame)) ?? false;
  const frames: WorkflowPreviewFrame[] = [];
  if (firstUrl) frames.push({ role: "first", label: "首帧", url: firstUrl, selected: Boolean(output.selectedFirstFrame || (!explicitFirst && version.selected)), regenerable: version.clipIndex <= 1 });
  if (!firstUrl && firstFailure) frames.push({ role: "first", label: "首帧", url: "", selected: false, regenerable: version.clipIndex <= 1, errorMessage: firstFailure.message });
  if (lastUrl && (!firstUrl || lastUrl !== firstUrl || version.clipIndex === 1)) frames.push({ role: "last", label: "尾帧", url: lastUrl, selected: Boolean(output.selectedLastFrame || (!explicitLast && version.selected)), regenerable: true });
  if (!lastUrl && lastFailure) frames.push({ role: "last", label: "尾帧", url: "", selected: false, regenerable: true, errorMessage: lastFailure.message });
  return frames;
}

export function versionSeed(version: StageVersion): number | null {
  const seed = version.inputSummary?.seed;
  if (seed === undefined || seed === null || seed === "") return null;
  const value = Number(seed);
  return Number.isFinite(value) ? value : null;
}

export function durationLabel(value?: number | null): string {
  return typeof value === "number" && Number.isFinite(value) && value > 0 ? `${value.toFixed(1)}s` : "-";
}

export function clipSceneSummary(slot: WorkflowClipSlot): string {
  const text = slot.scene?.trim() || "暂无场景描述";
  return text.length > 120 ? `${text.slice(0, 120)}...` : text;
}

export function formatDateTime(value?: string | null): string {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("zh-CN", { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" }).format(date);
}
