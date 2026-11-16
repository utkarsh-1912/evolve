"use client";
// App-wide providers: React Query (retries + caching), @evolve/ui (labels, locale, dir, router Link), tooltips, toasts.
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { TooltipProvider } from "@evolve/ui/primitives/tooltip";
import { ToastProvider } from "@evolve/ui/primitives/toast";
import { EvolveUIProvider, type LinkLike, type UILabels } from "@evolve/ui/provider";
import { useLocale, useMessages } from "next-intl";
import { forwardRef, useState, type AnchorHTMLAttributes, type ReactNode } from "react";
import { Link as IntlLink } from "@/i18n/navigation";
import { ApiError } from "@/lib/types";

// The design system's router-agnostic Link, backed by next-intl (locale-prefixed hrefs).
const AppLink = forwardRef<HTMLAnchorElement, AnchorHTMLAttributes<HTMLAnchorElement> & { href: string }>(function AppLink(
  { href, ...rest },
  ref,
) {
  return <IntlLink ref={ref} href={href} {...rest} />;
}) as unknown as LinkLike;

export function Providers({ children, dir }: { children: ReactNode; dir: "ltr" | "rtl" }) {
  const locale = useLocale();
  const messages = useMessages() as unknown as { ui: Partial<UILabels> };
  const [client] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 30_000,
            refetchOnWindowFocus: false,
            // Never retry auth/consent/permission errors; retry transient ones twice.
            retry: (count, err) => !(err instanceof ApiError && err.status >= 400 && err.status < 500) && count < 2,
          },
          mutations: { retry: false },
        },
      }),
  );
  return (
    <QueryClientProvider client={client}>
      <EvolveUIProvider locale={locale} dir={dir} labels={messages.ui} Link={AppLink}>
        <TooltipProvider delayDuration={250}>
          <ToastProvider>{children}</ToastProvider>
        </TooltipProvider>
      </EvolveUIProvider>
    </QueryClientProvider>
  );
}
