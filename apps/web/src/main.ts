import { createApp } from "vue";
import App from "./App.vue";
import router from "./router";
import "./styles/tailwind.css";
import { loadRuntimeConfig } from "./api/runtime-config";

async function bootstrap() {
  await loadRuntimeConfig();
  const app = createApp(App);
  app.use(router);
  await router.isReady();
  app.mount("#app");
}

bootstrap();
