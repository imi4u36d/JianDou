import { describe, expect, it } from "vitest";
import { installPageZoomGuard } from "@/utils/page-zoom";

function dispatchCancelable(target: EventTarget, event: Event): boolean {
  return target.dispatchEvent(event);
}

describe("installPageZoomGuard", () => {
  it("prevents browser zoom keyboard shortcuts", () => {
    const cleanup = installPageZoomGuard(window, document);
    const event = new KeyboardEvent("keydown", {
      key: "=",
      ctrlKey: true,
      cancelable: true,
    });

    expect(dispatchCancelable(window, event)).toBe(false);
    expect(event.defaultPrevented).toBe(true);

    cleanup();
  });

  it("allows regular keyboard shortcuts", () => {
    const cleanup = installPageZoomGuard(window, document);
    const event = new KeyboardEvent("keydown", {
      key: "s",
      ctrlKey: true,
      cancelable: true,
    });

    expect(dispatchCancelable(window, event)).toBe(true);
    expect(event.defaultPrevented).toBe(false);

    cleanup();
  });

  it("prevents trackpad and mouse wheel zoom gestures", () => {
    const cleanup = installPageZoomGuard(window, document);
    const event = new WheelEvent("wheel", {
      ctrlKey: true,
      cancelable: true,
    });

    expect(dispatchCancelable(window, event)).toBe(false);
    expect(event.defaultPrevented).toBe(true);

    cleanup();
  });

  it("prevents multi-touch page zoom", () => {
    const cleanup = installPageZoomGuard(window, document);
    const event = new Event("touchmove", { cancelable: true });
    Object.defineProperty(event, "touches", { value: [{}, {}] });

    expect(dispatchCancelable(document, event)).toBe(false);
    expect(event.defaultPrevented).toBe(true);

    cleanup();
  });

  it("prevents Safari gesture zoom events", () => {
    const cleanup = installPageZoomGuard(window, document);
    const event = new Event("gesturestart", { cancelable: true });

    expect(dispatchCancelable(document, event)).toBe(false);
    expect(event.defaultPrevented).toBe(true);

    cleanup();
  });
});
