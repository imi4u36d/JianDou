/**
 * 用户积分相关 API 请求封装。
 */
import type { CreditSummary, CreditTransactionPage } from "@/types/credits";

import { getJson } from "./client";
import { withQuery } from "./query";

export function fetchCreditSummary() {
  return getJson<CreditSummary>("/credits");
}

export function fetchCreditTransactions(query: { offset?: number; limit?: number } = {}) {
  return getJson<CreditTransactionPage>(
    withQuery("/credits/transactions", {
      offset: query.offset,
      limit: query.limit,
    }),
  );
}
