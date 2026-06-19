import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import { fileURLToPath, URL } from "node:url";

// 允许在 Docker 或本地开发环境中把代理指向非默认后端地址。
const apiProxyTarget = process.env.VITE_API_PROXY_TARGET ?? "http://127.0.0.1:8100";

export default defineConfig({
  // 启用 Vue 单文件组件支持。
  plugins: [vue()],
  resolve: {
    alias: {
      // 使用 @/ 作为 src 目录的统一别名。
      "@": fileURLToPath(new URL("./src", import.meta.url)),
      "@jiandou/api": fileURLToPath(new URL("../../packages/api/src/index.ts", import.meta.url)),
      "@jiandou/api/generated": fileURLToPath(new URL("../../packages/api/src/generated/index.ts", import.meta.url)),
      "@jiandou/domain": fileURLToPath(new URL("../../packages/domain/src/index.ts", import.meta.url)),
      "@jiandou/ui": fileURLToPath(new URL("../../packages/ui/src/index.ts", import.meta.url))
    }
  },
  server: {
    // 监听所有网卡，方便 Docker 和局域网调试访问。
    host: "0.0.0.0",
    port: 5173,
    proxy: {
      // 开发期将 API 请求代理到后端服务（统一 v2）。
      "/api/v3": {
        target: apiProxyTarget,
        changeOrigin: true
      },
      // 生成资源访问同样代理到后端服务。
      "/storage": {
        target: apiProxyTarget,
        changeOrigin: true
      }
    }
  }
});
