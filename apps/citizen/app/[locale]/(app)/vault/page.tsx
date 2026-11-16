import { redirect } from "@/i18n/navigation";

// P2 route kept as a redirect: "My results" now lives at /results (the backend's notification href).
export default async function VaultRedirect({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  redirect({ href: "/results", locale });
}
