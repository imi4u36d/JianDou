import { describe, expect, it } from "vitest";
import {
  REFERENCE_ADD_CARD_OFFSET,
  referenceAddCardStyle,
  referenceExpandedStep,
  referencePreviewImageStyle,
  referenceUploadSceneStyle,
} from "@/composables/home/referenceImageLayout";

describe("reference image layout", () => {
  it("keeps collapsed stacks compact and hides overflow cards", () => {
    const style = referencePreviewImageStyle(5, 6, false);
    expect(style.left).toBe("26px");
    expect(style.opacity).toBe("0");
    expect(referenceUploadSceneStyle(6, false)).toBeUndefined();
  });

  it("lays expanded cards out with a deterministic projected step", () => {
    const step = referenceExpandedStep();
    const first = referencePreviewImageStyle(0, 3, true);
    const second = referencePreviewImageStyle(1, 3, true);
    expect(Number.parseInt(second.left) - Number.parseInt(first.left)).toBe(step);
    expect(referenceUploadSceneStyle(3, true)?.width).toBe(`${3 * step + 68}px`);
  });

  it("places the add card beside a single expanded reference", () => {
    expect(referenceAddCardStyle(1, true)).toEqual({
      left: `${REFERENCE_ADD_CARD_OFFSET}px`,
      top: "0px",
      bottom: "auto",
    });
  });
});
