/**
 * 全局登录弹窗状态。
 */
import { reactive } from "vue";
import { ensureAuthSession, useAuthSessionState } from "@/auth/session";

type AuthDialogMode = "login" | "register";

interface AuthModalState {
  open: boolean;
  mode: AuthDialogMode;
  title: string;
  message: string;
  pendingResolvers: Array<(value: boolean) => void>;
}

const state = reactive<AuthModalState>({
  open: false,
  mode: "login",
  title: "登录后继续",
  message: "当前操作需要登录账号。",
  pendingResolvers: [],
});

const authState = useAuthSessionState();

export function openAuthModal(options?: {
  mode?: AuthDialogMode;
  title?: string;
  message?: string;
}) {
  state.mode = options?.mode ?? "login";
  state.title = options?.title ?? "登录后继续";
  state.message = options?.message ?? "当前操作需要登录账号。";
  state.open = true;
  return new Promise<boolean>((resolve) => {
    state.pendingResolvers.push(resolve);
  });
}

export async function requireAuth(options?: {
  title?: string;
  message?: string;
}) {
  const session = await ensureAuthSession().catch(() => authState.session.value);
  if (session.authenticated) {
    return true;
  }
  return openAuthModal(options);
}

export function closeAuthModal(success = false) {
  state.open = false;
  const resolvers = state.pendingResolvers.splice(0);
  for (const resolve of resolvers) {
    resolve(success);
  }
}

export function switchAuthModalMode(mode: AuthDialogMode) {
  state.mode = mode;
}

export function useAuthModalState() {
  return state;
}
