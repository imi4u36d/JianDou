import { getJson, postJson, putJson } from "./client";
import type {
  AdminCreditAdjustmentRequest,
  AdminCreditRule,
  AdminCreditRuleUpdateRequest,
  AdminCreditTransaction,
  AdminCreditUser,
  AdminCreditUserQuery
} from "@/types";

export async function fetchAdminCreditUsers(query?: AdminCreditUserQuery) {
  const params = new URLSearchParams();
  if (query?.q?.trim()) {
    params.set("q", query.q.trim());
  }
  const search = params.toString();
  return getJson<AdminCreditUser[]>(search ? `/admin/credits/users?${search}` : "/admin/credits/users");
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
  return putJson<AdminCreditRule>(`/admin/credits/rules/${encodeURIComponent(featureCode)}`, payload);
}
