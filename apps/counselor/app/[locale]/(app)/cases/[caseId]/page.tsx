import { setRequestLocale } from "next-intl/server";
import { CaseScreen } from "@/components/case/CaseScreen";

// Case IDs are opaque synthetic identifiers (no PHI in URLs, P-11).
export default async function CasePage({ params }: { params: Promise<{ locale: string; caseId: string }> }) {
  const { locale, caseId } = await params;
  setRequestLocale(locale);
  return <CaseScreen caseId={decodeURIComponent(caseId)} />;
}
