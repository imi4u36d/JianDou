/**
 * Web 客户端应用启动入口。
 */
import { createApp } from "vue";
import App from "./App.vue";
import router from "./router";
import "./styles/tailwind.css";
import { loadRuntimeConfig } from "./api/runtime-config";
import { ensureAuthSession, installAuthClientBridge } from "./auth/session";
import { openAuthModal } from "./auth/modal";

async function bootstrap() {
  await loadRuntimeConfig();
  installAuthClientBridge(() => {
    if (router.currentRoute.value.path === "/login" || router.currentRoute.value.path === "/activate") {
      return;
    }
    void openAuthModal({
      title: "登录后继续",
      message: "当前操作需要登录账号，请登录或使用邀请码注册。"
    });
  });
  try {
    await ensureAuthSession();
  } catch {
    // Allow the public landing page to render even when the API is temporarily unavailable.
  }
  const app = createApp(App);
  app.use(router);
  await router.isReady();
  app.mount("#app");
}

bootstrap();
