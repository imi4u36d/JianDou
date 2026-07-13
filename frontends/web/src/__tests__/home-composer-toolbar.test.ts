/* eslint-disable vue/one-component-per-file -- mounts the same production component with multiple prop contracts */
import { createApp, nextTick } from "vue";
import { describe, expect, it, vi } from "vitest";
import HomeComposerToolbar from "@/views/home/components/HomeComposerToolbar.vue";

function baseProps() {
  const imageMode = { value: "image" as const, kind: "image" as const, label: "图片", description: "", iconName: "image" as const };
  const videoMode = { value: "video" as const, kind: "video" as const, label: "视频", description: "", iconName: "video" as const };
  return {
    activeMenu: "" as const,
    selectedMode: imageMode,
    selectedModeValue: "image" as const,
    modeOptions: [imageMode, videoMode],
    selectedPrimaryModelLabel: "GPT Image",
    textModelOptions: [{ value: "gpt-4.1", label: "GPT-4.1" }],
    imageModelOptions: [{ value: "gpt-image-1", label: "GPT Image 1" }],
    textAnalysisModel: "gpt-4.1",
    imageModel: "gpt-image-1",
    ratioToolLabel: "16:9",
    aspectRatio: "16:9" as const,
    ratioOptions: [
      { value: "16:9" as const, shortLabel: "16:9", shape: "16 / 9" },
      { value: "9:16" as const, shortLabel: "9:16", shape: "9 / 16" },
    ],
    selectedPromptTemplate: null,
    templateChipNonce: 0,
    imageOutputCount: 1,
    imageOutputCountOptions: [1, 2, 3, 4],
    referenceImages: [],
    uploadingReference: false,
    seedMode: "auto" as const,
    seedInput: "",
    autoSeed: 42,
    seedCapabilityHint: "支持种子",
  };
}

function buttonByText(host: HTMLElement, text: string) {
  return [...host.querySelectorAll("button")].find((button) => button.textContent?.trim() === text);
}

describe("home composer toolbar", () => {
  it("emits mode selection from the open mode menu", async () => {
    const host = document.createElement("div");
    const onSelectMode = vi.fn();
    const app = createApp(HomeComposerToolbar, {
      ...baseProps(),
      activeMenu: "mode",
      onSelectMode,
    });
    app.mount(host);
    await nextTick();

    buttonByText(host, "视频")?.click();

    expect(onSelectMode).toHaveBeenCalledWith("video");
    app.unmount();
  });

  it("emits ratio selection without mutating parent state", async () => {
    const host = document.createElement("div");
    const onSelectRatio = vi.fn();
    const app = createApp(HomeComposerToolbar, {
      ...baseProps(),
      activeMenu: "ratio",
      onSelectRatio,
    });
    app.mount(host);
    await nextTick();

    buttonByText(host, "9:16")?.click();

    expect(onSelectRatio).toHaveBeenCalledWith("9:16");
    app.unmount();
  });

  it("renders the selected template and emits reference mentions", async () => {
    const host = document.createElement("div");
    const onInsertMention = vi.fn();
    const app = createApp(HomeComposerToolbar, {
      ...baseProps(),
      activeMenu: "mention",
      selectedPromptTemplate: { id: "ink", title: "水墨", prompt: "东方水墨" },
      referenceImages: [{ id: "ref-1", label: "图片1", fileUrl: "data:image/png;base64,AA==", fileName: "ref.png" }],
      onInsertMention,
    });
    app.mount(host);
    await nextTick();

    expect(host.textContent).toContain("已使用水墨");
    buttonByText(host, "图片1")?.click();
    expect(onInsertMention).toHaveBeenCalledWith("图片1");
    app.unmount();
  });
});
