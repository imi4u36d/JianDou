import { ref } from "vue";
import { describe, expect, it } from "vitest";
import { useWorkflowStagePreviews } from "@/composables/workflow/useWorkflowStagePreviews";
import type { StageVersion, WorkflowDetail } from "@/types";

function version(id: string, selected = false): StageVersion {
  return {
    id,
    stageType: "keyframe",
    clipIndex: 1,
    versionNo: Number(id.slice(-1)),
    title: id,
    status: "SUCCEEDED",
    selected,
    outputSummary: {},
    createdAt: "2026-07-11T00:00:00Z",
    updatedAt: "2026-07-11T00:00:00Z",
  };
}

function workflow(): WorkflowDetail {
  return {
    id: "wf-1",
    title: "雨夜",
    aspectRatio: "16:9",
    textAnalysisModel: "gpt-5.5",
    imageModel: "gpt-image-2",
    videoModel: "seedance",
    status: "DRAFT",
    currentStage: "keyframe",
    createdAt: "2026-07-11T00:00:00Z",
    updatedAt: "2026-07-11T00:00:00Z",
    storyboardVersions: [version("s1"), version("s2", true)],
    characterSheets: [
      {
        id: "hero",
        characterName: "主角",
        syntheticClipIndex: 1001,
        versions: [version("c1", true), version("c2")],
      },
    ],
    clipSlots: [
      {
        clipIndex: 1,
        keyframeVersions: [version("k1"), version("k2", true)],
        videoVersions: [version("v1", true), version("v2")],
      },
    ],
  };
}

describe("workflow stage preview state", () => {
  it("repairs stale preview choices from selected workflow versions", () => {
    const currentWorkflow = workflow();
    const selectedWorkflow = ref<WorkflowDetail | null>(currentWorkflow);
    const previews = useWorkflowStagePreviews(selectedWorkflow);
    previews.previewStoryboardVersionId.value = "missing";
    previews.previewKeyframeVersionIds[1] = "missing";
    previews.applyPreviewSelections(currentWorkflow);

    expect(previews.selectedStoryboardVersion.value?.id).toBe("s2");
    expect(previews.previewKeyframeVersion.value?.id).toBe("k2");
    expect(previews.previewVideoVersion.value?.id).toBe("v1");
    expect(previews.previewCharacterSheetVersion(currentWorkflow.characterSheets![0])?.id).toBe("c1");
  });

  it("keeps storyboard adjustment drafts with their version", () => {
    const currentWorkflow = workflow();
    const selectedWorkflow = ref<WorkflowDetail | null>(currentWorkflow);
    const previews = useWorkflowStagePreviews(selectedWorkflow);
    previews.applyPreviewSelections(currentWorkflow);
    previews.setStoryboardAdjustment("s2", "加强雨夜氛围");

    expect(previews.selectedStoryboardAdjustment.value).toBe("加强雨夜氛围");
    previews.updateSelectedStoryboardAdjustment("缩短镜头");
    expect(previews.storyboardAdjustment("s2")).toBe("缩短镜头");
  });

  it("owns explicit preview and clip selection setters", () => {
    const selectedWorkflow = ref<WorkflowDetail | null>(workflow());
    const previews = useWorkflowStagePreviews(selectedWorkflow);

    previews.selectCanvasClip(1);
    previews.setPreviewStoryboardVersion("s1");
    previews.setPreviewCharacterSheetVersion("hero", "c2");
    previews.setPreviewKeyframeVersion(1, "k1");
    previews.setPreviewVideoVersion(1, "v2");

    expect(previews.selectedCanvasClip.value?.clipIndex).toBe(1);
    expect(previews.selectedStoryboardVersion.value?.id).toBe("s1");
    expect(previews.previewCharacterSheetVersion(selectedWorkflow.value!.characterSheets![0])?.id).toBe("c2");
    expect(previews.previewKeyframeVersion.value?.id).toBe("k1");
    expect(previews.previewVideoVersion.value?.id).toBe("v2");
  });
});
