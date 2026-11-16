import { setRequestLocale } from "next-intl/server";
import { QueueScreen } from "@/components/screens";

export default async function QueuePage({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  setRequestLocale(locale);
  return <QueueScreen mode="queue" />;
}
