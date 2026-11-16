import { setRequestLocale } from "next-intl/server";
import { CalendarScreen } from "@/components/screens";

export default async function CalendarPage({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  setRequestLocale(locale);
  return <CalendarScreen />;
}
