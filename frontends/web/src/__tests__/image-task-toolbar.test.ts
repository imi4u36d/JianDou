import { createApp, nextTick } from "vue";
import { describe, expect, it, vi } from "vitest";
import ImageTaskToolbar from "@/views/image-tasks/components/ImageTaskToolbar.vue";

describe("image task toolbar", () => {
  it("updates search and status filters from the page header controls", async () => {
    const host = document.createElement("div");
    const updateSearchText = vi.fn();
    const updateStatusFilter = vi.fn();
    const app = createApp(ImageTaskToolbar, {
      loading: false,
      loadingMore: false,
      refreshing: false,
      searchText: "portrait",
      statusFilter: "all",
      "onUpdate:searchText": updateSearchText,
      "onUpdate:statusFilter": updateStatusFilter,
    });
    app.mount(host);
    await nextTick();

    host.querySelector<HTMLButtonElement>(".image-task-search-field__clear")?.click();
    const completed = Array.from(host.querySelectorAll<HTMLButtonElement>(".image-task-filter-chip")).find(
      (button) => button.textContent?.trim() === "已完成",
    );
    completed?.click();

    const select = host.querySelector<HTMLSelectElement>(".image-task-status-select select");
    if (select) {
      select.value = "failed";
      select.dispatchEvent(new Event("change"));
    }

    expect(updateSearchText).toHaveBeenCalledWith("");
    expect(updateStatusFilter).toHaveBeenCalledWith("completed");
    expect(updateStatusFilter).toHaveBeenCalledWith("failed");
    app.unmount();
  });
});
