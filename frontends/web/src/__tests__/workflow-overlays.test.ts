/* eslint-disable vue/one-component-per-file -- mounts two small production overlay components */
import { createApp, nextTick } from "vue";
import { describe, expect, it, vi } from "vitest";
import CharacterSummaryDialog from "@/views/workflow/components/CharacterSummaryDialog.vue";
import ImagePreviewOverlay from "@/views/workflow/components/ImagePreviewOverlay.vue";

describe("workflow overlays", () => {
  it("renders the character summary and emits close", async () => {
    const host = document.createElement("div");
    const onClose = vi.fn();
    const app = createApp(CharacterSummaryDialog, {
      open: true,
      title: "夜行者",
      content: "黑色风衣，冷静克制。",
      onClose,
    });
    app.mount(host);
    await nextTick();

    expect(host.textContent).toContain("夜行者");
    expect(host.textContent).toContain("黑色风衣");
    host.querySelector<HTMLButtonElement>('button[aria-label="关闭角色定义弹窗"]')?.click();
    expect(onClose).toHaveBeenCalledOnce();
    app.unmount();
  });

  it("supports keyboard image navigation and an image-load fallback", async () => {
    const host = document.createElement("div");
    const onClose = vi.fn();
    const onSwitchFrame = vi.fn();
    const app = createApp(ImagePreviewOverlay, {
      open: true,
      url: "/missing-frame.png",
      alt: "镜头一首帧",
      caption: "镜头一 · 首帧",
      gallerySize: 2,
      onClose,
      onSwitchFrame,
    });
    app.mount(host);
    await nextTick();

    const overlay = host.querySelector<HTMLElement>('[role="dialog"]');
    overlay?.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowRight", bubbles: true }));
    expect(onSwitchFrame).toHaveBeenCalledWith(1);
    overlay?.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
    expect(onClose).toHaveBeenCalledOnce();

    host.querySelector<HTMLImageElement>("img")?.dispatchEvent(new Event("error"));
    await nextTick();
    expect(host.textContent).toContain("镜头一 · 首帧");
    expect(host.querySelector(".image-preview-fallback")).not.toBeNull();
    app.unmount();
  });
});
