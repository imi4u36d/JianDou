/* eslint-disable vue/one-component-per-file -- mounts the same production component with multiple prop contracts */
import { createApp, nextTick } from "vue";
import { describe, expect, it, vi } from "vitest";
import WorkflowCharacterBoard from "@/views/workflow/components/WorkflowCharacterBoard.vue";
import type { StageVersion, WorkflowCharacterSheet } from "@/types";

function version(id: string, selected = false): StageVersion {
  return {
    id,
    stageType: "keyframe",
    clipIndex: 1001,
    versionNo: Number(id.slice(-1)),
    title: `角色版本 ${id}`,
    status: "SUCCEEDED",
    selected,
    outputSummary: { frontViewUrl: "/front.png", sideViewUrl: "/side.png", backViewUrl: "/back.png" },
    createdAt: "2026-07-11T00:00:00Z",
    updatedAt: "2026-07-11T00:00:00Z",
  };
}

const sheet: WorkflowCharacterSheet = {
  id: "hero",
  characterName: "主角",
  appearanceSummary: "黑色风衣，银灰短发",
  characterIndex: 1,
  syntheticClipIndex: 1001,
  versions: [version("v1", true), version("v2")],
};

describe("workflow character board", () => {
  it("renders character versions and emits presentation actions", async () => {
    const host = document.createElement("div");
    const onSummary = vi.fn();
    const onPreviewVersion = vi.fn();
    const app = createApp(WorkflowCharacterBoard, {
      sheets: [sheet],
      missingCount: 0,
      previewVersionIds: { hero: "v2" },
      busyActionKey: "",
      onSummary,
      onPreviewVersion,
    });
    app.mount(host);
    await nextTick();

    expect(host.textContent).toContain("主角");
    expect(host.textContent).toContain("黑色风衣，银灰短发");
    expect(host.querySelectorAll(".character-frame")).toHaveLength(3);

    host.querySelector<HTMLButtonElement>(".character-card__summary")?.click();
    const versionButtons = host.querySelectorAll<HTMLButtonElement>(".version-tab button");
    versionButtons[0]?.click();

    expect(onSummary).toHaveBeenCalledWith(sheet);
    expect(onPreviewVersion).toHaveBeenCalledWith("hero", "v1");
    app.unmount();
  });

  it("disables missing generation when all characters are complete", async () => {
    const host = document.createElement("div");
    const app = createApp(WorkflowCharacterBoard, {
      sheets: [sheet],
      missingCount: 0,
      previewVersionIds: {},
      busyActionKey: "",
    });
    app.mount(host);
    await nextTick();

    const fillButton = [...host.querySelectorAll<HTMLButtonElement>("button")].find(
      (button) => button.textContent?.trim() === "补齐",
    );
    expect(fillButton?.disabled).toBe(true);
    app.unmount();
  });
});
