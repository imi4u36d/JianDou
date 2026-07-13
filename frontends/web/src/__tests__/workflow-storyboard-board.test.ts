import { createApp, nextTick } from "vue";
import { describe, expect, it, vi } from "vitest";
import type { StageVersion } from "@/types";
import WorkflowStoryboardBoard from "@/views/workflow/components/WorkflowStoryboardBoard.vue";

const version: StageVersion = {
  id: "storyboard-v1",
  stageType: "storyboard",
  clipIndex: 0,
  versionNo: 1,
  title: "雨夜分镜",
  status: "SUCCEEDED",
  selected: true,
  outputSummary: { scriptMarkdown: "## 镜头一\n雨夜街口" },
  createdAt: "2026-07-11T00:00:00Z",
  updatedAt: "2026-07-11T00:00:00Z",
};

describe("workflow storyboard board", () => {
  it("renders the selected version and emits normalized board actions", async () => {
    const host = document.createElement("div");
    const onGenerate = vi.fn();
    const onPreview = vi.fn();
    const app = createApp(WorkflowStoryboardBoard, {
      versions: [version],
      selectedVersion: version,
      adjustment: "增强雨景",
      busyActionKey: "",
      onGenerate,
      onPreview,
    });
    app.mount(host);
    await nextTick();

    expect(host.textContent).toContain("雨夜分镜");
    expect(host.textContent).toContain("雨夜街口");
    [...host.querySelectorAll<HTMLButtonElement>("button")]
      .find((button) => button.textContent?.trim() === "生成")
      ?.click();
    host.querySelector<HTMLButtonElement>(".version-switcher__tab-main")?.click();

    expect(onGenerate).toHaveBeenCalledOnce();
    expect(onPreview).toHaveBeenCalledWith("storyboard-v1");
    app.unmount();
  });
});
