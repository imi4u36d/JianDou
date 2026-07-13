import { describe, expect, it } from "vitest";
import {
  featureLabel,
  formatDateTime,
  formatNumber,
  formatSignedNumber,
  transactionTypeLabel,
} from "@/features/credits/credit-details-presenters";

describe("credit detail presenters", () => {
  it("formats balances and signed deltas without redundant decimals", () => {
    expect(formatNumber(12)).toBe("12");
    expect(formatNumber(12.5)).toBe("12.5");
    expect(formatSignedNumber(3.25)).toBe("+3.25");
    expect(formatSignedNumber(-2)).toBe("-2");
  });

  it("maps transaction and feature codes to user-facing labels", () => {
    expect(featureLabel("image_generation")).toBe("图片生成");
    expect(featureLabel("VIDEO_GENERATION")).toBe("视频生成");
    expect(transactionTypeLabel("CONSUME")).toBe("消耗");
    expect(transactionTypeLabel("REFUND")).toBe("退还");
  });

  it("keeps empty and invalid timestamps readable", () => {
    expect(formatDateTime()).toBe("--");
    expect(formatDateTime("not-a-date")).toBe("not-a-date");
  });
});
