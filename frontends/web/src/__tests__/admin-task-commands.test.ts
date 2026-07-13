import { computed, ref } from "vue";
import { describe, expect, it, vi } from "vitest";
import { useAdminTaskCommands } from "@/admin/composables/useAdminTaskCommands";
import type { AdminTaskListItem, AdminTaskBatchResult } from "@/types";

function task(id: string, status: AdminTaskListItem["status"] = "RENDERING") {
  return { id, title: `任务 ${id}`, status } as AdminTaskListItem;
}

function batchResult(
  action: AdminTaskBatchResult["action"],
  succeededTaskIds: string[],
  failedTaskIds: string[] = [],
): AdminTaskBatchResult {
  return {
    action,
    requestedCount: succeededTaskIds.length + failedTaskIds.length,
    succeededTaskIds,
    failed: failedTaskIds.map((taskId) => ({ taskId, error: "failed" })),
  };
}

function harness(items: AdminTaskListItem[]) {
  const selectedTasks = ref(items);
  const selectedTerminableIds = computed(() =>
    selectedTasks.value.filter((item) => item.status === "RENDERING").map((item) => item.id),
  );
  const reloadTasks = vi.fn(async () => undefined);
  const api = {
    terminateOne: vi.fn(async () => undefined),
    terminateMany: vi.fn(async () => batchResult("terminate", [])),
    deleteOne: vi.fn(async () => undefined),
    deleteMany: vi.fn(async () => batchResult("delete", [])),
  };
  const confirm = vi.fn(async () => undefined);
  const message = {
    success: vi.fn(),
    warning: vi.fn(),
    error: vi.fn(),
  };
  const commands = useAdminTaskCommands(
    { selectedTasks, selectedTerminableIds, reloadTasks },
    { api, confirm, message },
  );
  return { selectedTasks, reloadTasks, api, confirm, message, commands };
}

describe("admin task commands", () => {
  it("terminates one task, refreshes and clears its selection", async () => {
    const current = task("one");
    const { selectedTasks, reloadTasks, api, message, commands } = harness([current, task("two")]);

    await commands.terminateSingle(current);

    expect(api.terminateOne).toHaveBeenCalledWith("one");
    expect(selectedTasks.value.map((item) => item.id)).toEqual(["two"]);
    expect(reloadTasks).toHaveBeenCalledOnce();
    expect(commands.successMessage.value).toBe("任务已终止。");
    expect(message.success).toHaveBeenCalledWith("任务已终止。");
    expect(commands.actionLoading.value).toBe(false);
  });

  it("retains only failed selections after a partial batch delete", async () => {
    const { selectedTasks, api, commands } = harness([task("one"), task("two")]);
    api.deleteMany.mockResolvedValue(batchResult("delete", ["one"], ["two"]));

    await commands.deleteSelected();

    expect(api.deleteMany).toHaveBeenCalledWith(["one", "two"]);
    expect(selectedTasks.value.map((item) => item.id)).toEqual(["two"]);
    expect(commands.successMessage.value).toBe("已删除 1 个任务，1 个未成功。");
  });

  it("treats confirmation cancellation as a no-op", async () => {
    const current = task("one");
    const { api, confirm, message, commands } = harness([current]);
    confirm.mockRejectedValue("cancel");

    await commands.deleteSingle(current);

    expect(api.deleteOne).not.toHaveBeenCalled();
    expect(message.error).not.toHaveBeenCalled();
    expect(commands.actionLoading.value).toBe(false);
  });

  it("warns when no terminable task is selected", async () => {
    const { api, message, commands } = harness([task("done", "COMPLETED")]);

    await commands.terminateSelected();

    expect(api.terminateMany).not.toHaveBeenCalled();
    expect(message.warning).toHaveBeenCalledWith("请选择排队或执行中的任务");
  });
});
