import { ref } from "vue";
import { describe, expect, it } from "vitest";
import { useWorkflowStageReadiness } from "@/composables/workflow/useWorkflowStageReadiness";
import type { WorkflowDetail } from "@/types";

describe("workflow stage readiness", () => {
  it("derives shared character, video and final-stage readiness", () => {
    const selectedVideo = {
      id: "video-1",
      status: "COMPLETED",
      selected: true,
      downloadUrl: "/storage/video.mp4",
    };
    const workflow = ref({
      storyboardVersions: [{ id: "storyboard-1" }],
      characterSheets: [{ versions: [{ id: "character-1", selected: true }] }],
      clipSlots: [{
        clipIndex: 1,
        keyframeVersions: [],
        videoVersions: [selectedVideo],
      }],
      finalResult: null,
    } as unknown as WorkflowDetail);

    const state = useWorkflowStageReadiness(workflow);

    expect(state.missingCharacterSheets.value).toEqual([]);
    expect(state.videoReadiness.value).toMatchObject({ total: 1, generated: 1, selected: 1 });
    expect(state.canFinalize.value).toBe(true);
    expect(state.finalizeHint.value).toBe("可拼接");
    expect(state.canvasStageItems.value.find((stage) => stage.key === "final")).toMatchObject({
      status: "可拼接",
      ready: true,
    });
  });

  it("keeps an empty workflow out of the finalization path", () => {
    const workflow = ref(null as WorkflowDetail | null);
    const state = useWorkflowStageReadiness(workflow);

    expect(state.canFinalize.value).toBe(false);
    expect(state.finalizeButtonLabel.value).toBe("拼接");
    expect(state.finalizeHint.value).toBe("等待镜头");
  });

  it("uses all analyzed public assets for the material-stage gap", () => {
    const workflow = ref({
      storyboardVersions: [{ id: "storyboard-1" }],
      visualAssets: [
        { assetType: "character", versions: [{ id: "character-1", selected: true }] },
        { assetType: "building", versions: [] },
      ],
      characterSheets: [{ versions: [{ id: "legacy-character", selected: true }] }],
      clipSlots: [],
    } as unknown as WorkflowDetail);

    const state = useWorkflowStageReadiness(workflow);

    expect(state.workflowCharacterSheets.value).toHaveLength(2);
    expect(state.missingCharacterSheets.value).toHaveLength(1);
    expect(state.canvasStageItems.value[1]).toMatchObject({ label: "公共素材", count: "1/2" });
  });
});
