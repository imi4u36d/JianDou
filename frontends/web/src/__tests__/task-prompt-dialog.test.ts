/* eslint-disable vue/one-component-per-file -- mounts the same production dialog with multiple prop contracts */
import { createApp, nextTick } from "vue";
import { describe, expect, it, vi } from "vitest";
import TaskPromptDialog from "@/views/unified/components/TaskPromptDialog.vue";

describe("task prompt dialog", () => {
  it("renders prompt content, focuses close and emits close", async () => {
    const host = document.createElement("div");
    document.body.appendChild(host);
    const onClose = vi.fn();
    const app = createApp(TaskPromptDialog, {
      open: true,
      title: "雨夜任务",
      prompt: "生成霓虹雨夜中的追逐镜头",
      onClose,
    });
    app.mount(host);
    await nextTick();
    await nextTick();

    const closeButton = document.querySelector<HTMLButtonElement>('button[aria-label="关闭提示词"]');
    expect(document.body.textContent).toContain("雨夜任务");
    expect(document.body.textContent).toContain("生成霓虹雨夜中的追逐镜头");
    expect(document.activeElement).toBe(closeButton);
    closeButton?.click();
    expect(onClose).toHaveBeenCalledOnce();

    app.unmount();
    host.remove();
  });

  it("renders an explicit empty state", async () => {
    const host = document.createElement("div");
    document.body.appendChild(host);
    const app = createApp(TaskPromptDialog, { open: true, title: "空任务", prompt: "" });
    app.mount(host);
    await nextTick();

    expect(document.body.textContent).toContain("暂无提示词");
    app.unmount();
    host.remove();
  });
});
