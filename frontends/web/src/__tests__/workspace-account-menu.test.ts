import { createApp, nextTick } from "vue";
import { createMemoryHistory, createRouter } from "vue-router";
import { describe, expect, it } from "vitest";
import { clearAuthSession } from "@/auth/session";
import WorkspaceAccountMenu from "@/components/layout/WorkspaceAccountMenu.vue";

describe("workspace account menu", () => {
  it("renders anonymous state and closes on an outside pointer event", async () => {
    clearAuthSession();
    const host = document.createElement("div");
    document.body.append(host);
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: "/", component: { template: "<div />" } },
        { path: "/login", component: { template: "<div />" } },
      ],
    });
    await router.push("/");
    await router.isReady();
    const app = createApp(WorkspaceAccountMenu);
    app.use(router);
    app.mount(host);
    await nextTick();

    expect(host.textContent).toContain("--");
    expect(host.textContent).toContain("JD");
    host.querySelector<HTMLButtonElement>('button[aria-label="用户信息"]')?.click();
    await nextTick();
    expect(host.textContent).toContain("未登录");
    expect(host.textContent).toContain("登录");

    document.body.dispatchEvent(new PointerEvent("pointerdown", { bubbles: true }));
    await nextTick();
    expect(host.textContent).not.toContain("未登录");

    app.unmount();
    host.remove();
  });
});
