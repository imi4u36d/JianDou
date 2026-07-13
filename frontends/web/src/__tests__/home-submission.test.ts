import { describe, expect, it, vi } from "vitest";
import {
  buildCreativePrompt,
  buildImageGenerationRequest,
  buildSubmitFingerprint,
  buildVideoWorkflowRequest,
  type HomeSubmissionSnapshot,
} from "@/features/home/home-submission";
import { useHomeSubmissionGuard } from "@/composables/home/useHomeSubmissionGuard";

function snapshot(overrides: Partial<HomeSubmissionSnapshot> = {}): HomeSubmissionSnapshot {
  return {
    mode: "image",
    prompt: "一只猫",
    template: null,
    aspectRatio: "1:1",
    textAnalysisModel: "text-model",
    imageModel: "image-model",
    videoModel: "video-model",
    videoSize: "",
    outputCount: 2,
    supportsSeed: true,
    seedMode: "manual",
    manualSeed: 42,
    autoSeed: 7,
    referenceImageUrls: [],
    ...overrides,
  };
}

describe("home submission payloads", () => {
  it("applies a prompt template without mutating the user's text", () => {
    expect(
      buildCreativePrompt("一只猫", {
        id: "ink",
        title: "水墨",
        prompt: "[主体]，东方水墨",
      }),
    ).toBe("一只猫\n\n画风模板：水墨\n画风提示词：一只猫，东方水墨");
  });

  it("builds a stable fingerprint regardless of reference order", () => {
    const left = buildSubmitFingerprint(snapshot({ referenceImageUrls: ["b.jpg", "a.jpg"] }));
    const right = buildSubmitFingerprint(snapshot({ referenceImageUrls: ["a.jpg", "b.jpg"] }));

    expect(left).toBe(right);
  });

  it("builds image-to-image and video requests from one snapshot", () => {
    const input = snapshot({ referenceImageUrls: ["reference.jpg"], aspectRatio: "1:1" });

    expect(buildImageGenerationRequest(input, { assetType: "image", resolvedAspectRatio: "1024x1024" })).toMatchObject({
      taskType: "image_to_image",
      aspectRatio: "1024x1024",
      seed: 42,
      referenceImageUrls: ["reference.jpg"],
    });
    expect(buildVideoWorkflowRequest(input, "1280*720")).toMatchObject({
      title: "一只猫",
      transcriptText: "一只猫",
      aspectRatio: "16:9",
      videoSize: "1280*720",
      executionMode: "auto",
    });
  });
});

describe("home submission guard", () => {
  it("blocks concurrent and recently successful duplicate submissions", () => {
    let timestamp = 1000;
    const guard = useHomeSubmissionGuard({ now: () => timestamp, duplicateWindowMs: 3000 });

    expect(guard.begin("same")).toBe("started");
    expect(guard.begin("other")).toBe("busy");
    guard.finish("same", true);
    timestamp = 2000;
    expect(guard.begin("same")).toBe("duplicate");
    timestamp = 5000;
    expect(guard.begin("same")).toBe("started");
  });

  it("expires and dismisses task toasts", () => {
    vi.useFakeTimers();
    const guard = useHomeSubmissionGuard({ toastDurationMs: 5000 });

    guard.showTaskToast("task-1");
    expect(guard.taskToastTaskId.value).toBe("task-1");
    vi.advanceTimersByTime(5000);
    expect(guard.taskToastTaskId.value).toBe("");
    guard.showTaskToast("task-2");
    guard.dismissTaskToast();
    expect(guard.taskToastTaskId.value).toBe("");
    vi.useRealTimers();
  });
});
