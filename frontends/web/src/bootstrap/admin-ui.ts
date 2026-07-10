import type { App } from "vue";
import type { Router } from "vue-router";

export function installAdminUiLoader(app: App, router: Router): void {
  let registered = false;

  router.beforeEach(async (to) => {
    if (!to.path.startsWith("/admin") || registered) {
      return;
    }

    registered = true;
    await Promise.all([
      import("element-plus/dist/index.css"),
      import("@/admin/styles/main.css"),
      (async () => {
        const [{ default: ElementPlus }, { default: zhCn }, icons] = await Promise.all([
          import("element-plus"),
          import("element-plus/es/locale/lang/zh-cn"),
          import("@element-plus/icons-vue"),
        ]);

        app.use(ElementPlus, { locale: zhCn, size: "small" });
        for (const [name, component] of Object.entries(icons)) {
          app.component(name, component);
        }
      })(),
    ]);
  });
}
