import nextPlugin from "@next/eslint-plugin-next";

// ESLint 9 flat config. Next 16 + ESLint 9 dropped legacy `.eslintrc` support
// and `next lint`; we now consume the plugin's flat-shipped `core-web-vitals`
// preset directly. Avoids FlatCompat's circular-reference bug with the
// transitively imported eslint-config-next/typescript shim.
export default [
  {
    ignores: [
      ".next/**",
      "node_modules/**",
      "out/**",
      "build/**",
      "coverage/**",
      "test-results/**",
      "playwright-report/**",
    ],
  },
  nextPlugin.configs["core-web-vitals"],
];
