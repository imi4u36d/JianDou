/* eslint-disable vue/one-component-per-file */
import { createApp, defineComponent, h, nextTick } from "vue";
import { describe, expect, it, vi } from "vitest";
import { normalizeAuthRedirectTarget } from "@/auth/redirect";
import AuthStandaloneForm from "@/components/auth/AuthStandaloneForm.vue";

describe("auth redirect targets", () => {
  it("accepts local paths and rejects external or protocol-relative targets", () => {
    expect(normalizeAuthRedirectTarget("/workflow/1", "/image-tasks")).toBe("/workflow/1");
    expect(normalizeAuthRedirectTarget("//evil.example", "/image-tasks")).toBe("/image-tasks");
    expect(normalizeAuthRedirectTarget("https://evil.example", "/admin")).toBe("/admin");
  });
});

describe("auth standalone form", () => {
  it("renders activation fields and emits immutable field updates", async () => {
    Object.defineProperty(window, "matchMedia", {
      configurable: true,
      value: vi.fn(() => ({
        matches: true,
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
      })),
    });
    const updateCode = vi.fn();
    const updateUsername = vi.fn();
    const updatePassword = vi.fn();
    const submit = vi.fn();
    const host = document.createElement("div");
    const app = createApp({
      render: () => h(AuthStandaloneForm, {
        title: "激活账号",
        subtitle: "创建账号",
        showCode: true,
        code: "ABC",
        username: "alice",
        password: "password123",
        submitting: false,
        submitLabel: "激活",
        submittingLabel: "激活中",
        footerLabel: "登录",
        footerTo: "/login",
        "onUpdate:code": updateCode,
        "onUpdate:username": updateUsername,
        "onUpdate:password": updatePassword,
        onSubmit: submit,
      }),
    });
    app.component("RouterLink", defineComponent({
      setup(_, { slots }) { return () => h("a", slots.default?.()); },
    }));
    app.mount(host);

    const inputs = host.querySelectorAll("input");
    expect(inputs).toHaveLength(3);
    inputs[0].value = "XYZ";
    inputs[0].dispatchEvent(new Event("input", { bubbles: true }));
    inputs[1].value = "bob";
    inputs[1].dispatchEvent(new Event("input", { bubbles: true }));
    inputs[2].value = "new-password";
    inputs[2].dispatchEvent(new Event("input", { bubbles: true }));
    (host.querySelector(".auth-form__password-toggle") as HTMLButtonElement).click();
    (host.querySelector("form") as HTMLFormElement).dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
    await nextTick();

    expect(updateCode).toHaveBeenCalledWith("XYZ");
    expect(updateUsername).toHaveBeenCalledWith("bob");
    expect(updatePassword).toHaveBeenCalledWith("new-password");
    expect(inputs[2].type).toBe("text");
    expect(submit).toHaveBeenCalledOnce();
    app.unmount();
  });
});
