import type { WorkflowCharacterSheet, WorkflowDetail, StageVersion } from "@/types";

interface PreviewFrame {
  role: string;
  label: string;
  url: string;
  selected?: boolean;
  regenerable?: boolean;
  errorMessage?: string;
}

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

export function characterSheetTitle(sheet: WorkflowCharacterSheet): string {
  return sheet.characterName?.trim()
    || sheet.displayName?.trim()
    || sheet.name?.trim()
    || `角色 #${characterSheetClipIndex(sheet) ?? "-"}`;
}

export function characterSheetAppearanceSummary(sheet: WorkflowCharacterSheet): string {
  return sheet.appearanceSummary?.trim()
    || sheet.appearance?.trim()
    || "暂无角色外观摘要";
}

export function characterSheetVersions(sheet: WorkflowCharacterSheet): StageVersion[] {
  return sheet.versions?.length ? sheet.versions : (sheet.keyframeVersions ?? []);
}

export function selectedCharacterSheetVersion(sheet: WorkflowCharacterSheet): StageVersion | null {
  return characterSheetVersions(sheet).find((version) => version.selected) ?? null;
}

export function hasMissingCharacterSheets(workflow: WorkflowDetail): boolean {
  const sheets = workflow.characterSheets ?? [];
  return sheets.some((sheet) => !selectedCharacterSheetVersion(sheet));
}

export function characterSheetPreviewFrames(version: StageVersion): PreviewFrame[] {
  const outputSummary = version.outputSummary ?? {};
  const summaryUrlValue = (obj: Record<string, unknown>, ...keys: string[]): string => {
    for (const key of keys) {
      const val = obj[key];
      if (typeof val === "string" && val.trim()) return val.trim();
    }
    return "";
  };
  const summaryUrlListValue = (obj: Record<string, unknown>, ...keys: string[]): string[] => {
    for (const key of keys) {
      const val = obj[key];
      if (Array.isArray(val)) return val.filter((item): item is string => typeof item === "string" && item.trim());
    }
    return [];
  };
  const frames: PreviewFrame[] = [];
  const namedFrames = [
    { role: "front", label: "正面", url: summaryUrlValue(outputSummary, "frontViewUrl", "frontImageUrl", "frontUrl") },
    { role: "side", label: "侧面", url: summaryUrlValue(outputSummary, "sideViewUrl", "sideImageUrl", "sideUrl", "profileViewUrl") },
    { role: "back", label: "背面", url: summaryUrlValue(outputSummary, "backViewUrl", "backImageUrl", "backUrl") },
  ].filter((frame) => frame.url);
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
      label: "三视图",
      url: previewUrl,
    });
  }
  return frames;
}
