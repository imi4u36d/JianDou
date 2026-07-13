import { describe, expect, it, vi } from "vitest";
import { useCreditManagement } from "@/admin/composables/useCreditManagement";
import {
  adminTransactionTypeLabel,
  formatCreditDateTime,
  formatSignedCreditAmount,
  transactionTagType,
} from "@/admin/features/credits/credit-management-presenters";
import type { AdminCreditRule, AdminCreditUser } from "@/types";

const user = (balance = 50): AdminCreditUser => ({
  id: 7,
  username: "tester",
  balance,
  totalConsumed: 0,
  totalAdjusted: balance - 50,
  imageGenerationCount: 0,
  videoGenerationCount: 0,
});

const rule = (cost = 10): AdminCreditRule => ({
  id: 1,
  featureCode: "IMAGE_GENERATION",
  displayName: "图片生成",
  cost,
});

function harness() {
  const api = {
    fetchUsers: vi.fn(async () => [user()]),
    fetchRules: vi.fn(async () => [rule()]),
    fetchTransactions: vi.fn(async () => []),
    adjustUser: vi.fn(async () => user(70)),
    updateRule: vi.fn(async () => rule(15)),
  };
  const message = { success: vi.fn(), warning: vi.fn(), error: vi.fn() };
  return { api, message, state: useCreditManagement({ api, message, loadOnMount: false }) };
}

describe("credit management", () => {
  it("loads the active resource and reports failures in page state", async () => {
    const { api, state } = harness();
    await state.loadCreditUsers();
    expect(api.fetchUsers).toHaveBeenCalledWith({ q: "" });
    expect(state.creditUsers.value).toHaveLength(1);

    api.fetchRules.mockRejectedValueOnce(new Error("rules unavailable"));
    state.activeTab.value = "rules";
    await state.refreshActiveTab();
    expect(state.ruleErrorMessage.value).toBe("rules unavailable");
    expect(state.loadingRules.value).toBe(false);
  });

  it("validates and applies an account adjustment in place", async () => {
    const { api, message, state } = harness();
    await state.loadCreditUsers();
    state.openAdjustDialog(state.creditUsers.value[0]);

    await state.submitAdjustment();
    expect(message.warning).toHaveBeenCalledWith("调整数量不能为 0");

    state.adjustForm.amount = 20;
    state.adjustForm.reason = " correction ";
    await state.submitAdjustment();
    expect(api.adjustUser).toHaveBeenCalledWith(7, { amount: 20, reason: "correction" });
    expect(state.creditUsers.value[0].balance).toBe(70);
    expect(state.adjustDialogVisible.value).toBe(false);
  });

  it("updates a selected rule and keeps display helpers deterministic", async () => {
    const { api, state } = harness();
    await state.loadCreditRules();
    state.openRuleDialog(state.creditRules.value[0]);
    state.ruleForm.cost = 15;
    await state.submitRule();

    expect(api.updateRule).toHaveBeenCalledWith("IMAGE_GENERATION", { cost: 15 });
    expect(state.creditRules.value[0].cost).toBe(15);
    expect(formatCreditDateTime("invalid")).toBe("未记录");
    expect(formatSignedCreditAmount(3)).toBe("+3");
    expect(adminTransactionTypeLabel("REFUND")).toBe("退回");
    expect(transactionTagType(-1)).toBe("warning");
  });
});
