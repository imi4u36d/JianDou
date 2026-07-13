import { createApp, nextTick } from "vue";
import { describe, expect, it, vi } from "vitest";
import PromptTemplateGallery from "@/components/home/PromptTemplateGallery.vue";
import { promptTemplates } from "@/components/home/prompt-templates";

describe("prompt template gallery", () => {
  it("keeps a unique immutable-style catalog and emits the selected template", async () => {
    expect(promptTemplates).toHaveLength(10);
    expect(new Set(promptTemplates.map((item) => item.id)).size).toBe(promptTemplates.length);

    const onApply = vi.fn();
    const host = document.createElement("div");
    document.body.appendChild(host);
    const app = createApp(PromptTemplateGallery, { onApply });
    app.mount(host);

    host.querySelector<HTMLButtonElement>(".prompt-template-card")?.click();
    await nextTick();
    document.body.querySelector<HTMLButtonElement>(".prompt-template-preview__apply")?.click();
    await nextTick();

    expect(onApply).toHaveBeenCalledWith(promptTemplates[0]);

    app.unmount();
    host.remove();
  });
});
