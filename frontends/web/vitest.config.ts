import { defineConfig, mergeConfig } from "vitest/config";
import viteConfig from "./vite.config";

export default mergeConfig(
  viteConfig,
  defineConfig({
    test: {
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
  }),
);
