"use client";
import { Button } from "@evolve/ui/primitives/button";
import { EmptyState } from "@evolve/ui/primitives/feedback";
import { KeyRound } from "lucide-react";
import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";

// Permission-denied state (docs/09 §6): explains what is needed instead of a bare redirect.
export function SignInRequired({ title, body }: { title: string; body: string }) {
  const t = useTranslations("chrome");
  return (
    <div className="mx-auto max-w-xl py-8" data-testid="sign-in-required">
      <h1 className="sr-only">{title}</h1>
      <EmptyState
        icon={KeyRound}
        title={title}
        body={body}
        action={
          <Button asChild>
            <Link href="/sign-in">{t("signIn")}</Link>
          </Button>
        }
      />
    </div>
  );
}
