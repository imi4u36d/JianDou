import { onBeforeUnmount, reactive } from "vue";

export interface ConfirmDialogOptions {
  title: string;
  message: string;
  confirmText?: string;
  cancelText?: string;
  tone?: "danger" | "primary";
}

export function useConfirmDialog() {
  let pendingResolve: ((value: boolean) => void) | null = null;

  const confirmDialog = reactive({
    open: false,
    title: "",
    message: "",
    confirmText: "确认",
    cancelText: "取消",
    tone: "danger" as "danger" | "primary",
  });

  function requestConfirm(options: ConfirmDialogOptions) {
    if (pendingResolve) {
      pendingResolve(false);
      pendingResolve = null;
    }
    confirmDialog.title = options.title;
    confirmDialog.message = options.message;
    confirmDialog.confirmText = options.confirmText ?? "确认";
    confirmDialog.cancelText = options.cancelText ?? "取消";
    confirmDialog.tone = options.tone ?? "danger";
    confirmDialog.open = true;
    return new Promise<boolean>((resolve) => {
      pendingResolve = resolve;
    });
  }

  function settleConfirm(value: boolean) {
    confirmDialog.open = false;
    pendingResolve?.(value);
    pendingResolve = null;
  }

  function acceptConfirm() {
    settleConfirm(true);
  }

  function cancelConfirm() {
    settleConfirm(false);
  }

  onBeforeUnmount(() => {
    settleConfirm(false);
  });

  return {
    confirmDialog,
    requestConfirm,
    acceptConfirm,
    cancelConfirm,
  };
}
