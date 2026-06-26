import type { PublicShareItem } from "@/types";

export function publicShareAspectRatio(item: Pick<PublicShareItem, "width" | "height" | "mediaType">): number {
  const width = Number(item.width ?? 0);
  const height = Number(item.height ?? 0);
  if (Number.isFinite(width) && Number.isFinite(height) && width > 0 && height > 0) {
    return Math.max(0.5, Math.min(2.2, width / height));
  }
  return item.mediaType === "video" ? 16 / 9 : 1;
}

export function publicShareCardStyle(item: Pick<PublicShareItem, "width" | "height" | "mediaType">) {
  return {
    aspectRatio: publicShareAspectRatio(item).toFixed(4),
  };
}

export function publicSharePreviewUrl(item: Pick<PublicShareItem, "previewUrl" | "thumbnailUrl">): string {
  return item.thumbnailUrl || item.previewUrl || "";
}
