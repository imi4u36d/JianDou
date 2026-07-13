import { createApp, defineComponent, h, nextTick } from "vue";
import { describe, expect, it } from "vitest";
import { useWorkflowPreviewInteractions } from "@/views/unified/composables/useWorkflowPreviewInteractions";
import type { WorkflowCharacterSheet } from "@/types";

const sheet: WorkflowCharacterSheet = {
  id: "hero",
  characterName: "主角",
  appearanceSummary: "黑色风衣",
  characterIndex: 1,
  syntheticClipIndex: 1001,
  versions: [],
};

describe("workflow preview interactions", () => {
  it("owns failed-image and keyboard-dismiss state", async () => {
    let interactions: ReturnType<typeof useWorkflowPreviewInteractions> | undefined;
    const component = defineComponent({
      setup() {
        interactions = useWorkflowPreviewInteractions();
        return () => h("div");
      },
    });
    const host = document.createElement("div");
    const app = createApp(component);
    app.mount(host);

    interactions!.markPreviewImageFailed("/failed.png");
    expect(interactions!.isPreviewImageFailed("/failed.png")).toBe(true);
    expect(interactions!.isPreviewImageAvailable("/ok.png")).toBe(true);

    interactions!.openCharacterSummaryPreview(sheet);
    expect(interactions!.characterSummaryPreviewState).toMatchObject({
      open: true,
      title: "主角",
      content: "黑色风衣",
    });
    window.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" }));
    await nextTick();
    expect(interactions!.characterSummaryPreviewState.open).toBe(false);

    app.unmount();
  });
});
