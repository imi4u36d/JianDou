import { ApiClientError } from "@/api/client";

const INSUFFICIENT_CREDIT_MESSAGE = "积分不足，请联系管理员充值";

function asRecord(value: unknown): Record<string, unknown> | null {
  return value && typeof value === "object" ? value as Record<string, unknown> : null;
}

function readCreditDetailValue(details: Record<string, unknown>, key: string) {
  const value = details[key];
  return typeof value === "number" || typeof value === "string" ? String(value) : "";
}

export function formatApiErrorMessage(error: unknown, fallback: string) {
  if (error instanceof ApiClientError && (error.code === "insufficient_credits" || error.status === 402)) {
    const payload = asRecord(error.payload);
    const details = asRecord(payload?.details);
    const available = details ? readCreditDetailValue(details, "available") : "";
    const required = details ? readCreditDetailValue(details, "required") : "";
    if (available || required) {
      const parts = [
        available ? `可用 ${available}` : "",
        required ? `需要 ${required}` : "",
      ].filter(Boolean);
      return `${INSUFFICIENT_CREDIT_MESSAGE}（${parts.join("，")}）`;
    }
    return INSUFFICIENT_CREDIT_MESSAGE;
  }
  return error instanceof Error ? error.message : fallback;
}
