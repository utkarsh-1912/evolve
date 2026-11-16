import { redirect } from "next/navigation";

// The workbench opens on the queue.
export default async function Index({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  redirect(`/${locale}/queue`);
}
