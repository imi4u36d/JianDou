/* eslint-disable vue/one-component-per-file -- mounts the same production component with multiple prop contracts */
import { createApp, nextTick } from "vue";
import { describe, expect, it, vi } from "vitest";
import WorkflowKeyframeBoard from "@/views/workflow/components/WorkflowKeyframeBoard.vue";
import type { StageVersion, WorkflowClipSlot } from "@/types";

const keyframeVersion: StageVersion = {
  id: "keyframe-v1",
  stageType: "keyframe",
  clipIndex: 1,
  versionNo: 1,
  title: "雨夜镜头 V1",
  status: "SUCCEEDED",
  selected: true,
  outputSummary: { startFrameUrl: "/start.png", endFrameUrl: "/end.png", selectedFirstFrame: true },
  createdAt: "2026-07-11T00:00:00Z",
  updatedAt: "2026-07-11T00:00:00Z",
};

const slot: WorkflowClipSlot = {
  clipIndex: 1,
  shotLabel: "镜头一",
  scene: "雨夜街口缓慢推进",
  durationHint: "8s",
  keyframeVersions: [keyframeVersion],
  videoVersions: [],
};

describe("workflow keyframe board", () => {
  it("renders the selected clip and emits clip generation", async () => {
    const host = document.createElement("div");
    const onGenerate = vi.fn();
    const app = createApp(WorkflowKeyframeBoard, {
      slots: [slot],
      selectedClip: slot,
      previewVersion: keyframeVersion,
      aspectRatio: "16:9",
      busyActionKey: "",
      onGenerate,
    });
    app.mount(host);
    await nextTick();

    expect(host.textContent).toContain("镜头一");
    expect(host.textContent).toContain("雨夜街口缓慢推进");
    expect(host.querySelectorAll(".frame-card")).toHaveLength(2);
    [...host.querySelectorAll<HTMLButtonElement>("button")]
      .find((button) => button.textContent?.trim() === "生成")
      ?.click();
    expect(onGenerate).toHaveBeenCalledWith(1);
    app.unmount();
  });

  it("shows the empty selection state", async () => {
    const host = document.createElement("div");
    const app = createApp(WorkflowKeyframeBoard, {
      slots: [],
      selectedClip: null,
      previewVersion: null,
      aspectRatio: "16:9",
      busyActionKey: "",
    });
    app.mount(host);
    await nextTick();
    expect(host.textContent).toContain("选择分镜版本");
    app.unmount();
  });
});
