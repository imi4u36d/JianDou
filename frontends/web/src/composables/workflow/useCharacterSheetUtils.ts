import type { WorkflowCharacterSheet, WorkflowDetail, StageVersion, WorkflowStageOutputSummary, WorkflowVisualAsset } from "@/types";

interface PreviewFrame {
  role: string;
  label: string;
  url: string;
  selected?: boolean;
  regenerable?: boolean;
  errorMessage?: string;
}

const CHARACTER_SHEET_CLIP_INDEX_BASE = 1000;

export function characterSheetKey(sheet: WorkflowCharacterSheet): string {
  return sheet.id || `${characterSheetTitle(sheet)}-${characterSheetClipIndex(sheet) ?? "na"}`;
}

export function characterSheetClipIndex(sheet: WorkflowCharacterSheet): number | null {
  const candidates = [sheet.syntheticClipIndex, sheet.clipIndex];
  for (const candidate of candidates) {
    const numericValue = Number(candidate);
    if (Number.isInteger(numericValue) && numericValue > 0) {
      return numericValue;
    }
  }
  return null;
}

export function characterSheetIndex(sheet: WorkflowCharacterSheet): number | null {
  const assetIndex = Number(sheet.assetIndex);
  if (Number.isInteger(assetIndex) && assetIndex > 0) {
    return assetIndex;
  }
  const directIndex = Number(sheet.characterIndex);
  if (Number.isInteger(directIndex) && directIndex > 0) {
    return directIndex;
  }
  const clipIndex = characterSheetClipIndex(sheet);
  if (clipIndex !== null && clipIndex > CHARACTER_SHEET_CLIP_INDEX_BASE) {
    return clipIndex - CHARACTER_SHEET_CLIP_INDEX_BASE;
  }
  return null;
}

export function characterSheetTitle(sheet: WorkflowCharacterSheet): string {
  return sheet.characterName?.trim()
    || sheet.displayName?.trim()
    || sheet.name?.trim()
    || `素材 #${characterSheetClipIndex(sheet) ?? "-"}`;
}

export function characterSheetAppearanceSummary(sheet: WorkflowCharacterSheet): string {
  return sheet.appearanceSummary?.trim()
    || sheet.appearance?.trim()
    || sheet.summary?.trim()
    || sheet.description?.trim()
    || "暂无素材视觉描述";
}

export const visualAssetTypeLabels: Record<string, string> = {
  character: "角色",
  prop: "道具",
  building: "建筑",
  scene: "场景",
  vehicle: "载具",
  other: "其他",
};

export function visualAssetTypeLabel(asset: WorkflowVisualAsset): string {
  return visualAssetTypeLabels[asset.assetType?.trim() || "other"] || "其他";
}

export function characterSheetVersions(sheet: WorkflowCharacterSheet): StageVersion[] {
  return sheet.versions?.length ? sheet.versions : (sheet.keyframeVersions ?? []);
}

export function selectedCharacterSheetVersion(sheet: WorkflowCharacterSheet): StageVersion | null {
  return characterSheetVersions(sheet).find((version) => version.selected) ?? null;
}

export function hasMissingCharacterSheets(workflow: WorkflowDetail): boolean {
  const sheets = workflow.visualAssets ?? workflow.characterSheets ?? [];
  return sheets.some((sheet) => !selectedCharacterSheetVersion(sheet));
}

export function characterSheetPreviewFrames(version: StageVersion): PreviewFrame[] {
  const outputSummary = version.outputSummary ?? {};
  const summaryUrlValue = (obj: WorkflowStageOutputSummary, ...keys: Array<keyof WorkflowStageOutputSummary>): string => {
    for (const key of keys) {
      const val = obj[key];
      if (typeof val === "string" && val.trim()) return val.trim();
    }
    return "";
  };
  const summaryUrlListValue = (obj: WorkflowStageOutputSummary, ...keys: Array<keyof WorkflowStageOutputSummary>): string[] => {
    for (const key of keys) {
      const val = obj[key];
      if (Array.isArray(val)) return val.filter((item): item is string => typeof item === "string" && item.trim().length > 0);
    }
    return [];
  };
  const frames: PreviewFrame[] = [];
  const namedFrames = [
    { role: "front", label: "正面", url: summaryUrlValue(outputSummary, "frontViewUrl", "frontImageUrl", "frontUrl") },
    { role: "side", label: "侧面", url: summaryUrlValue(outputSummary, "sideViewUrl", "sideImageUrl", "sideUrl", "profileViewUrl") },
    { role: "back", label: "背面", url: summaryUrlValue(outputSummary, "backViewUrl", "backImageUrl", "backUrl") },
  ].filter((frame): frame is { role: string; label: string; url: string } => Boolean(frame.url));
  if (namedFrames.length) {
    return namedFrames;
  }
  const listFrames = summaryUrlListValue(outputSummary, "threeViewUrls", "viewUrls", "sheetUrls", "images");
  if (listFrames.length) {
    const labels = ["正面", "侧面", "背面"];
    return listFrames.map((url, index) => ({
      role: `view-${index + 1}`,
      label: labels[index] || `视图 ${index + 1}`,
      url,
    }));
  }
  const previewUrl = summaryUrlValue(outputSummary, "sheetUrl", "previewUrl", "fileUrl")
    || (typeof version.previewUrl === "string" ? version.previewUrl : "");
  if (previewUrl) {
    frames.push({
      role: "sheet",
      label: version.inputSummary?.assetType && version.inputSummary.assetType !== "character" ? "设定图" : "三视图",
      url: previewUrl,
    });
  }
  return frames;
}
