import { createApp, nextTick } from "vue";
import { describe, expect, it, vi } from "vitest";
import type { WorkflowSummary } from "@/types";
import WorkflowProjectDrawer from "@/views/workflow/components/WorkflowProjectDrawer.vue";

const workflow: WorkflowSummary = {
  id: "workflow-1",
  title: "一个需要在列表中单行省略的较长视频任务名称",
  status: "draft",
  currentStage: "storyboard",
  aspectRatio: "9:16",
  createdAt: "2026-07-20T00:00:00Z",
  updatedAt: "2026-07-20T01:00:00Z",
  storyboardVersionCount: 0,
  keyframeVersionCount: 0,
  videoVersionCount: 0,
};

describe("workflow project drawer", () => {
  it("renders a direct delete control and emits the selected workflow", async () => {
    const host = document.createElement("div");
    const handleDelete = vi.fn();
    const app = createApp(WorkflowProjectDrawer, {
      search: "",
      filter: "all",
      workflows: [workflow],
      filteredWorkflows: [workflow],
      selectedWorkflowId: "",
      loading: false,
      loadingMore: false,
      refreshing: false,
      hasMore: false,
      busyActionKey: "",
      completionPercentage: () => 0,
      onDelete: handleDelete,
    });

    app.mount(host);
    await nextTick();

    expect(host.querySelector(".workflow-nav-item__title")?.textContent).toBe(workflow.title);
    expect(host.querySelector(".workflow-more-menu__trigger")).toBeNull();

    const deleteButton = host.querySelector<HTMLButtonElement>(".workflow-nav-item__delete");
    expect(deleteButton?.getAttribute("title")).toBe("删除");
    deleteButton?.click();
    expect(handleDelete).toHaveBeenCalledWith(workflow);

    app.unmount();
  });
});
