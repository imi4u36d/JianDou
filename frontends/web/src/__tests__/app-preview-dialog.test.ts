import { createApp, nextTick } from "vue";
import { describe, expect, it, vi } from "vitest";
import AppPreviewDialog from "@/components/common/AppPreviewDialog.vue";

describe("AppPreviewDialog", () => {
  it("renders through Teleport and handles keyboard navigation", async () => {
    const host = document.createElement("div");
    document.body.appendChild(host);
    const onPrevious = vi.fn();
    const onNext = vi.fn();
    const onClose = vi.fn();
    const app = createApp(AppPreviewDialog, {
      open: true,
      kind: "image",
      title: "预览图",
      url: "/preview.png",
      showNavigation: true,
      canPrevious: true,
      canNext: true,
      onPrevious,
      onNext,
      onClose,
    });
    app.mount(host);
    await nextTick();
    await nextTick();

    const dialog = document.body.querySelector<HTMLElement>(".app-preview-dialog-overlay");
    expect(dialog).not.toBeNull();
    dialog!.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowLeft", bubbles: true }));
    dialog!.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowRight", bubbles: true }));
    dialog!.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
    expect(onPrevious).toHaveBeenCalledOnce();
    expect(onNext).toHaveBeenCalledOnce();
    expect(onClose).toHaveBeenCalledOnce();

    app.unmount();
    host.remove();
  });
});
