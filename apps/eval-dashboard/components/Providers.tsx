"use client";
// App-wide providers: React Query (polling + retries), @evolve/ui (labels, locale, dir, router Link), tooltips.
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { EvolveUIProvider, TooltipProvider, type LinkLike, type UILabels } from "@evolve/ui";
import { useLocale, useMessages } from "next-intl";
import { forwardRef, useState, type AnchorHTMLAttributes, type ReactNode } from "react";
import { Link as IntlLink } from "@/i18n/navigation";
import { ApiError } from "@/lib/api";

const AppLink = forwardRef<HTMLAnchorElement, AnchorHTMLAttributes<HTMLAnchorElement> & { href: string }>(function AppLink(
  { href, ...rest },
  ref,
) {
  // In-page anchors (the eval rail links to sections) stay plain hash links.
  if (href.startsWith("#")) return <a ref={ref} href={href} {...rest} />;
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
            refetchOnWindowFocus: false,
            retry: (n, err) => !(err instanceof ApiError && err.status >= 400 && err.status < 500) && n < 1,
          },
          mutations: { retry: false },
        },
      }),
  );
  return (
    <QueryClientProvider client={client}>
      <EvolveUIProvider locale={locale} dir={dir} labels={messages.ui} Link={AppLink}>
        <TooltipProvider delayDuration={250}>{children}</TooltipProvider>
      </EvolveUIProvider>
    </QueryClientProvider>
  );
}
