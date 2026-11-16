import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

// Same rule set as the apps (React hooks, jsx-a11y, typescript-eslint). No `any` in packages/ui (docs/09 §7).
export default defineConfig([
  ...nextVitals,
  ...nextTs,
  {
    rules: {
      "@next/next/no-html-link-for-pages": "off",
      "@next/next/no-img-element": "off",
      "@typescript-eslint/no-explicit-any": "error",
    },
  },
  globalIgnores(["node_modules/**"]),
]);
