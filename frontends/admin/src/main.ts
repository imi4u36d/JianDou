import { createApp } from "vue";
import ElementPlus from "element-plus";
import zhCn from "element-plus/es/locale/lang/zh-cn";
import * as ElementPlusIconsVue from "@element-plus/icons-vue";
import App from "./App.vue";
import router from "./router";
import "./styles/main.css";
import "element-plus/dist/index.css";
import { loadRuntimeConfig } from "./api/runtime-config";
import { ensureAuthSession, installAuthClientBridge } from "./auth/session";

function normalizeRedirectTarget(value: unknown) {
  if (typeof value !== "string" || !value.startsWith("/") || value.startsWith("//")) {
    return "/";
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
    // Allow login page to render when API is temporarily unavailable.
  }

  const app = createApp(App);
  for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
    app.component(key, component);
  }
  app.use(ElementPlus, {
    locale: zhCn,
    size: "small"
  });
  app.use(router);
  await router.isReady();
  app.mount("#app");
}

bootstrap();
