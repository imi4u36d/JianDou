/* eslint-disable vue/one-component-per-file -- mounts the same production preview with multiple states */
import { createApp, nextTick } from "vue";
import { describe, expect, it, vi } from "vitest";
import TaskResultPreview from "@/views/unified/components/TaskResultPreview.vue";

describe("task result preview", () => {
  it("renders media and emits preview, download and share actions", async () => {
    const host = document.createElement("div");
    const onPreview = vi.fn();
    const onDownload = vi.fn();
    const onShare = vi.fn();
    const app = createApp(TaskResultPreview, {
      progressPercent: 100,
      previewLoading: false,
      loadState: "ready",
      mediaItems: [{ type: "image", url: "/result.png", title: "结果图" }],
      referenceItems: [{ url: "/reference.png", title: "参考图" }],
      awaitingCompletedPreview: false,
      taskStatus: "COMPLETED",
      shareable: true,
      sharing: false,
      shared: false,
      onPreview,
      onDownload,
      onShare,
    });
    app.mount(host);
    await nextTick();

    host.querySelector<HTMLButtonElement>(".task-result-preview__image-button")?.click();
    host.querySelector<HTMLButtonElement>('button[aria-label="下载参考图"]')?.click();
    [...host.querySelectorAll<HTMLButtonElement>(".task-result-preview__action")]
      .find((button) => button.textContent?.includes("分享"))
      ?.click();

    expect(onPreview).toHaveBeenCalledWith("结果图", "/result.png");
    expect(onDownload).toHaveBeenCalledWith("/reference.png", "参考图", "image");
    expect(onShare).toHaveBeenCalledOnce();
    app.unmount();
  });

  it("renders pending and failed load states explicitly", async () => {
    const host = document.createElement("div");
    const app = createApp(TaskResultPreview, {
      progressPercent: 80,
      previewLoading: false,
      loadState: "failed",
      mediaItems: [],
      referenceItems: [],
      awaitingCompletedPreview: true,
      taskStatus: "RENDERING",
      shareable: false,
      sharing: false,
      shared: false,
    });
    app.mount(host);
    await nextTick();

    expect(host.textContent).toContain("加载预览中");
    expect(host.textContent).toContain("预览加载失败");
    app.unmount();
  });
});
