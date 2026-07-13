/* eslint-disable vue/one-component-per-file -- mounts multiple production components for contract tests */
import { createApp, nextTick } from "vue";
import { createMemoryHistory, createRouter } from "vue-router";
import { describe, expect, it, vi } from "vitest";
import HomeActiveTasks from "@/views/home/components/HomeActiveTasks.vue";
import HomeTaskToast from "@/views/home/components/HomeTaskToast.vue";
import type { TaskListItem } from "@/types";

function router() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [{ path: "/image-tasks", name: "image-tasks", component: HomeTaskToast }],
  });
}

describe("home task components", () => {
  it("renders active task progress and queue state", async () => {
    const host = document.createElement("div");
    const task: TaskListItem = {
      id: "task-1",
      title: "雨夜短片",
      status: "PENDING",
      progress: 42,
      queuePosition: 2,
      createdAt: "2026-01-01T00:00:00Z",
      updatedAt: "2026-01-01T00:00:00Z",
    };
    const app = createApp(HomeActiveTasks, { tasks: [task] });
    app.use(router());
    app.mount(host);
    await nextTick();

    expect(host.textContent).toContain("雨夜短片");
    expect(host.textContent).toContain("队列第 2 位");
    expect(host.textContent).toContain("42%");
    expect(host.querySelector<HTMLElement>(".home-active-task-card__progress span")?.style.width).toBe("42%");
    app.unmount();
  });

  it("emits dismiss from the task toast", async () => {
    const host = document.createElement("div");
    const onDismiss = vi.fn();
    const app = createApp(HomeTaskToast, { taskId: "task-1", onDismiss });
    app.use(router());
    app.mount(host);
    await nextTick();

    host.querySelector<HTMLButtonElement>('button[aria-label="关闭任务提示"]')?.click();
    await nextTick();

    expect(onDismiss).toHaveBeenCalledOnce();
    app.unmount();
  });
});
