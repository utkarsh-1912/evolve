import { redirect } from "@/i18n/navigation";

// P2 route kept as a redirect: "Who does what" is now part of Help.
export default async function HowRedirect({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  redirect({ href: "/help", locale });
}
