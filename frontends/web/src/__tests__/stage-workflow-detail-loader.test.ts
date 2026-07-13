import { reactive, ref } from "vue";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { createWorkflowSettingsDraft } from "@/features/workflows/workflow-settings";
import type { WorkflowDetail } from "@/types";

const mocks = vi.hoisted(() => ({
  fetchWorkflow: vi.fn(),
  route: { params: { workflowId: "wf_1" }, query: {}, path: "/video-tasks/wf_1" },
  push: vi.fn(() => Promise.resolve()),
  replace: vi.fn(() => Promise.resolve()),
}));

vi.mock("vue-router", () => ({
  useRoute: () => mocks.route,
  useRouter: () => ({ push: mocks.push, replace: mocks.replace }),
}));
vi.mock("@/features/workflows", () => ({ fetchWorkflow: mocks.fetchWorkflow }));
vi.mock("@/composables/useMessage", () => ({ messageApi: { error: vi.fn() } }));

import { useStageWorkflowDetailLoader } from "@/composables/workflow/useStageWorkflowDetailLoader";

function workflow(): WorkflowDetail {
  return {
    id: "wf_1",
    title: "Workflow",
    status: "READY",
    currentStage: "keyframe",
    aspectRatio: "16:9",
    createdAt: "",
    updatedAt: "",
    textAnalysisModel: "text",
    imageModel: "image",
    videoModel: "video",
    storyboardVersions: [{
      id: "story_1", stageType: "storyboard", clipIndex: 0, versionNo: 1,
      title: "Story", status: "READY", selected: true, createdAt: "", updatedAt: "",
    }],
    characterSheets: [],
    clipSlots: [{ clipIndex: 2, keyframeVersions: [], videoVersions: [] }],
  };
}

function createLoader() {
  const selectedWorkflow = ref<WorkflowDetail | null>(null);
  const loadingDetail = ref(false);
  const activeCreateStage = ref<"storyboard" | "character" | "keyframe" | "video">("storyboard");
  const activeCanvasStage = ref<"storyboard" | "character" | "keyframe" | "video" | "final">("storyboard");
  const selectedCanvasClipIndex = ref<number | null>(null);
  const previewStoryboardVersionId = ref("");
  const workflowSettingsDraft = reactive(createWorkflowSettingsDraft());
  const loader = useStageWorkflowDetailLoader({
    selectedWorkflow,
    loadingDetail,
    activeCreateStage,
    activeCanvasStage,
    selectedCanvasClipIndex,
    previewStoryboardVersionId,
    workflowSettingsOpen: ref(false),
    workflowSettingsDraft,
    syncVideoSizeSelection: () => {},
    applyPreviewSelections: () => {},
    loadWorkflows: async () => {},
  });
  return {
    ...loader,
    activeCanvasStage,
    previewStoryboardVersionId,
    selectedCanvasClipIndex,
    selectedWorkflow,
    workflowSettingsDraft,
  };
}

describe("useStageWorkflowDetailLoader", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.fetchWorkflow.mockResolvedValue(workflow());
  });

  it("loads the route workflow and synchronizes its selected preview", async () => {
    const state = createLoader();
    await state.loadWorkflowDetail("wf_1");

    expect(state.selectedWorkflow.value?.id).toBe("wf_1");
    expect(state.previewStoryboardVersionId.value).toBe("story_1");
    expect(state.selectedCanvasClipIndex.value).toBe(2);
    expect(state.workflowSettingsDraft.imageModel).toBe("image");
    expect(state.activeCanvasStage.value).toBe("keyframe");
  });

  it("keeps final-stage routing in the URL", () => {
    const state = createLoader();
    state.switchCanvasStage("final");

    expect(mocks.push).toHaveBeenCalledWith({
      path: "/video-tasks/wf_1",
      query: { stage: "final" },
    });
  });
});
