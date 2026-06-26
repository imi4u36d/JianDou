import { reactive } from "vue";
import type { CreditSummary } from "@/types";

const state = reactive<{
  open: boolean;
  initialSummary: CreditSummary | null;
}>({
  open: false,
  initialSummary: null,
});

export function openCreditDetailsDialog(summary?: CreditSummary | null) {
  state.initialSummary = summary ?? null;
  state.open = true;
}

export function useCreditDialogState() {
  return state;
}
