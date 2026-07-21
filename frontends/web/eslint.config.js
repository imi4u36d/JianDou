import js from "@eslint/js";
import typescriptEslint from "@typescript-eslint/eslint-plugin";
import typescriptParser from "@typescript-eslint/parser";
import vue from "eslint-plugin-vue";
import vueParser from "vue-eslint-parser";
import prettier from "eslint-config-prettier";

export default [
  {
    ignores: [
      "dist/",
      "node_modules/",
      "static/",
      "*.d.ts",
      "src/views/HomeView.vue",
      "src/views/StageWorkflowView.vue",
      "src/views/TasksView.vue",
    ],
  },
  js.configs.recommended,
  ...vue.configs["flat/recommended"],
  prettier,
  {
    files: ["src/**/*.{ts,vue}"],
    languageOptions: {
      parser: vueParser,
      parserOptions: {
        parser: typescriptParser,
        ecmaVersion: "latest",
        sourceType: "module",
        extraFileExtensions: [".vue"],
      },
      globals: {
        console: "readonly",
        document: "readonly",
        localStorage: "readonly",
        navigator: "readonly",
        window: "readonly",
      },
    },
    plugins: {
      "@typescript-eslint": typescriptEslint,
    },
    rules: {
      ...typescriptEslint.configs.recommended.rules,
      "vue/multi-word-component-names": "off",
      "@typescript-eslint/no-unused-vars": ["warn", { argsIgnorePattern: "^_" }],
      "no-undef": "off",
      "no-console": ["warn", { allow: ["warn", "error"] }],
    },
  },
  {
    files: [
      "src/api/auth.ts",
      "src/api/credits.ts",
      "src/api/generation.ts",
      "src/api/health.ts",
      "src/api/material-assets.ts",
      "src/api/script.ts",
      "src/api/showcase.ts",
      "src/api/tasks.ts",
      "src/api/workflows.ts",
      "src/admin/api/**/*.ts",
      "src/auth/**/*.ts",
    ],
    rules: {
      "no-restricted-imports": [
        "error",
        {
          paths: [
            {
              name: "@/types",
              message: "Import contracts from a domain module such as @/types/tasks or @/types/auth.",
            },
          ],
        },
      ],
    },
  },
  {
    files: [
      "src/types/auth.ts",
      "src/types/credits.ts",
      "src/types/health.ts",
      "src/types/uploads.ts",
    ],
    rules: {
      "no-restricted-imports": [
        "error",
        {
          paths: [
            {
              name: "./index",
              message: "Owned contract modules must define their contracts instead of re-exporting the legacy barrel.",
            },
          ],
        },
      ],
    },
  },
];
