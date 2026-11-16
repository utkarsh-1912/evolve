// Shared CSP pattern for all évolvé apps (DECISIONS #44 Q3; docs/09 §7). Server/edge-safe: no React, no DOM.
// Scripts: per-request nonce + 'strict-dynamic' (no 'unsafe-inline'). Styles keep 'unsafe-inline' because inline
// style ATTRIBUTES (Radix positioning, DetectionBar scaleX) cannot carry a nonce; no user content is ever styled inline.
// Usage (proxy.ts): const nonce = makeNonce(); const csp = buildCsp({ nonce, connectSrc: [apiOrigin], dev });
// then forward it on the request (x-nonce + Content-Security-Policy) and set it on the response.

export function makeNonce(): string {
  const bytes = new Uint8Array(16);
  crypto.getRandomValues(bytes);
  let s = "";
  bytes.forEach((b) => (s += String.fromCharCode(b)));
  return btoa(s);
}

export function buildCsp({ nonce, connectSrc = [], dev = false }: { nonce: string; connectSrc?: string[]; dev?: boolean }): string {
  return [
    "default-src 'self'",
    `script-src 'self' 'nonce-${nonce}' 'strict-dynamic'${dev ? " 'unsafe-eval'" : ""}`,
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data: blob:",
    "font-src 'self'",
    `connect-src 'self'${connectSrc.filter(Boolean).map((s) => ` ${s}`).join("")}${dev ? " ws:" : ""}`,
    "frame-ancestors 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "object-src 'none'",
  ].join("; ");
}

/** Other security headers shared by every app. */
export const SECURITY_HEADERS: ReadonlyArray<{ key: string; value: string }> = [
  { key: "Referrer-Policy", value: "no-referrer" },
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=(), interest-cohort=()" },
];
