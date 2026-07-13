import { afterEach, describe, expect, it } from "vitest";
import {
  closeOpenWorkflowMenus,
  positionWorkflowVersionMenu,
} from "@/composables/workflow/useStageWorkflowInteractions";

describe("stage workflow interactions", () => {
  afterEach(() => {
    document.body.innerHTML = "";
  });

  it("positions a version popover within the viewport", () => {
    const trigger = document.createElement("button");
    trigger.setAttribute("popovertarget", "version-menu");
    trigger.getBoundingClientRect = () => ({
      bottom: 120, height: 20, left: 100, right: 220, top: 100, width: 120,
      x: 100, y: 100, toJSON: () => ({}),
    });
    const popover = document.createElement("div");
    popover.id = "version-menu";
    Object.defineProperty(popover, "offsetWidth", { value: 164 });
    Object.defineProperty(popover, "offsetHeight", { value: 92 });
    document.body.append(trigger, popover);

    positionWorkflowVersionMenu({ newState: "open", target: popover } as unknown as ToggleEvent);

    expect(popover.style.left).toBe("56px");
    expect(popover.style.top).toBe("124px");
  });

  it("closes unrelated details menus while preserving the active one", () => {
    const active = document.createElement("details");
    const activeButton = document.createElement("button");
    active.className = "workflow-more-menu";
    active.open = true;
    active.append(activeButton);
    const other = document.createElement("details");
    other.className = "workflow-more-menu";
    other.open = true;
    document.body.append(active, other);

    closeOpenWorkflowMenus(activeButton);

    expect(active.open).toBe(true);
    expect(other.open).toBe(false);
  });
});
