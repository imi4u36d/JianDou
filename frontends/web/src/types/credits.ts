export interface CreditRule {
  featureCode: string;
  displayName: string;
  cost: number;
  updatedAt?: string | null;
}

export interface CreditSummary {
  exempt: boolean;
  balance: number | null;
  totalConsumed?: number;
  totalAdjusted?: number;
  rules: CreditRule[];
}

export type CreditTransactionType = "ADJUST" | "CONSUME" | "USAGE" | "REFUND" | string;

export interface CreditTransaction {
  transactionId: string;
  userId: number;
  featureCode?: string | null;
  transactionType: CreditTransactionType;
  amountDelta: number;
  balanceBefore: number;
  balanceAfter: number;
  relatedRunId?: string | null;
  relatedTaskId?: string | null;
  relatedWorkflowId?: string | null;
  reason?: string | null;
  createdAt: string;
}

export interface CreditTransactionPage {
  items: CreditTransaction[];
  total: number;
  offset: number;
  limit: number;
}
