import { createApp, ref } from "vue";
import { describe, expect, it, vi } from "vitest";
import { useTaskDetailCommands } from "@/views/unified/composables/useTaskDetailCommands";
import { useTaskDetailLoader } from "@/views/unified/composables/useTaskDetailLoader";
import type { TaskDetail, TaskListItem } from "@/types";

const task = { id: "task-1", title: "测试任务", status: "FAILED" } as TaskListItem;
const detail = { ...task, outputs: [], materials: [] } as unknown as TaskDetail;

describe("task detail state", () => {
  it("loads selected detail through an injectable request port", async () => {
    const selectedId = ref("task-1");
    const fetch = vi.fn(async () => detail);
    const message = { error: vi.fn() };
    let loader!: ReturnType<typeof useTaskDetailLoader>;
    const app = createApp({
      setup() {
        loader = useTaskDetailLoader({
          selectedTaskId: () => selectedId.value,
          selectedTaskSummary: () => task,
          dependencies: { fetch, message, pollIntervalMs: 60_000 },
        });
        return () => null;
      },
    });
    const host = document.createElement("div");
    app.mount(host);

    await loader.loadSelectedTaskDetails();
    expect(fetch).toHaveBeenCalledWith("task-1");
    expect(loader.selectedTaskDetail.value?.id).toBe("task-1");
    expect(loader.selectedTaskLoading.value).toBe(false);
    expect(message.error).not.toHaveBeenCalled();
    app.unmount();
  });

  it("runs authenticated commands and refreshes both views", async () => {
    const api = {
      retry: vi.fn(async () => detail),
      pause: vi.fn(async () => detail),
      continue: vi.fn(async () => detail),
      terminate: vi.fn(async () => detail),
      delete: vi.fn(async () => ({ taskId: "task-1", deleted: true })),
    };
    const reloadTasks = vi.fn(async () => undefined);
    const reloadDetail = vi.fn(async () => undefined);
    const message = { success: vi.fn(), error: vi.fn() };
    const commands = useTaskDetailCommands({
      selectedTaskId: () => "task-1",
      reloadTasks,
      reloadDetail,
      requestConfirm: vi.fn(async () => true),
      dependencies: { api, authenticate: vi.fn(async () => true), message },
    });

    await commands.handlePause(task);
    expect(api.pause).toHaveBeenCalledWith("task-1");
    expect(reloadTasks).toHaveBeenCalledOnce();
    expect(reloadDetail).toHaveBeenCalledOnce();
    expect(commands.managingTaskId.value).toBe("");
  });

  it("does not terminate when confirmation is declined", async () => {
    const api = {
      retry: vi.fn(async () => detail),
      pause: vi.fn(async () => detail),
      continue: vi.fn(async () => detail),
      terminate: vi.fn(async () => detail),
      delete: vi.fn(async () => ({ taskId: "task-1", deleted: true })),
    };
    const commands = useTaskDetailCommands({
      selectedTaskId: () => "task-1",
      reloadTasks: vi.fn(async () => undefined),
      reloadDetail: vi.fn(async () => undefined),
      requestConfirm: vi.fn(async () => false),
      dependencies: {
        api,
        authenticate: vi.fn(async () => true),
        message: { success: vi.fn(), error: vi.fn() },
      },
    });

    await commands.handleTerminate(task);
    expect(api.terminate).not.toHaveBeenCalled();
  });
});
