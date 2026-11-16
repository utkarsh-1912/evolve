import { SimpleFooter, SimpleHeader } from "@/components/SimpleHeader";

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <SimpleHeader showSignIn={false} />
      <main id="main" className="mx-auto max-w-[var(--content-max)] px-4 py-8 md:px-8 md:py-12">
        {children}
      </main>
      <SimpleFooter />
    </>
  );
}
