/** @type {import('tailwindcss').Config} 前端 Tailwind 配置 */
module.exports = {
  // 扫描入口文件以及所有 Vue / TS 源码中的类名。
  content: ["./index.html", "./src/**/*.{vue,ts}"],
  theme: {
    extend: {
      colors: {
        // 主要的深色文字与面板底色。
        ink: "#101724",
        // 用于抬升层级的中性色深色调。
        slate: "#1f2937",
        // 主品牌强调色，用于操作和高亮。
        accent: "#f97316",
        // 更亮的暖色强调，用于渐变和悬停态。
        ember: "#fb923c",
        // 柔和浅色中性调，用于边框和浅背景。
        mist: "#e2e8f0"
      },
      boxShadow: {
        // 玻璃卡片类面板默认阴影。
        panel: "0 24px 60px rgba(15, 23, 42, 0.18)"
      }
    }
  },
  // 当前未启用第三方 Tailwind 插件。
  plugins: []
};
