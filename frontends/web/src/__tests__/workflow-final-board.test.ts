/* eslint-disable vue/one-component-per-file -- mounts the same production component with multiple prop contracts */
import { createApp, nextTick } from "vue";
import { describe, expect, it, vi } from "vitest";
import WorkflowFinalBoard from "@/views/workflow/components/WorkflowFinalBoard.vue";
import type { MaterialAssetLibraryItem, WorkflowClipSlot } from "@/types";

const finalResult = {
  id: "final-1",
  title: "雨夜成片",
  publicUrl: "/final.mp4",
  fileUrl: "/final.mp4",
  durationSeconds: 16,
} as MaterialAssetLibraryItem;
const missingClip: WorkflowClipSlot = { clipIndex: 2, shotLabel: "镜头二", keyframeVersions: [], videoVersions: [] };

describe("workflow final board", () => {
  it("renders a completed result and emits download", async () => {
    const host = document.createElement("div");
    const onDownload = vi.fn();
    const app = createApp(WorkflowFinalBoard, {
      finalResult,
      readiness: { total: 1, selected: 1, missing: [] },
      canFinalize: true,
      finalizeHint: "可拼接",
      finalizeButtonLabel: "重拼",
      busyActionKey: "",
      onDownload,
    });
    app.mount(host);
    await nextTick();

    expect(host.textContent).toContain("雨夜成片");
    expect(host.textContent).toContain("16.0s");
    host.querySelector<HTMLButtonElement>('button[aria-label="下载成片"]')?.click();
    expect(onDownload).toHaveBeenCalledWith("/final.mp4", "雨夜成片");
    app.unmount();
  });

  it("emits the missing clip selected for completion", async () => {
    const host = document.createElement("div");
    const onOpenMissing = vi.fn();
    const app = createApp(WorkflowFinalBoard, {
      finalResult: null,
      readiness: { total: 2, selected: 1, missing: [missingClip] },
      canFinalize: false,
      finalizeHint: "缺 1",
      finalizeButtonLabel: "拼接",
      busyActionKey: "",
      onOpenMissing,
    });
    app.mount(host);
    await nextTick();

    expect(host.textContent).toContain("缺 1 个镜头");
    [...host.querySelectorAll<HTMLButtonElement>("button")]
      .find((button) => button.textContent?.trim() === "镜头二")
      ?.click();
    expect(onOpenMissing).toHaveBeenCalledWith(2);
    app.unmount();
  });
});
