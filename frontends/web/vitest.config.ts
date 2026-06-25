import { defineConfig } from "vitest/config";
import vue from "@vitejs/plugin-vue";
import { fileURLToPath, URL } from "node:url";

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
      "@jiandou/api": fileURLToPath(new URL("../../packages/api/src/index.ts", import.meta.url)),
      "@jiandou/api/generated": fileURLToPath(new URL("../../packages/api/src/generated/index.ts", import.meta.url)),
      "@jiandou/domain": fileURLToPath(new URL("../../packages/domain/src/index.ts", import.meta.url)),
      "@jiandou/ui": fileURLToPath(new URL("../../packages/ui/src/index.ts", import.meta.url)),
    },
  },
  test: {
    api: false,
    globals: true,
    environment: "jsdom",
    include: ["src/**/*.{test,spec}.{ts,tsx}"],
    coverage: {
      provider: "v8",
      reporter: ["text", "lcov"],
      include: ["src/**/*.{ts,vue}"],
      exclude: [
        "src/**/*.d.ts",
        "src/**/*.{test,spec}.{ts,tsx}",
        "src/main.ts",
        "src/router/index.ts",
      ],
    },
  },
});
