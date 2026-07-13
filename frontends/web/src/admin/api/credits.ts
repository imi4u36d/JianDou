import type {
  AdminCreditAdjustmentRequest,
  AdminCreditRule,
  AdminCreditRuleUpdateRequest,
  AdminCreditTransaction,
  AdminCreditUser,
  AdminCreditUserQuery,
} from "@/types/admin";

import { getJson, patchJson, postJson } from "@/api/client";
import { withQuery } from "@/api/query";

export async function fetchAdminCreditUsers(query?: AdminCreditUserQuery) {
  return getJson<AdminCreditUser[]>(withQuery("/admin/credits/users", { q: query?.q }));
}

export async function fetchAdminCreditTransactions(userId: number) {
  return getJson<AdminCreditTransaction[]>(`/admin/credits/users/${userId}/transactions`);
}

export async function adjustAdminUserCredits(userId: number, payload: AdminCreditAdjustmentRequest) {
  return postJson<AdminCreditUser>(`/admin/credits/users/${userId}/adjust`, payload);
}

export async function fetchAdminCreditRules() {
  return getJson<AdminCreditRule[]>("/admin/credits/rules");
}

export async function updateAdminCreditRule(featureCode: string, payload: AdminCreditRuleUpdateRequest) {
  return patchJson<AdminCreditRule>(`/admin/credits/rules/${encodeURIComponent(featureCode)}`, payload);
}
