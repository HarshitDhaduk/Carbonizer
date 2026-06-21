import { defineConfig } from "vitest/config";
import { fileURLToPath } from "node:url";
import path from "node:path";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

export default defineConfig({
  resolve: {
    // Match the @/ alias in tsconfig so imports work the same in tests as in source.
    alias: { "@": path.resolve(__dirname, "./src") },
  },
  // Use the React 17+ automatic JSX runtime so tests don't need a React import.
  // tsconfig.json keeps `jsx: "preserve"` for Next.js, which is fine for source;
  // vitest's esbuild needs an explicit jsx mode for .tsx tests.
  esbuild: { jsx: "automatic" },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./vitest.setup.ts"],
    css: false,
    include: ["src/**/*.{test,spec}.{ts,tsx}"],
    coverage: {
      provider: "v8",
      reporter: ["text", "html", "lcov"],
      include: ["src/**/*.{ts,tsx}"],
      exclude: [
        "src/**/*.{test,spec}.{ts,tsx}",
        "src/**/types.ts",
        "src/**/tokens.ts",
        "src/app/**/{layout,page,loading,error}.tsx",
      ],
      thresholds: {
        // Floor that we can lift as Phase 3 adds component tests for the
        // dashboard / questionnaire / connections trees. Anything lower
        // turns the coverage gate into theatre.
        statements: 30,
        branches: 60,
        functions: 50,
        lines: 30,
      },
    },
  },
});
