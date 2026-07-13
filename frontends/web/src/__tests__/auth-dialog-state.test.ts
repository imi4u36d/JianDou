import { createApp, defineComponent, h } from "vue";
import { describe, expect, it, vi } from "vitest";
import { useAuthDialog } from "@/components/auth/useAuthDialog";
import type { ActivateInviteRequest, AuthSession, LoginRequest } from "@/types";

describe("auth dialog state", () => {
  it("submits normalized form ownership through injected session ports", async () => {
    const session: AuthSession = { authenticated: true, user: null };
    const login = vi.fn(async (_payload: LoginRequest) => session);
    const activate = vi.fn(async (_payload: ActivateInviteRequest) => session);
    const close = vi.fn();
    const reportError = vi.fn();
    let state: ReturnType<typeof useAuthDialog> | undefined;
    const app = createApp(defineComponent({
      setup() {
        state = useAuthDialog({ login, activate, close, reportError });
        return () => h("div");
      },
    }));
    const host = document.createElement("div");
    app.mount(host);

    state!.loginForm.username = "tester";
    state!.loginForm.password = "secret";
    await state!.handleLogin();
    expect(login).toHaveBeenCalledWith({ username: "tester", password: "secret" });
    expect(close).toHaveBeenCalledWith(true);
    expect(state!.submitting.value).toBe(false);

    activate.mockRejectedValueOnce(new Error("invite expired"));
    await state!.handleRegister();
    expect(reportError).toHaveBeenCalledWith("invite expired");
    expect(state!.submitting.value).toBe(false);

    app.unmount();
  });
});
