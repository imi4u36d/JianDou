import type { TaskDetail, TaskListItem, TaskMaterial, TaskOutput } from "@/types";

export type TaskPreviewMediaType = "image" | "video";

export interface TaskPreviewMedia {
  type: TaskPreviewMediaType;
  url: string;
  title: string;
  posterUrl?: string;
  materialAssetId?: string;
}

const IMAGE_RESULT_TYPES = new Set(["image", "image_generation", "image_to_image", "character_sheet", "workspace_image"]);
const PRIMARY_VIDEO_RESULT_TYPES = new Set(["video", "video_generation", "video_clip"]);
const JOIN_VIDEO_RESULT_TYPES = new Set(["video_join", "join_video", "joined_video"]);
const VIDEO_RESULT_TYPES = new Set([...PRIMARY_VIDEO_RESULT_TYPES, ...JOIN_VIDEO_RESULT_TYPES]);

const IMAGE_URL_PATTERN = /\.(avif|gif|jpe?g|png|svg|webp)(?:[?#].*)?$/i;
const VIDEO_URL_PATTERN = /\.(m4v|mov|mp4|ogg|webm)(?:[?#].*)?$/i;

function normalizedText(value: unknown): string {
  return String(value ?? "").trim();
}

export function firstNonBlankTaskValue(...values: unknown[]): string {
  for (const value of values) {
    const normalized = normalizedText(value);
    if (normalized) return normalized;
  }
  return "";
}

function normalizedType(value: unknown): string {
  return normalizedText(value).toLowerCase();
}

function normalizedTaskType(task?: Pick<TaskListItem, "taskType"> & { requestSnapshot?: { taskType?: string | null } } | null): string {
  return normalizedType(task?.requestSnapshot?.taskType || task?.taskType || "video_generation") || "video_generation";
}

function isTaskDetail(task?: TaskListItem | TaskDetail | null): task is TaskDetail {
  return Boolean(task && "outputs" in task);
}

function isPrimaryVideoResultType(value: unknown): boolean {
  return PRIMARY_VIDEO_RESULT_TYPES.has(normalizedType(value));
}

function isJoinVideoResultType(value: unknown): boolean {
  return JOIN_VIDEO_RESULT_TYPES.has(normalizedType(value));
}

function isVideoResultType(value: unknown): boolean {
  return VIDEO_RESULT_TYPES.has(normalizedType(value));
}

function isImageResultType(value: unknown): boolean {
  return IMAGE_RESULT_TYPES.has(normalizedType(value));
}

function inferMediaType(mediaType: unknown, mimeType: unknown, url: string): TaskPreviewMediaType | "" {
  const normalizedMediaType = normalizedType(mediaType);
  const normalizedMimeType = normalizedType(mimeType);
  if (normalizedMediaType.includes("video") || normalizedMimeType.startsWith("video/")) return "video";
  if (normalizedMediaType.includes("image") || normalizedMimeType.startsWith("image/")) return "image";
  if (VIDEO_URL_PATTERN.test(url)) return "video";
  if (IMAGE_URL_PATTERN.test(url)) return "image";
  return "";
}

function taskOutputMediaType(output: TaskOutput, url: string, fallbackType: TaskPreviewMediaType | "" = ""): TaskPreviewMediaType | "" {
  if (isVideoResultType(output.resultType)) return "video";
  if (isImageResultType(output.resultType)) return "image";
  return inferMediaType("", output.mimeType, url) || fallbackType;
}

function taskMaterialMediaType(material: TaskMaterial, url: string): TaskPreviewMediaType | "" {
  return inferMediaType(material.mediaType, material.mimeType, url);
}

export function taskOutputUrl(output: TaskOutput): string {
  return firstNonBlankTaskValue(
    output.previewUrl,
    output.previewPath,
    output.downloadUrl,
    output.downloadPath,
    output.remoteUrl,
  );
}

export function taskMaterialUrl(material: TaskMaterial): string {
  return firstNonBlankTaskValue(material.publicUrl, material.fileUrl);
}

function taskOutputDownloadUrl(output: TaskOutput): string {
  return firstNonBlankTaskValue(output.downloadUrl, output.downloadPath, output.previewUrl, output.previewPath, output.remoteUrl);
}

function outputPosterUrl(output: TaskOutput): string {
  const extra: Record<string, unknown> = output.extra && typeof output.extra === "object" ? output.extra : {};
  return firstNonBlankTaskValue(output.thumbnailUrl, extra.thumbnailUrl, extra.posterUrl);
}

function materialById(materials: TaskMaterial[] | undefined): Map<string, TaskMaterial> {
  return new Map((materials ?? [])
    .map((material) => [normalizedText(material.id), material] as const)
    .filter(([id]) => Boolean(id)));
}

function outputPreviewMedia(
  output: TaskOutput,
  materialsById?: Map<string, TaskMaterial>,
  fallbackType: TaskPreviewMediaType | "" = "",
): TaskPreviewMedia | null {
  const linkedMaterial = materialsById?.get(normalizedText(output.materialAssetId));
  const url = firstNonBlankTaskValue(taskOutputUrl(output), linkedMaterial ? taskMaterialUrl(linkedMaterial) : "");
  if (!url) return null;
  const type = taskOutputMediaType(output, url, fallbackType) || (linkedMaterial ? taskMaterialMediaType(linkedMaterial, url) : "");
  if (!type) return null;
  return {
    type,
    url: type === "video" ? taskOutputDownloadUrl(output) || (linkedMaterial ? taskMaterialUrl(linkedMaterial) : "") || url : url,
    posterUrl: type === "video" ? firstNonBlankTaskValue(outputPosterUrl(output), linkedMaterial?.thumbnailUrl) : undefined,
    title: output.title || "任务结果",
    materialAssetId: firstNonBlankTaskValue(output.materialAssetId, linkedMaterial?.id),
  };
}

function materialPreviewMedia(material: TaskMaterial): TaskPreviewMedia | null {
  const url = taskMaterialUrl(material);
  if (!url) return null;
  const type = taskMaterialMediaType(material, url);
  if (!type) return null;
  return {
    type,
    url,
    posterUrl: type === "video" ? firstNonBlankTaskValue(material.thumbnailUrl) : undefined,
    title: material.title || material.id || "任务素材",
    materialAssetId: material.id,
  };
}

function outputClipIndex(output: TaskOutput): number {
  const value = Number(output.clipIndex);
  return Number.isFinite(value) ? value : 0;
}

function firstOutput(outputs: TaskOutput[], predicate: (output: TaskOutput) => boolean): TaskOutput | null {
  return outputs.find(predicate) ?? null;
}

function latestOutput(outputs: TaskOutput[], predicate: (output: TaskOutput) => boolean): TaskOutput | null {
  return outputs
    .filter(predicate)
    .sort((left, right) => outputClipIndex(right) - outputClipIndex(left))[0] ?? null;
}

function firstPreviewFromOutputs(
  outputs: TaskOutput[],
  preferredType: TaskPreviewMediaType,
  materialsById?: Map<string, TaskMaterial>,
): TaskPreviewMedia | null {
  const previews = outputs
    .map((output) => outputPreviewMedia(output, materialsById))
    .filter((preview): preview is TaskPreviewMedia => Boolean(preview));
  return previews.find((preview) => preview.type === preferredType) ?? previews[0] ?? null;
}

function firstPreviewFromMaterials(materials: TaskMaterial[] | undefined, preferredType: TaskPreviewMediaType): TaskPreviewMedia | null {
  const outputMaterials = (materials ?? []).filter((material) => normalizedType(material.kind) !== "source");
  const preferred = outputMaterials
    .map(materialPreviewMedia)
    .find((preview): preview is TaskPreviewMedia => Boolean(preview && preview.type === preferredType));
  if (preferred) return preferred;
  return outputMaterials
    .map(materialPreviewMedia)
    .find((preview): preview is TaskPreviewMedia => Boolean(preview)) ?? null;
}

function monitoringPreviewMedia(detail: TaskDetail): TaskPreviewMedia | null {
  const taskType = normalizedTaskType(detail);
  const monitoringImageUrls = Array.isArray(detail.monitoring?.latestImageOutputUrls) ? detail.monitoring.latestImageOutputUrls : [];
  const contextImageUrls = Array.isArray(detail.executionContext?.latestImageOutputUrls) ? detail.executionContext.latestImageOutputUrls : [];
  const latestImageUrl = firstNonBlankTaskValue(
    detail.monitoring?.latestImageOutputUrl,
    detail.executionContext?.latestImageOutputUrl,
    monitoringImageUrls[monitoringImageUrls.length - 1],
    contextImageUrls[contextImageUrls.length - 1],
  );
  if (taskType !== "video_generation" && latestImageUrl) {
    return {
      type: "image",
      url: latestImageUrl,
      title: "最新图片结果",
    };
  }
  const joinUrl = firstNonBlankTaskValue(detail.monitoring?.latestJoinOutputUrl);
  if (joinUrl) {
    return {
      type: "video",
      url: joinUrl,
      title: detail.monitoring?.latestJoinName || "最新拼接结果",
    };
  }
  const videoUrl = firstNonBlankTaskValue(detail.monitoring?.latestVideoOutputUrl);
  if (videoUrl) {
    return {
      type: "video",
      url: videoUrl,
      title: "最新视频结果",
    };
  }
  return null;
}

function detailOutputPreviewMedia(detail: TaskDetail): TaskPreviewMedia | null {
  const outputs = Array.isArray(detail.outputs) ? detail.outputs : [];
  const linkedMaterials = materialById(detail.materials);
  const taskType = normalizedTaskType(detail);
  const preferredType: TaskPreviewMediaType = taskType === "video_generation" ? "video" : "image";
  const joinedVideoOutput = latestOutput(outputs, (output) => isJoinVideoResultType(output.resultType));
  const primaryVideoOutput = latestOutput(outputs, (output) => isPrimaryVideoResultType(output.resultType));
  const imageOutput = firstOutput(outputs, (output) => isImageResultType(output.resultType));

  const outputCandidates = taskType === "video_generation"
    ? [joinedVideoOutput, primaryVideoOutput, imageOutput]
    : [imageOutput, primaryVideoOutput, joinedVideoOutput];

  for (const output of outputCandidates) {
    const preview = output ? outputPreviewMedia(output, linkedMaterials, taskType === "video_generation" ? "" : "image") : null;
    if (preview) return preview;
  }

  return firstPreviewFromOutputs(outputs, preferredType, linkedMaterials)
    ?? (taskType !== "video_generation" && outputs.length ? outputPreviewMedia(outputs[0], linkedMaterials, "image") : null);
}

export function resolveTaskPreviewMedia(task?: TaskListItem | TaskDetail | null): TaskPreviewMedia | null {
  if (!task) return null;
  if (isTaskDetail(task)) {
    const taskType = normalizedTaskType(task);
    const outputPreview = detailOutputPreviewMedia(task);
    if (outputPreview?.type === "video" || (outputPreview && taskType !== "video_generation")) return outputPreview;

    const monitoringPreview = monitoringPreviewMedia(task);
    if (monitoringPreview) return monitoringPreview;
    if (outputPreview) return outputPreview;

    const preferredMaterialType: TaskPreviewMediaType = taskType === "video_generation" ? "video" : "image";
    const materialPreview = firstPreviewFromMaterials(task.materials, preferredMaterialType);
    if (materialPreview) return materialPreview;
  }

  const thumbnailUrl = firstNonBlankTaskValue(task.thumbnailUrl);
  return thumbnailUrl ? { type: "image", url: thumbnailUrl, title: task.title || "任务预览" } : null;
}

export function resolveTaskThumbnailUrl(task?: TaskListItem | TaskDetail | null): string {
  const preview = resolveTaskPreviewMedia(task);
  return firstNonBlankTaskValue(preview?.posterUrl, preview?.type === "image" ? preview.url : "", task?.thumbnailUrl);
}
