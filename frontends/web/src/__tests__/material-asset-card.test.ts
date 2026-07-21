import { createApp, nextTick } from "vue";
import { describe, expect, it, vi } from "vitest";
import MaterialAssetCard from "@/views/materials/components/MaterialAssetCard.vue";
import type { MaterialAssetLibraryItem } from "@/types";

function asset(): MaterialAssetLibraryItem {
  return {
    id: "asset-1",
    stageType: "keyframe",
    clipIndex: 1,
    versionNo: 1,
    selectedForNext: false,
    mediaType: "image",
    title: "关键帧",
    publicUrl: "https://cdn.example/asset.png",
    fileUrl: "",
    previewUrl: "",
    createdAt: "2026-01-01T00:00:00Z",
    updatedAt: "2026-01-01T00:00:00Z",
  };
}

function mountCard(batchMode: boolean, listeners: Record<string, (...args: unknown[]) => void> = {}) {
  const host = document.createElement("div");
  document.body.append(host);
  const app = createApp(MaterialAssetCard, {
    asset: asset(),
    batchMode,
    selected: false,
    favorite: false,
    busyActionKey: "",
    ...listeners,
  });
  app.mount(host);
  return {
    host,
    unmount() {
      app.unmount();
      host.remove();
    },
  };
}

describe("MaterialAssetCard", () => {
  it("opens preview when the card is not in batch mode", async () => {
    const onPreview = vi.fn();
    const wrapper = mountCard(false, { onPreview });

    wrapper.host.querySelector<HTMLButtonElement>(".material-preview-trigger")?.click();
    await nextTick();

    expect(onPreview).toHaveBeenCalledWith(expect.objectContaining({ id: "asset-1" }));
    wrapper.unmount();
  });

  it("turns preview clicks into selection while batch mode is active", async () => {
    const onPreview = vi.fn();
    const onToggleSelection = vi.fn();
    const wrapper = mountCard(true, { onPreview, onToggleSelection });

    wrapper.host.querySelector<HTMLButtonElement>(".material-preview-trigger")?.click();
    await nextTick();

    expect(onToggleSelection).toHaveBeenCalledWith("asset-1");
    expect(onPreview).not.toHaveBeenCalled();
    wrapper.unmount();
  });
});
