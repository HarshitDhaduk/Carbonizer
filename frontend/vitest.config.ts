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
        // Honest floor: the React component tree is exercised by Playwright +
        // axe-core (e2e/), not by vitest. The unit tests cover lib/ pure
        // functions + ui/ presentational primitives + store/ where the
        // value-per-test is high. Where we do test, branch coverage is
        // strong (74%); lines/statements are low because most code is
        // components without dedicated specs.
        // Lifting these requires adding component tests for Dashboard,
        // Insights, Profile, ConnectSources, Questionnaire — that's a
        // focused testing PR, not a side-effect of this gate.
        statements: 7,
        branches: 60,
        functions: 30,
        lines: 7,
      },
    },
  },
});
