import type { NextConfig } from "next";
import path from "node:path";

// Same setup as apps/citizen. next-intl: the `next-intl/config` alias is wired directly instead of `next-intl/plugin`,
// because the plugin eagerly requires @swc/core whose native addon is blocked on this machine (DECISIONS #29).
const ROOT = path.join(__dirname, "..", "..");
// The live guardrail feed and gate probe call the backend (CORS allows :3002, DECISIONS #38).
const API = process.env.NEXT_PUBLIC_API ?? "http://localhost:8000";

// Security headers (docs/09 §7). Next injects inline bootstrap scripts, so script-src keeps 'unsafe-inline'
// until the nonce work scheduled for all three apps (DECISIONS #44).
const csp = [
  "default-src 'self'",
  "script-src 'self' 'unsafe-inline'",
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data: blob:",
  "font-src 'self'",
  `connect-src 'self' ${API}`,
  "frame-ancestors 'none'",
  "base-uri 'self'",
  "form-action 'self'",
  "object-src 'none'",
].join("; ");

const nextConfig: NextConfig = {
  // Separate output dir lets a verification build run beside a live `next dev` (same pattern as citizen/counselor).
  distDir: process.env.NEXT_DIST_DIR ?? ".next",
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
