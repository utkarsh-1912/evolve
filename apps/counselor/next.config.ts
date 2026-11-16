import type { NextConfig } from "next";
import path from "node:path";

// Same setup as apps/citizen (DECISIONS #29): the `next-intl/config` alias is wired directly instead of
// `next-intl/plugin`, because the plugin eagerly requires @swc/core whose native addon is blocked on this machine.
const ROOT = path.join(__dirname, "..", "..");

// API base URL (same rule as lib/api.ts): NEXT_PUBLIC_API at build; unset => http://localhost:8000; "mock" => none.
const RAW_API = process.env.NEXT_PUBLIC_API?.trim();
const API_ORIGIN = RAW_API === "mock" ? "" : (RAW_API || "http://localhost:8000").replace(/\/$/, "");

// Security headers (docs/09 §7). Next injects inline bootstrap scripts, so script-src keeps 'unsafe-inline'
// until nonces land for all three apps (DECISIONS #44 (3)); everything else is locked down.
const csp = [
  "default-src 'self'",
  "script-src 'self' 'unsafe-inline'",
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data: blob:",
  "font-src 'self'",
  `connect-src 'self' ${API_ORIGIN}`.trim(),
  "frame-ancestors 'none'",
  "base-uri 'self'",
  "form-action 'self'",
  "object-src 'none'",
].join("; ");

const nextConfig: NextConfig = {
  // Separate output for the live-backend e2e build (NEXT_PUBLIC_API set), so it never overwrites the mock build.
  distDir: process.env.NEXT_DIST_DIR ?? ".next",
  // Opt-in self-contained server for Docker images (NEXT_OUTPUT=standalone); traced from the monorepo root.
  output: process.env.NEXT_OUTPUT === "standalone" ? "standalone" : undefined,
  outputFileTracingRoot: ROOT,
  transpilePackages: ["@evolve/ui"],
  turbopack: {
    root: ROOT,
    resolveAlias: { "next-intl/config": "./i18n/request.ts" },
  },
  webpack: (config) => {
    config.resolve.alias["next-intl/config"] = path.resolve(__dirname, "i18n/request.ts");
    return config;
  },
  poweredByHeader: false,
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          { key: "Content-Security-Policy", value: csp },
          { key: "Referrer-Policy", value: "no-referrer" },
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "X-Frame-Options", value: "DENY" },
          { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=(), interest-cohort=()" },
        ],
      },
    ];
  },
};

export default nextConfig;
