import type { CSSProperties } from "vue";
import type { MaterialAssetLibraryItem } from "@/types";
import { inferMediaDownloadKind, type DownloadMediaKind } from "@/utils/download";
import { renderMarkdownToHtml } from "@/utils/markdown";

export function normalizedAssetValue(value?: string | null) {
  return typeof value === "string" ? value.trim().toLowerCase() : "";
}

export function isWorkflowArtifactAsset(asset: MaterialAssetLibraryItem) {
  return (
    Boolean(normalizedAssetValue(asset.workflowId))
    || normalizedAssetValue(asset.assetType) === "workflow"
    || normalizedAssetValue(asset.assetRole) === "workflow"
  );
}

export function assetPublicUrl(asset: MaterialAssetLibraryItem) {
  return asset.publicUrl || asset.fileUrl || "";
}

export function assetDownloadKind(asset: MaterialAssetLibraryItem): DownloadMediaKind {
  if (asset.mediaType === "image" || asset.mediaType === "video") return asset.mediaType;
  return inferMediaDownloadKind(assetPublicUrl(asset));
}

export function assetOverlayMeta(asset: MaterialAssetLibraryItem) {
  const size = asset.width && asset.height ? `${asset.width} x ${asset.height}` : "未知分辨率";
  return `${size} · ${asset.remoteUrl ? "远端" : "本地"}`;
}

export function assetPreviewRatio(asset: MaterialAssetLibraryItem) {
  const width = Number(asset.width);
  const height = Number(asset.height);
  if (!Number.isFinite(width) || !Number.isFinite(height) || width <= 0 || height <= 0) return null;
  return width / height;
}

export function boundedAssetPreviewRatio(asset: MaterialAssetLibraryItem) {
  const ratio = assetPreviewRatio(asset);
  return ratio ? Math.min(Math.max(ratio, 0.5), 9 / 16) : 9 / 16;
}

export function assetPreviewStyle(asset: MaterialAssetLibraryItem): CSSProperties | undefined {
  if (!assetPreviewRatio(asset)) return undefined;
  return {
    "--material-preview-ratio": boundedAssetPreviewRatio(asset).toFixed(4),
  } as CSSProperties;
}

export function assetPreviewBackdropStyle(url?: string): CSSProperties | undefined {
  if (!url) return undefined;
  return {
    backgroundImage: `url("${url.replace(/["\\]/g, "\\$&")}")`,
  };
}

export function assetPreviewClass(asset: MaterialAssetLibraryItem) {
  const ratio = assetPreviewRatio(asset);
  if (!ratio) return "";
  if (ratio < 0.78) return "material-card__preview-portrait";
  if (ratio > 2.8) return "material-card__preview-panorama";
  return "";
}

export function storyboardText(asset: MaterialAssetLibraryItem) {
  const scriptMarkdown = typeof asset.metadata?.scriptMarkdown === "string" ? asset.metadata.scriptMarkdown : "";
  return scriptMarkdown || asset.title;
}

export function storyboardPreviewHtml(asset: MaterialAssetLibraryItem) {
  return renderMarkdownToHtml(storyboardText(asset));
}

export function assetListImageUrl(asset: MaterialAssetLibraryItem) {
  return asset.thumbnailUrl || "";
}

export function assetVideoPosterUrl(asset: MaterialAssetLibraryItem) {
  return asset.thumbnailUrl || undefined;
}

export function assetOriginalImageUrl(asset: MaterialAssetLibraryItem) {
  return assetPublicUrl(asset);
}

export function assetVideoPreviewUrl(asset: MaterialAssetLibraryItem) {
  return assetPublicUrl(asset);
}

export function isAssetShareable(asset: MaterialAssetLibraryItem) {
  return (asset.mediaType === "image" || asset.mediaType === "video") && Boolean(assetPublicUrl(asset));
}

export function materialShareSource(asset: MaterialAssetLibraryItem): {
  sourceType: "task" | "workflow" | "material";
  sourceId: string;
} {
  if (asset.workflowId) return { sourceType: "workflow", sourceId: asset.workflowId };
  if (asset.taskId) return { sourceType: "task", sourceId: asset.taskId };
  return { sourceType: "material", sourceId: asset.id };
}
