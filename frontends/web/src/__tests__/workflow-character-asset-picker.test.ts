import { createApp, h, nextTick } from "vue";
import { describe, expect, it, vi } from "vitest";
import WorkflowCharacterAssetPicker from "@/views/unified/components/WorkflowCharacterAssetPicker.vue";
import type { MaterialAssetLibraryItem } from "@/types";

const asset = {
  id: "asset-1",
  title: "主角三视图",
  thumbnailUrl: "/thumb.png",
  previewUrl: "/preview.png",
  originModel: "gpt-image",
} as MaterialAssetLibraryItem;

describe("workflow character asset picker", () => {
  it("renders asset metadata and emits search, preview and selection commands", async () => {
    const search = vi.fn();
    const preview = vi.fn();
    const select = vi.fn();
    const updateKeyword = vi.fn();
    const host = document.createElement("div");
    const app = createApp({
      render: () => h(WorkflowCharacterAssetPicker, {
        title: "主角",
        busy: false,
        picker: { keyword: "主角", loading: false, error: "", assets: [asset] },
        isPreviewImageAvailable: () => true,
        onSearch: search,
        onPreview: preview,
        onSelect: select,
        "onUpdate:keyword": updateKeyword,
      }),
    });
    app.mount(host);

    expect(host.textContent).toContain("主角三视图");
    expect(host.textContent).toContain("gpt-image");
    (host.querySelector('input[type="search"]') as HTMLInputElement).value = "新关键词";
    host.querySelector('input[type="search"]')?.dispatchEvent(new Event("input", { bubbles: true }));
    (host.querySelector(".character-asset-picker__filters button") as HTMLButtonElement).click();
    (host.querySelector(".character-asset-card__preview") as HTMLButtonElement).click();
    (host.querySelector(".character-asset-card > .jd-button") as HTMLButtonElement).click();
    await nextTick();

    expect(updateKeyword).toHaveBeenCalledWith("新关键词");
    expect(search).toHaveBeenCalledOnce();
    expect(preview).toHaveBeenCalledWith("/thumb.png", "主角三视图");
    expect(select).toHaveBeenCalledWith("asset-1");
    app.unmount();
  });
});
