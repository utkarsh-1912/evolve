import { setRequestLocale } from "next-intl/server";
import { CounselorShell } from "@/components/CounselorShell";

// Shelled counselor routes (docs/09 §3).
export default async function AppLayout({ children, params }: { children: React.ReactNode; params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  setRequestLocale(locale);
  return <CounselorShell>{children}</CounselorShell>;
}
