import { describe, expect, it } from "vitest";
import type { MaterialAssetLibraryItem } from "@/types";
import {
  assetPreviewClass,
  assetPreviewStyle,
  isWorkflowArtifactAsset,
  materialShareSource,
  storyboardPreviewHtml,
} from "@/features/materials/material-library-presenters";

function asset(overrides: Partial<MaterialAssetLibraryItem> = {}) {
  return {
    id: "asset-1",
    stageType: "keyframe",
    clipIndex: 1,
    versionNo: 1,
    selectedForNext: false,
    mediaType: "image",
    title: "Asset",
    publicUrl: "https://cdn.example/asset.png",
    fileUrl: "",
    previewUrl: "",
    ...overrides,
  } as MaterialAssetLibraryItem;
}

describe("material library presenters", () => {
  it("recognizes workflow assets from ownership metadata", () => {
    expect(isWorkflowArtifactAsset(asset({ workflowId: "workflow-1" }))).toBe(true);
    expect(isWorkflowArtifactAsset(asset({ assetType: "workflow" }))).toBe(true);
    expect(isWorkflowArtifactAsset(asset())).toBe(false);
  });

  it("bounds extreme preview ratios and classifies panoramas", () => {
    expect(assetPreviewStyle(asset({ width: 100, height: 400 }))).toMatchObject({
      "--material-preview-ratio": "0.5000",
    });
    expect(assetPreviewClass(asset({ width: 4000, height: 500 }))).toBe("material-card__preview-panorama");
  });

  it("prefers workflow then task ownership for sharing", () => {
    expect(materialShareSource(asset({ workflowId: "workflow-1", taskId: "task-1" }))).toEqual({
      sourceType: "workflow",
      sourceId: "workflow-1",
    });
    expect(materialShareSource(asset({ taskId: "task-1" }))).toEqual({
      sourceType: "task",
      sourceId: "task-1",
    });
  });

  it("renders storyboard markdown from asset metadata", () => {
    const html = storyboardPreviewHtml(asset({ metadata: { scriptMarkdown: "## 分镜标题" } }));

    expect(html).toContain("分镜标题");
    expect(html).toContain("<h2");
  });
});
