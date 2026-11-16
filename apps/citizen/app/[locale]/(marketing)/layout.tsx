import { SimpleFooter, SimpleHeader } from "@/components/SimpleHeader";

// Marketing landing stays un-shelled (TASK-P3-UI-DS §3).
export default function MarketingLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <SimpleHeader />
      <main id="main" className="mx-auto max-w-[var(--content-max)] px-4 py-8 md:px-8 md:py-12">
        {children}
      </main>
      <SimpleFooter />
    </>
  );
}
