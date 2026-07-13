import { nextTick, onBeforeUnmount, reactive, ref, watch } from "vue";
import { activateInviteAndStoreSession, loginAndStoreSession } from "@/auth/session";
import { closeAuthModal, useAuthModalState } from "@/auth/modal";
import { messageApi } from "@/composables/useMessage";

interface AuthDialogDependencies {
  login?: typeof loginAndStoreSession;
  activate?: typeof activateInviteAndStoreSession;
  close?: typeof closeAuthModal;
  reportError?: (message: string) => void;
}

export function useAuthDialog(dependencies: AuthDialogDependencies = {}) {
  const login = dependencies.login ?? loginAndStoreSession;
  const activate = dependencies.activate ?? activateInviteAndStoreSession;
  const close = dependencies.close ?? closeAuthModal;
  const reportError = dependencies.reportError ?? messageApi.error;
  const modal = useAuthModalState();
  const submitting = ref(false);
  const showLoginPassword = ref(false);
  const showRegisterPassword = ref(false);
  const loginUsernameRef = ref<HTMLInputElement | null>(null);
  const registerCodeRef = ref<HTMLInputElement | null>(null);
  const loginForm = reactive({ username: "", password: "" });
  const registerForm = reactive({ code: "", username: "", password: "" });
  let returnFocusTarget: HTMLElement | null = null;

  function handleClose() {
    if (!submitting.value) close(false);
  }

  function restoreFocus() {
    const target = returnFocusTarget;
    returnFocusTarget = null;
    target?.focus({ preventScroll: true });
  }

  async function handleLogin() {
    submitting.value = true;
    try {
      await login({ username: loginForm.username, password: loginForm.password });
      close(true);
    } catch (error) {
      reportError(error instanceof Error ? error.message : "登录失败");
    } finally {
      submitting.value = false;
    }
  }

  async function handleRegister() {
    submitting.value = true;
    try {
      await activate({
        code: registerForm.code,
        username: registerForm.username,
        password: registerForm.password,
      });
      close(true);
    } catch (error) {
      reportError(error instanceof Error ? error.message : "注册失败");
    } finally {
      submitting.value = false;
    }
  }

  watch(
    () => [modal.open, modal.mode] as const,
    async ([open, mode], previous) => {
      const wasOpen = Boolean(previous?.[0]);
      showLoginPassword.value = false;
      showRegisterPassword.value = false;
      if (open && !wasOpen) {
        returnFocusTarget = document.activeElement instanceof HTMLElement
          ? document.activeElement
          : null;
      }
      if (open) {
        await nextTick();
        const input = mode === "register" ? registerCodeRef.value : loginUsernameRef.value;
        input?.focus({ preventScroll: true });
      } else {
        restoreFocus();
      }
    },
  );
  onBeforeUnmount(restoreFocus);

  return {
    modal,
    submitting,
    showLoginPassword,
    showRegisterPassword,
    loginUsernameRef,
    registerCodeRef,
    loginForm,
    registerForm,
    handleClose,
    handleLogin,
    handleRegister,
  };
}
