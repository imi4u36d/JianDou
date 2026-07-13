import { computed, reactive, ref } from "vue";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { WorkflowDetail } from "@/types";
import { createWorkflowSettingsDraft } from "@/features/workflows/workflow-settings";
import { useWorkflowStagePreviews } from "@/composables/workflow/useWorkflowStagePreviews";

const mocks = vi.hoisted(() => ({
  fetchWorkflow: vi.fn(),
  replace: vi.fn(() => Promise.resolve()),
}));

vi.mock("vue-router", () => ({
  useRoute: () => ({ query: {} }),
  useRouter: () => ({ replace: mocks.replace }),
}));

vi.mock("@/features/workflows", () => ({ fetchWorkflow: mocks.fetchWorkflow }));
vi.mock("@/composables/useMessage", () => ({ messageApi: { error: vi.fn() } }));

import { useWorkflowDetailLoader } from "@/views/unified/composables/useWorkflowDetailLoader";

function workflow(): WorkflowDetail {
  return {
    id: "wf_1",
    title: "Workflow",
    status: "READY",
    currentStage: "keyframe",
    aspectRatio: "9:16",
    createdAt: "2026-01-01",
    updatedAt: "2026-01-01",
    characterSheetCount: 1,
    textAnalysisModel: "text-1",
    imageModel: "image-1",
    videoModel: "video-1",
    storyboardVersions: [{
      id: "story_1", stageType: "storyboard", clipIndex: 0, versionNo: 1,
      title: "Story", status: "READY", selected: true, createdAt: "", updatedAt: "",
    }],
    characterSheets: [{
      id: "character_1",
      versions: [{
        id: "character_version_1", stageType: "keyframe", clipIndex: 1001, versionNo: 1,
        title: "Character", status: "READY", selected: true, createdAt: "", updatedAt: "",
      }],
    }],
    clipSlots: [{
      clipIndex: 1,
      keyframeVersions: [{
        id: "keyframe_1", stageType: "keyframe", clipIndex: 1, versionNo: 1,
        title: "Keyframe", status: "READY", selected: true, createdAt: "", updatedAt: "",
      }],
      videoVersions: [],
    }],
  };
}

function createLoader() {
  const selectedWorkflow = ref<WorkflowDetail | null>(null);
  const settings = reactive(createWorkflowSettingsDraft());
  const previews = useWorkflowStagePreviews(selectedWorkflow);
  const activeCanvasStage = ref<"storyboard" | "character" | "keyframe" | "video" | "final">("storyboard");
  const selectedCanvasClipIndex = ref<number | null>(null);
  const loader = useWorkflowDetailLoader({
    selectedWorkflowId: computed(() => "wf_1"),
    selectedWorkflow,
    loadingDetail: ref(false),
    activeCanvasStage,
    selectedCanvasClipIndex,
    workflowSettingsOpen: ref(false),
    workflowSettingsDraft: settings,
    applyPreviewSelections: previews.applyPreviewSelections,
    syncVideoSizeSelection: () => {},
    closeCharacterAssetPicker: () => {},
    reloadWorkflows: async () => {},
  });
  return {
    ...loader,
    activeCanvasStage,
    previewCharacterSheetVersionIds: previews.previewCharacterSheetVersionIds,
    previewKeyframeVersionIds: previews.previewKeyframeVersionIds,
    previewStoryboardVersionId: previews.previewStoryboardVersionId,
    selectedCanvasClipIndex,
    selectedWorkflow,
    settings,
  };
}

describe("useWorkflowDetailLoader", () => {
  beforeEach(() => vi.clearAllMocks());

  it("synchronizes settings and selected preview versions", () => {
    const state = createLoader();
    state.applyWorkflowDrafts(workflow());

    expect(state.settings.aspectRatio).toBe("9:16");
    expect(state.previewStoryboardVersionId.value).toBe("story_1");
    expect(state.previewCharacterSheetVersionIds.character_1).toBe("character_version_1");
    expect(state.previewKeyframeVersionIds[1]).toBe("keyframe_1");
  });

  it("loads workflow data and selects the first available clip", async () => {
    mocks.fetchWorkflow.mockResolvedValue(workflow());
    const state = createLoader();

    await state.loadWorkflowDetail("wf_1");

    expect(state.selectedWorkflow.value?.id).toBe("wf_1");
    expect(state.selectedCanvasClipIndex.value).toBe(1);
    expect(state.activeCanvasStage.value).toBe("keyframe");
  });
});
