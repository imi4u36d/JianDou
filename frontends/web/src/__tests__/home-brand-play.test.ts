import { createApp, nextTick } from "vue";
import { describe, expect, it } from "vitest";
import HomeBrandPlay from "@/views/home/components/HomeBrandPlay.vue";

describe("HomeBrandPlay", () => {
  it("maps composer state to animation classes", async () => {
    const host = document.createElement("div");
    const app = createApp(HomeBrandPlay, {
      focused: true,
      active: true,
      submitting: false,
    });
    app.mount(host);
    await nextTick();

    const brand = host.querySelector(".home-brand-play");
    expect(brand?.classList.contains("home-brand-play-focused")).toBe(true);
    expect(brand?.classList.contains("home-brand-play-active")).toBe(true);
    expect(brand?.classList.contains("home-brand-play-submitting")).toBe(false);
    expect(host.querySelectorAll(".home-brand-play__spark")).toHaveLength(8);
    expect(host.querySelectorAll(".home-brand-play__fall-dot")).toHaveLength(6);

    app.unmount();
  });
});
