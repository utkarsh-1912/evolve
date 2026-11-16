import type { NextConfig } from "next";
import path from "node:path";
import { SECURITY_HEADERS } from "../../packages/ui/src/csp";

// next-intl: the `next-intl/config` alias is wired directly instead of `next-intl/plugin`, because the plugin
// eagerly requires @swc/core whose native addon is blocked on this machine (ERR_SWC_NATIVE_CACHE). DECISIONS #29.
const ROOT = path.join(__dirname, "..", "..");

// Security headers (docs/09 §7): CSP with a per-request nonce is set in proxy.ts (@evolve/ui/csp); the
// remaining headers are static and shared across apps.
const nextConfig: NextConfig = {
  // Separate build dir for the live-backend build (NEXT_PUBLIC_API set) so it never overwrites the mock build.
  distDir: process.env.NEXT_DIST_DIR || ".next",
  transpilePackages: ["@evolve/ui"],
  experimental: { optimizePackageImports: ["@evolve/ui", "lucide-react", "@radix-ui/react-icons"] },
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
        headers: [...SECURITY_HEADERS],
      },
    ];
  },
};

export default nextConfig;
