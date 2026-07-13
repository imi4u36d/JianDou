export function formatCreditDateTime(value?: string | null) {
  if (!value) return "未记录";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "未记录" : date.toLocaleString("zh-CN");
}

export function formatSignedCreditAmount(value: number) {
  return value > 0 ? `+${value}` : `${value}`;
}

export function adminTransactionTypeLabel(type: string) {
  const labels: Record<string, string> = {
    ADJUST: "管理员调整",
    CONSUME: "功能消耗",
    USAGE: "功能使用",
    REFUND: "退回",
  };
  return labels[type] ?? (type || "-");
}

export function transactionTagType(amountDelta: number) {
  return amountDelta >= 0 ? "success" : "warning";
}
