import createMiddleware from "next-intl/middleware";
import { NextResponse, type NextRequest } from "next/server";
import { buildCsp, makeNonce } from "@evolve/ui/csp";
import { routing } from "./i18n/routing";

// Locale routing (next-intl) + per-request CSP nonce (DECISIONS #44 Q3). Next applies the nonce to its own
// scripts when it finds it in the request's Content-Security-Policy header (pages render dynamically).
const intl = createMiddleware(routing);

export default function proxy(request: NextRequest) {
  const nonce = makeNonce();
  const csp = buildCsp({ nonce, connectSrc: [process.env.NEXT_PUBLIC_API ?? ""], dev: process.env.NODE_ENV === "development" });

  const requestHeaders = new Headers(request.headers);
  requestHeaders.set("x-nonce", nonce);
  requestHeaders.set("Content-Security-Policy", csp);

  const response = intl(request);
  // Forward the modified request headers through next-intl's response. Only the request-override headers are
  // copied (never x-middleware-next/rewrite), so redirects and rewrites from next-intl keep their meaning.
  const forward = NextResponse.next({ request: { headers: requestHeaders } });
  forward.headers.forEach((value, key) => {
    if (key === "x-middleware-override-headers" || key.startsWith("x-middleware-request-")) response.headers.set(key, value);
  });
  response.headers.set("Content-Security-Policy", csp);
  return response;
}

export const config = {
  // Everything except API routes, Next assets and files with an extension.
  matcher: ["/((?!api|_next/static|_next/image|brand|favicon\\.ico|.*\\..*).*)"],
};
