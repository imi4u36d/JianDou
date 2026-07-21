/* eslint-disable vue/one-component-per-file -- mounts the same production preview with multiple states */
import { createApp, nextTick } from "vue";
import { describe, expect, it, vi } from "vitest";
import TaskResultPreview from "@/views/unified/components/TaskResultPreview.vue";

describe("task result preview", () => {
  it("renders media and emits preview and download actions", async () => {
    const host = document.createElement("div");
    const onPreview = vi.fn();
    const onDownload = vi.fn();
    const app = createApp(TaskResultPreview, {
      progressPercent: 100,
      previewLoading: false,
      loadState: "ready",
      mediaItems: [{ type: "image", url: "/result.png", title: "结果图" }],
      referenceItems: [{ url: "/reference.png", title: "参考图" }],
      awaitingCompletedPreview: false,
      taskStatus: "COMPLETED",
      onPreview,
      onDownload,
    });
    app.mount(host);
    await nextTick();

    const imageButton = host.querySelector<HTMLButtonElement>(".task-result-preview__image-button");
    expect(imageButton?.querySelectorAll("img")).toHaveLength(1);
    const resultImage = imageButton?.querySelector<HTMLImageElement>("img");
    expect(resultImage?.getAttribute("src")).toBe("/result.png");
    Object.defineProperties(resultImage, {
      naturalWidth: { configurable: true, value: 1920 },
      naturalHeight: { configurable: true, value: 1080 },
    });
    resultImage?.dispatchEvent(new Event("load"));
    await nextTick();

    expect(imageButton?.querySelector(".task-result-preview__image-meta")?.textContent).toContain(
      "分辨率 1920 × 1080 px · 比例 16:9",
    );
    imageButton?.click();
    host.querySelector<HTMLButtonElement>('button[aria-label="下载参考图"]')?.click();
    expect(onPreview).toHaveBeenCalledWith("结果图", "/result.png");
    expect(onDownload).toHaveBeenCalledWith("/reference.png", "参考图", "image");
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
    });
    app.mount(host);
    await nextTick();

    expect(host.textContent).toContain("加载预览中");
    expect(host.textContent).toContain("预览加载失败");
    app.unmount();
  });
});
