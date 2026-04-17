/**
 * 登录态单例状态。
 */
import { computed, reactive } from "vue";
import { activateInviteAccount, fetchAuthSession, loginByPassword, logoutSession } from "@/api/auth";
import { ApiClientError, setUnauthorizedHandler } from "@/api/client";
import type { ActivateInviteRequest, AuthSession, LoginRequest } from "@/types";

const anonymousSession: AuthSession = {
  authenticated: false,
  user: null
};

const state = reactive({
  ready: false,
  loading: false,
  session: { ...anonymousSession } as AuthSession
});

let pendingSessionPromise: Promise<AuthSession> | null = null;
let redirectToLoginHandler: ((path?: string) => void) | null = null;

function applySession(session: AuthSession) {
  state.session = session;
  state.ready = true;
  return session;
}

export function clearAuthSession() {
  return applySession({ ...anonymousSession });
}

export function installAuthClientBridge(handler: (path?: string) => void) {
  redirectToLoginHandler = handler;
  setUnauthorizedHandler(() => {
    clearAuthSession();
    redirectToLoginHandler?.();
  });
}

export async function ensureAuthSession(force = false) {
  if (state.ready && !force) {
    return state.session;
  }
  if (pendingSessionPromise && !force) {
    return pendingSessionPromise;
  }
  state.loading = true;
  pendingSessionPromise = fetchAuthSession()
    .then((session) => applySession(session))
    .catch((error) => {
      if (error instanceof ApiClientError && error.status === 401) {
        return clearAuthSession();
      }
      throw error;
    })
    .finally(() => {
      state.loading = false;
      pendingSessionPromise = null;
    });
  return pendingSessionPromise;
}

export async function refreshAuthSession() {
  return ensureAuthSession(true);
}

export async function loginAndStoreSession(payload: LoginRequest) {
  const session = await loginByPassword(payload);
  return applySession(session);
}

export async function activateInviteAndStoreSession(payload: ActivateInviteRequest) {
  const session = await activateInviteAccount(payload);
  return applySession(session);
}

export async function logoutAndClearSession() {
  try {
    await logoutSession();
  } finally {
    clearAuthSession();
  }
}

export function useAuthSessionState() {
  return {
    state,
    session: computed(() => state.session),
    user: computed(() => state.session.user),
    isAuthenticated: computed(() => state.session.authenticated),
    isAdmin: computed(() => state.session.user?.role === "ADMIN")
  };
}
