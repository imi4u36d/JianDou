/* eslint-disable vue/one-component-per-file -- each case mounts the same production component */
import { createApp, nextTick } from "vue";
import { afterEach, describe, expect, it, vi } from "vitest";
import AppSelect from "@/components/common/AppSelect.vue";

describe("AppSelect", () => {
  afterEach(() => {
    document.body.innerHTML = "";
    vi.restoreAllMocks();
  });

  it("opens its teleported menu and emits the selected value", async () => {
    Object.defineProperty(HTMLElement.prototype, "scrollIntoView", {
      configurable: true,
      value: vi.fn(),
    });
    const updates: unknown[] = [];
    const host = document.createElement("div");
    document.body.append(host);
    const app = createApp(AppSelect, {
      modelValue: "a",
      options: [
        { label: "Alpha", value: "a" },
        { label: "Beta", value: "b" },
      ],
      "onUpdate:modelValue": (value: unknown) => updates.push(value),
    });
    app.mount(host);

    host.querySelector<HTMLButtonElement>(".app-select__trigger")?.click();
    await nextTick();
    await nextTick();
    const options = document.body.querySelectorAll<HTMLButtonElement>(".app-select__option");
    options[1]?.click();
    await nextTick();

    expect(options).toHaveLength(2);
    expect(updates).toEqual(["b"]);
    expect(host.querySelector(".app-select__trigger")?.getAttribute("aria-expanded")).toBe("false");
    app.unmount();
  });

  it("skips disabled options during keyboard navigation", async () => {
    Object.defineProperty(HTMLElement.prototype, "scrollIntoView", {
      configurable: true,
      value: vi.fn(),
    });
    const updates: unknown[] = [];
    const host = document.createElement("div");
    document.body.append(host);
    const app = createApp(AppSelect, {
      modelValue: "a",
      options: [
        { label: "Alpha", value: "a" },
        { label: "Blocked", value: "b", disabled: true },
        { label: "Charlie", value: "c" },
      ],
      "onUpdate:modelValue": (value: unknown) => updates.push(value),
    });
    app.mount(host);

    host.querySelector<HTMLButtonElement>(".app-select__trigger")?.dispatchEvent(
      new KeyboardEvent("keydown", { key: "ArrowDown", bubbles: true }),
    );
    await nextTick();
    await nextTick();
    const menu = document.body.querySelector<HTMLElement>(".app-select__menu");
    menu?.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowDown", bubbles: true }));
    menu?.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
    await nextTick();

    expect(updates).toEqual(["c"]);
    app.unmount();
  });
});
