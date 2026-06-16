import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import { fileURLToPath, URL } from "node:url";

const apiProxyTarget = process.env.VITE_API_PROXY_TARGET ?? "http://127.0.0.1:8000";

export default defineConfig({
  base: "/admin/",
  plugins: [vue()],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
      "@jiandou/api": fileURLToPath(new URL("../../packages/api/src/index.ts", import.meta.url)),
      "@jiandou/api/generated": fileURLToPath(new URL("../../packages/api/src/generated/index.ts", import.meta.url)),
      "@jiandou/domain": fileURLToPath(new URL("../../packages/domain/src/index.ts", import.meta.url)),
      "@jiandou/ui": fileURLToPath(new URL("../../packages/ui/src/index.ts", import.meta.url))
    }
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          "vue-vendor": ["vue", "vue-router"],
          "element-plus": ["element-plus", "@element-plus/icons-vue"]
        }
      }
    }
  },
  server: {
    host: "0.0.0.0",
    port: 5174,
    proxy: {
      "/api/v3": {
        target: apiProxyTarget,
        changeOrigin: true
      },
      "/storage": {
        target: apiProxyTarget,
        changeOrigin: true
      }
    }
  }
});
