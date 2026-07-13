import { createApp, nextTick } from "vue";
import { describe, expect, it, vi } from "vitest";
import MaterialFavoriteDialog from "@/views/materials/components/MaterialFavoriteDialog.vue";
import type { MaterialFavoriteCreateRequest } from "@/views/materials/components/material-favorite-dialog";

function mountDialog(onCreate = vi.fn()) {
  const host = document.createElement("div");
  document.body.append(host);
  const app = createApp(MaterialFavoriteDialog, {
    open: true,
    folders: [
      {
        id: "folder-1",
        name: "灵感",
        assetIds: [],
        createdAt: "2026-01-01T00:00:00Z",
      },
    ],
    asset: null,
    batchAssets: [],
    activeFolderIds: [],
    onCreate,
  });
  app.mount(host);
  return {
    unmount() {
      app.unmount();
      host.remove();
    },
  };
}

function buttonByText(text: string) {
  return Array.from(document.body.querySelectorAll<HTMLButtonElement>("button")).find(
    (button) => button.textContent?.trim() === text,
  );
}

describe("MaterialFavoriteDialog", () => {
  it("owns folder rename editing state", async () => {
    const wrapper = mountDialog();

    buttonByText("修改")?.click();
    await nextTick();

    const renameInput = document.body.querySelector<HTMLInputElement>('input[aria-label="收藏夹名称"]');
    expect(renameInput?.value).toBe("灵感");

    buttonByText("取消")?.click();
    await nextTick();
    expect(document.body.querySelector('input[aria-label="收藏夹名称"]')).toBeNull();
    wrapper.unmount();
  });

  it("clears the create form only after the parent reports success", async () => {
    const onCreate = vi.fn();
    const wrapper = mountDialog(onCreate);
    const input = document.body.querySelector<HTMLInputElement>('input[placeholder="输入收藏夹名称"]');
    if (!input) throw new Error("create input not rendered");
    input.value = "新收藏夹";
    input.dispatchEvent(new Event("input", { bubbles: true }));
    await nextTick();

    input.closest("form")?.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
    await nextTick();

    const request = onCreate.mock.calls[0]?.[0] as MaterialFavoriteCreateRequest;
    expect(request.name).toBe("新收藏夹");
    expect(input.value).toBe("新收藏夹");
    request.complete();
    await nextTick();
    expect(input.value).toBe("");
    wrapper.unmount();
  });
});
