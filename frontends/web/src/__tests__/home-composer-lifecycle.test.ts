import { createApp, h, nextTick, ref } from "vue";
import { describe, expect, it, vi } from "vitest";
import { useHomeComposerLifecycle } from "@/composables/home/useHomeComposerLifecycle";
import type { ReferenceImageItem } from "@/composables/home/useReferenceImages";

describe("home composer lifecycle", () => {
  it("synchronizes editor state and owns global menu listeners", async () => {
    const host = document.createElement("div");
    document.body.appendChild(host);
    const activeMenu = ref<"" | "mention">("mention");
    const referenceImages = ref<ReferenceImageItem[]>([]);
    const referenceImagesBridge = ref<ReferenceImageItem[]>([]);
    const renderPromptEditor = vi.fn();
    const loadCredits = vi.fn();
    const dismissTaskToast = vi.fn();
    const app = createApp({
      setup() {
        useHomeComposerLifecycle({
          activeMenu,
          statusText: ref("加载参数"),
          referenceImages,
          referenceImagesBridge,
          promptText: ref("hello"),
          promptEditor: ref<HTMLElement | null>(null),
          composingPrompt: ref(false),
          syncingPromptFromEditor: ref(false),
          authenticated: () => false,
          renderPromptEditor,
          loadOptions: async () => undefined,
          loadCredits,
          dismissTaskToast,
        });
        return () => h("div", { class: "home-menu" }, "menu");
      },
    });

    app.mount(host);
    await nextTick();
    expect(renderPromptEditor).toHaveBeenCalledWith("hello");
    expect(loadCredits).toHaveBeenCalledOnce();

    host.querySelector(".home-menu")?.dispatchEvent(new PointerEvent("pointerdown", { bubbles: true }));
    expect(activeMenu.value).toBe("mention");
    document.body.dispatchEvent(new PointerEvent("pointerdown", { bubbles: true }));
    expect(activeMenu.value).toBe("");

    referenceImages.value = [{ id: "ref-1" } as ReferenceImageItem];
    await nextTick();
    expect(referenceImagesBridge.value).toEqual(referenceImages.value);

    app.unmount();
    expect(dismissTaskToast).toHaveBeenCalledOnce();
    host.remove();
  });
});
