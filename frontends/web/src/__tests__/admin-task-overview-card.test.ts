import { createApp, nextTick } from "vue";
import ElementPlus from "element-plus";
import { describe, expect, it, vi } from "vitest";
import AdminTaskOverviewCard from "@/admin/components/AdminTaskOverviewCard.vue";
import type { TaskDetail } from "@/types";

describe("admin task overview card", () => {
  it("renders task summaries and emits destructive actions", async () => {
    const host = document.createElement("div");
    const onDelete = vi.fn();
    const app = createApp(AdminTaskOverviewCard, {
      task: {
        id: "task-1",
        title: "雨夜短片",
        status: "FAILED",
        progress: 45,
        aspectRatio: "16:9",
        minDurationSeconds: 5,
        maxDurationSeconds: 8,
        sourceFileName: "script.txt",
        introTemplate: "",
        outroTemplate: "",
        createdAt: "2026-07-11T00:00:00Z",
        updatedAt: "2026-07-11T00:00:00Z",
        outputs: [],
      } satisfies TaskDetail,
      actionLoading: false,
      onDelete,
    });
    app.use(ElementPlus);
    app.mount(host);
    await nextTick();

    expect(host.textContent).toContain("雨夜短片");
    expect(host.textContent).toContain("创建参数");
    host.querySelector<HTMLButtonElement>(".el-button--danger")?.click();
    expect(onDelete).toHaveBeenCalledOnce();

    app.unmount();
  });
});
