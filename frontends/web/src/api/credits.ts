/**
 * 用户积分相关 API 请求封装。
 */
import { getJson } from "./client";
import type { CreditSummary } from "@/types";

export function fetchCreditSummary() {
  return getJson<CreditSummary>("/auth/credits");
}
