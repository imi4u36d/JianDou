/**
 * Web 客户端应用启动入口。
 */
import { createApp } from "vue";
import App from "./App.vue";
import router from "./router";
import "./styles/tailwind.css";
import { loadRuntimeConfig } from "./api/runtime-config";
import { ensureAuthSession, installAuthClientBridge } from "./auth/session";

function normalizeRedirectTarget(value: unknown) {
  if (typeof value !== "string" || !value.startsWith("/") || value.startsWith("//")) {
    return "/tasks";
  }
  return value;
}

async function bootstrap() {
  await loadRuntimeConfig();
  installAuthClientBridge((path) => {
    const currentPath = normalizeRedirectTarget(path ?? router.currentRoute.value.fullPath);
    if (router.currentRoute.value.path === "/login") {
      return;
    }
    void router.replace({
      path: "/login",
      query: {
        redirect: currentPath
      }
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
