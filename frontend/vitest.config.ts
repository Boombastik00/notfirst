import { resolve } from "path";
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  resolve: {
    // алиас @ из tsconfig путей next
    alias: {
      "@": resolve(__dirname, "src"),
    },
  },
  esbuild: {
    // тесты не проходят через свк next поэтому jsx раскрываем сами
    jsx: "automatic",
  },
  test: {
    environment: "happy-dom",
    globals: true,
    // смоук-тесты компонентов живут рядом с ними
    include: ["src/**/*.test.tsx"],
    setupFiles: ["./src/test-setup.ts"],
  },
});
