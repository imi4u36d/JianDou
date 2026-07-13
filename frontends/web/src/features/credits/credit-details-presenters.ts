import type { CreditTransactionType } from "@/types";

export function formatNumber(value: number | null | undefined) {
  const numeric = Number(value ?? 0);
  return Number.isInteger(numeric) ? String(numeric) : numeric.toFixed(2).replace(/\.?0+$/, "");
}

export function formatSignedNumber(value: number) {
  if (value > 0) {
    return `+${formatNumber(value)}`;
  }
  return formatNumber(value);
}

export function formatDateTime(value?: string | null) {
  if (!value) {
    return "--";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function featureLabel(value?: string | null) {
  const normalized = String(value ?? "").trim().toUpperCase();
  if (normalized === "IMAGE_GENERATION") {
    return "图片生成";
  }
  if (normalized === "VIDEO_GENERATION") {
    return "视频生成";
  }
  return normalized || "--";
}

export function transactionTypeLabel(value: CreditTransactionType) {
  const normalized = String(value ?? "").trim().toUpperCase();
  if (normalized === "CONSUME") {
    return "消耗";
  }
  if (normalized === "USAGE") {
    return "使用";
  }
  if (normalized === "REFUND") {
    return "退还";
  }
  if (normalized === "ADJUST") {
    return "调整";
  }
  return normalized || "--";
}
