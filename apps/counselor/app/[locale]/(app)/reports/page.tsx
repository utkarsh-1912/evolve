import { setRequestLocale } from "next-intl/server";
import { ReportsScreen } from "@/components/screens";

export default async function ReportsPage({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  setRequestLocale(locale);
  return <ReportsScreen />;
}
