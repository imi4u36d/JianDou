/**
 * 用户积分相关 API 请求封装。
 */
import { getJson } from "./client";
import type { CreditSummary, CreditTransactionPage } from "@/types";

export function fetchCreditSummary() {
  return getJson<CreditSummary>("/credits");
}

export function fetchCreditTransactions(query: { offset?: number; limit?: number } = {}) {
  const params = new URLSearchParams();
  if (typeof query.offset === "number") {
    params.set("offset", String(query.offset));
  }
  if (typeof query.limit === "number") {
    params.set("limit", String(query.limit));
  }
  const search = params.toString();
  return getJson<CreditTransactionPage>(search ? `/credits/transactions?${search}` : "/credits/transactions");
}
