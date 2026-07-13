import { createApp, h, nextTick, ref } from "vue";
import { describe, expect, it, vi } from "vitest";
import TaskDetailActions from "@/views/unified/components/TaskDetailActions.vue";
import type { TaskListItem } from "@/types";

function task(status: TaskListItem["status"]): TaskListItem {
  return {
    id: "task-1",
    title: "Task",
    status,
    progress: 50,
    createdAt: "2026-01-01T00:00:00Z",
    updatedAt: "2026-01-01T00:00:00Z",
  };
}

describe("task detail actions", () => {
  it("projects status-specific commands and emits the selected task", async () => {
    const selected = ref(task("FAILED"));
    const retry = vi.fn();
    const host = document.createElement("div");
    const app = createApp({
      render: () => h(TaskDetailActions, {
        task: selected.value,
        loading: false,
        managingTaskId: "",
        imageMode: false,
        onRetry: retry,
      }),
    });
    app.mount(host);

    expect(host.textContent).toContain("重试");
    expect(host.textContent).not.toContain("暂停");
    const retryButton = [...host.querySelectorAll("button")].find((button) => button.textContent?.includes("重试"));
    retryButton?.click();
    expect(retry).toHaveBeenCalledWith(selected.value);

    selected.value = task("PAUSED");
    await nextTick();
    expect(host.textContent).toContain("继续");
    expect(host.textContent).not.toContain("重试");
    app.unmount();
  });
});
