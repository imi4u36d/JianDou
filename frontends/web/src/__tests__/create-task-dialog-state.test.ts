import { createApp, defineComponent, h } from "vue";
import { describe, expect, it, vi } from "vitest";
import type {
  CreateWorkflowRequest,
  GenerationOptionsResponse,
  WorkflowDetail,
} from "@/types";
import { useCreateTaskDialog } from "@/views/unified/composables/useCreateTaskDialog";

const options: GenerationOptionsResponse = {
  aspectRatios: [{ value: "16:9", label: "横屏" }],
  defaultAspectRatio: "16:9",
  imageSizes: [],
  textAnalysisModels: [{ value: "gpt", label: "GPT", provider: "openai" }],
  imageModels: [{ value: "image", label: "Image", provider: "openai" }],
  videoModels: [{ value: "video", label: "Agnes Video", provider: "agnes" }],
  videoSizes: [{ value: "1280x720", label: "HD", supportedModels: ["video"] }],
  videoDurations: [],
};

describe("create task dialog state", () => {
  it("owns the authenticated creation transaction through injected ports", async () => {
    const create = vi.fn(async (_payload: CreateWorkflowRequest) => ({
      id: "workflow_1",
    }) as WorkflowDetail);
    const created = vi.fn();
    let state: ReturnType<typeof useCreateTaskDialog> | undefined;
    const app = createApp(defineComponent({
      setup() {
        state = useCreateTaskDialog({
          open: () => false,
          close: vi.fn(),
          created,
          dependencies: {
            fetchOptions: vi.fn(async () => options),
            create,
            authenticate: vi.fn(async () => true),
            authenticated: () => false,
            saveAspectRatio: vi.fn(async () => undefined),
          },
        });
        return () => h("div");
      },
    }));
    app.mount(document.createElement("div"));

    state!.taskTitle.value = "  New workflow  ";
    state!.taskPrompt.value = "  A short film  ";
    await state!.submitTask();

    expect(create).toHaveBeenCalledWith({
      title: "New workflow",
      transcriptText: "A short film",
      aspectRatio: "16:9",
      textAnalysisModel: "gpt",
      imageModel: "image",
      videoModel: "video",
      videoSize: "1280x720",
      durationMode: "auto",
      executionMode: "auto",
    });
    expect(created).toHaveBeenCalledWith("workflow_1");
    expect(state!.taskTitle.value).toBe("");
    expect(state!.taskStatusText.value).toBe("创建成功");
    expect(state!.submitting.value).toBe(false);

    app.unmount();
  });
});
