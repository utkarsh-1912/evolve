import { setRequestLocale } from "next-intl/server";
import { CitizenShell } from "@/components/CitizenShell";

// Shelled citizen routes (docs/09 §3).
export default async function AppLayout({ children, params }: { children: React.ReactNode; params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  setRequestLocale(locale);
  return <CitizenShell>{children}</CitizenShell>;
}
