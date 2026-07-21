import { createApp, nextTick } from "vue";
import { describe, expect, it } from "vitest";
import ImageTaskListPanel from "@/views/image-tasks/components/ImageTaskListPanel.vue";
import { calculateImageTaskPageSize } from "@/views/image-tasks/composables/useImageTaskListViewport";

describe("image task list panel", () => {
  it("calculates a bounded viewport page size", () => {
    expect(calculateImageTaskPageSize(500, 76, 8)).toBe(5);
    expect(calculateImageTaskPageSize(100, 76, 8)).toBe(4);
    expect(calculateImageTaskPageSize(-1, 0, 0)).toBe(4);
  });

  it("renders the filtered empty state", async () => {
    const host = document.createElement("div");
    const app = createApp(ImageTaskListPanel, {
      filteredItems: [],
      loading: false,
      loadingMore: false,
      hasMore: false,
      selectedId: "",
      filterActive: true,
    });
    app.mount(host);
    await nextTick();

    expect(host.textContent).toContain("没有匹配图片");
    app.unmount();
  });
});
