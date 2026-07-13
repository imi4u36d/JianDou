import { describe, expect, it, vi } from "vitest";
import { useAdminTaskList } from "@/admin/composables/useAdminTaskList";
import type { AdminTaskListItem, TaskDetail } from "@/types";

const task = (id: string, status: AdminTaskListItem["status"] = "PENDING") => ({
  id,
  status,
  title: id,
}) as AdminTaskListItem;

describe("admin task list", () => {
  it("owns pagination queries, selection recovery and detail caching", async () => {
    const fetchTasks = vi.fn(async () => ({
      items: [task("task-2", "COMPLETED")],
      total: 21,
      offset: 10,
      limit: 10,
    }));
    const fetchTask = vi.fn(async (id: string) => ({ id, status: "COMPLETED" }) as TaskDetail);
    const state = useAdminTaskList({ fetchTasks, fetchTask, notifyError: vi.fn() });
    state.currentPage.value = 2;
    state.pageSize.value = 10;
    state.selectedTasks.value = [task("task-1"), task("task-2", "COMPLETED")];

    await state.loadTasks();
    await state.loadTaskDetail("task-2");
    await state.loadTaskDetail("task-2");

    expect(fetchTasks).toHaveBeenCalledWith(expect.objectContaining({ offset: 10, limit: 10 }));
    expect(state.totalTasks.value).toBe(21);
    expect(state.selectedTasks.value.map((item) => item.id)).toEqual(["task-2"]);
    expect(fetchTask).toHaveBeenCalledOnce();
    expect(state.taskDetails["task-2"]?.id).toBe("task-2");
  });

  it("reports fetch failures and always releases loading state", async () => {
    const notifyError = vi.fn();
    const state = useAdminTaskList({
      fetchTasks: vi.fn(async () => { throw new Error("network down"); }),
      notifyError,
    });

    await state.loadTasks();

    expect(notifyError).toHaveBeenCalledWith("network down");
    expect(state.initialLoading.value).toBe(false);
    expect(state.refreshing.value).toBe(false);
  });
});
