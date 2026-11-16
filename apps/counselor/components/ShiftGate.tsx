"use client";
// Permission gate for case data (docs/09 §6 "Permission denied"): signed in as a counselor AND on shift
// (online_access, DECISIONS #40). The backend enforces the same rule (403 off_shift); this avoids the call.
import { Button, ErrorState, LoadingRegion, PermissionState, Skeleton } from "@evolve/ui";
import { useTranslations } from "next-intl";
import type { ReactNode } from "react";
import { Link } from "@/i18n/navigation";
import { useShift } from "@/lib/queries";
import { useSession } from "@/lib/session";
import { ApiError } from "@/lib/types";

export function ShiftGate({ children }: { children: ReactNode }) {
  const t = useTranslations("gate");
  const { session, ready } = useSession();
  const shift = useShift();
  if (!ready) {
    return (
      <LoadingRegion>
        <Skeleton className="h-10 w-1/3" />
        <Skeleton className="mt-4 h-64 w-full" />
      </LoadingRegion>
    );
  }
  if (!session) {
    return (
      <div data-testid="signed-out">
        <PermissionState
          body={t("signInBody")}
          action={
            <Button asChild>
              <Link href="/sign-in">{t("signInAction")}</Link>
            </Button>
          }
        />
      </div>
    );
  }
  if (!session.on_shift) {
    return <OffShift onGo={() => shift.mutate(true)} busy={shift.isPending} />;
  }
  return <>{children}</>;
}

export function OffShift({ onGo, busy }: { onGo?: () => void; busy?: boolean }) {
  const t = useTranslations("gate");
  return (
    <section aria-labelledby="off-shift-title" data-testid="off-shift" className="space-y-3">
      <h1 id="off-shift-title" className="font-display text-[1.875rem] font-medium text-ink">
        {t("offShiftTitle")}
      </h1>
      <PermissionState
        body={t("offShiftBody")}
        action={
          onGo ? (
            <Button onClick={onGo} loading={busy} data-testid="go-on-shift">
              {t("goOnShift")}
            </Button>
          ) : undefined
        }
      />
    </section>
  );
}

/** Map an API error to the right state: off shift → permission state; expired → sign-in; else ErrorState with retry. */
export function GateForError({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const t = useTranslations("gate");
  const shift = useShift();
  if (error instanceof ApiError && error.code === "off_shift") return <OffShift onGo={() => shift.mutate(true)} busy={shift.isPending} />;
  if (error instanceof ApiError && error.status === 401) {
    return (
      <PermissionState
        body={t("expired")}
        action={
          <Button asChild>
            <Link href="/sign-in">{t("signInAction")}</Link>
          </Button>
        }
      />
    );
  }
  // Reference = error code only (no PHI, no genes in errors).
  return <ErrorState onRetry={onRetry} reference={error instanceof ApiError ? `${error.status}-${error.code}` : undefined} />;
}
