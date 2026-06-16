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

  // Lazy register Element Plus — only loaded when visiting admin routes.
  let epRegistered = false;
  router.beforeEach(async (to) => {
    if (to.path.startsWith("/admin") && !epRegistered) {
      epRegistered = true;
      await Promise.all([
        import("element-plus/dist/index.css"),
        (async () => {
          const [{ default: ElementPlus }, { default: zhCn }, icons] = await Promise.all([
            import("element-plus"),
            import("element-plus/es/locale/lang/zh-cn"),
            import("@element-plus/icons-vue"),
          ]);
          app.use(ElementPlus, { locale: zhCn, size: "small" });
          for (const [key, component] of Object.entries(icons)) {
            app.component(key, component);
          }
        })(),
      ]);
    }
  });

  app.use(router);
  await router.isReady();
  app.mount("#app");
}

bootstrap();
