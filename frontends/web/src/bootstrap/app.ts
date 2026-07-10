import { createApp } from "vue";

import App from "@/App.vue";
import { openAuthModal } from "@/auth/modal";
import { ensureAuthSession, installAuthClientBridge } from "@/auth/session";
import router from "@/router";
import { loadRuntimeConfig } from "@/api/runtime-config";
import { installPageZoomGuard } from "@/utils/page-zoom";
import { installAdminUiLoader } from "./admin-ui";

function installAuthenticationBridge(): void {
  installAuthClientBridge(() => {
    if (router.currentRoute.value.path === "/login" || router.currentRoute.value.path === "/activate") {
      return;
    }

    void openAuthModal({
      title: "登录后继续",
      message: "当前操作需要登录账号，请登录或使用邀请码注册。",
    });
  });
}

async function restoreAuthenticationSession(): Promise<void> {
  try {
    await ensureAuthSession();
  } catch {
    // Public pages must remain available while the API is temporarily unavailable.
  }
}

export async function bootstrapApplication(): Promise<void> {
  installPageZoomGuard();
  await loadRuntimeConfig();
  installAuthenticationBridge();
  await restoreAuthenticationSession();

  const app = createApp(App);
  installAdminUiLoader(app, router);
  app.use(router);

  await router.isReady();
  app.mount("#app");
}
