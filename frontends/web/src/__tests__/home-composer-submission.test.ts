import { ref } from "vue";
import { describe, expect, it, vi } from "vitest";
import { useHomeComposerSubmission } from "@/composables/home/useHomeComposerSubmission";
import type { HomeSubmissionSnapshot } from "@/features/home/home-submission";

const snapshot = (mode: "image" | "video" = "image"): HomeSubmissionSnapshot => ({
  mode,
  prompt: "一只猫",
  template: null,
  aspectRatio: "1:1",
  textAnalysisModel: "text-model",
  imageModel: "image-model",
  videoModel: "video-model",
  videoSize: "",
  outputCount: 1,
  supportsSeed: true,
  seedMode: "manual",
  manualSeed: 42,
  autoSeed: 7,
  referenceImageUrls: [],
});

function harness(authenticated = true) {
  const statusText = ref("");
  const api = {
    createTask: vi.fn(async () => ({ id: "task-1" }) as never),
    createWorkflow: vi.fn(async () => ({ id: "workflow-1" }) as never),
    saveAspectRatio: vi.fn(async () => undefined as never),
  };
  const resetComposer = vi.fn();
  const loadActiveTasks = vi.fn(async () => undefined);
  const push = vi.fn(async () => undefined);
  const submission = useHomeComposerSubmission({
    statusText,
    isFormReady: () => true,
    modeKind: () => "image",
    snapshot: () => snapshot(),
    imageRequestOptions: () => ({ assetType: "free", resolvedAspectRatio: "1:1" }),
    defaultVideoSize: () => "1920x1080",
    aspectRatio: () => "1:1",
    isAuthenticated: () => authenticated,
    resetComposer,
    loadActiveTasks,
    push,
    dependencies: { api, authenticate: vi.fn(async () => authenticated) },
  });
  return { api, loadActiveTasks, push, resetComposer, statusText, submission };
}

describe("home composer submission", () => {
  it("submits an image task and updates page state", async () => {
    const context = harness();
    await context.submission.submitComposer();

    expect(context.api.createTask).toHaveBeenCalledOnce();
    expect(context.submission.createdTaskId.value).toBe("task-1");
    expect(context.statusText.value).toBe("已提交");
    expect(context.resetComposer).toHaveBeenCalledOnce();
    expect(context.loadActiveTasks).toHaveBeenCalledOnce();
  });

  it("stops before API submission when authentication is declined", async () => {
    const context = harness(false);
    await context.submission.submitComposer();

    expect(context.api.createTask).not.toHaveBeenCalled();
    expect(context.statusText.value).toBe("登录后即可继续生成。");
  });
});
