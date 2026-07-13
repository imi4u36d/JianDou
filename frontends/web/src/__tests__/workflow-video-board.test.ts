/* eslint-disable vue/one-component-per-file -- mounts the same production component with multiple prop contracts */
import { createApp, nextTick } from "vue";
import { describe, expect, it, vi } from "vitest";
import WorkflowVideoBoard from "@/views/workflow/components/WorkflowVideoBoard.vue";
import type { StageVersion, WorkflowClipSlot } from "@/types";

const keyframe: StageVersion = {
  id: "keyframe-v1",
  stageType: "keyframe",
  clipIndex: 1,
  versionNo: 1,
  title: "关键帧 V1",
  status: "SUCCEEDED",
  selected: true,
  outputSummary: {
    startFrameUrl: "/start.png",
    endFrameUrl: "/end.png",
    selectedFirstFrame: true,
    selectedLastFrame: true,
  },
  createdAt: "2026-07-11T00:00:00Z",
  updatedAt: "2026-07-11T00:00:00Z",
};
const video: StageVersion = {
  id: "video-v1",
  stageType: "video",
  clipIndex: 1,
  versionNo: 1,
  title: "视频 V1",
  status: "COMPLETED",
  selected: true,
  previewUrl: "/preview.mp4",
  downloadUrl: "/video.mp4",
  createdAt: "2026-07-11T00:00:00Z",
  updatedAt: "2026-07-11T00:00:00Z",
};
const slot: WorkflowClipSlot = {
  clipIndex: 1,
  shotLabel: "镜头一",
  scene: "雨夜追逐",
  durationHint: "8s",
  keyframeVersions: [keyframe],
  videoVersions: [video],
};

describe("workflow video board", () => {
  it("renders readiness, keyframes, and the selected video", async () => {
    const host = document.createElement("div");
    const onGenerate = vi.fn();
    const app = createApp(WorkflowVideoBoard, {
      slots: [slot],
      selectedClip: slot,
      previewVersion: video,
      readiness: { total: 1, generated: 1, selected: 1, missing: [] },
      canFinalize: true,
      busyActionKey: "",
      onGenerate,
    });
    app.mount(host);
    await nextTick();

    expect(host.textContent).toContain("可拼接");
    expect(host.textContent).toContain("雨夜追逐");
    expect(host.querySelectorAll(".keyframe-thumb")).toHaveLength(2);
    expect(host.querySelector("video")?.getAttribute("src")).toBe("/preview.mp4");
    [...host.querySelectorAll<HTMLButtonElement>("button")]
      .find((button) => button.textContent?.trim() === "生成")
      ?.click();
    expect(onGenerate).toHaveBeenCalledWith(1);
    app.unmount();
  });

  it("shows the empty video state", async () => {
    const host = document.createElement("div");
    const emptySlot = { ...slot, videoVersions: [] };
    const app = createApp(WorkflowVideoBoard, {
      slots: [emptySlot],
      selectedClip: emptySlot,
      previewVersion: null,
      readiness: { total: 1, generated: 0, selected: 0, missing: [emptySlot] },
      canFinalize: false,
      busyActionKey: "",
    });
    app.mount(host);
    await nextTick();
    expect(host.textContent).toContain("暂无视频版本");
    expect(host.textContent).toContain("差 1");
    app.unmount();
  });
});
