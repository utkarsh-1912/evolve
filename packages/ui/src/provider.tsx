"use client";
// EvolveUIProvider: locale, direction, a router-agnostic Link, and the design system's own UI strings.
// The package ships English defaults; apps pass translated labels (AR keys = TODO(native-review)).
import { createContext, useContext, useMemo, type AnchorHTMLAttributes, type ComponentType, type ReactNode } from "react";
import type { LoopState, Scenario } from "./contracts";

export interface UILabels {
  close: string;
  cancel: string;
  loading: string;
  retry: string;
  errorTitle: string;
  errorBody: string;
  errorReference: string;
  emptyTitle: string;
  offline: string;
  stale: string;
  refresh: string;
  permissionTitle: string;
  heldForReview: string;
  heldForReviewBody: string;
  howCounted: string;
  hideCounted: string;
  notComputed: string;
  notComputedHelp: string;
  formula: string;
  inputs: string;
  contract: string;
  digest: string;
  scenario: string;
  provenanceSource: string;
  inputNames: Record<"F" | "prior_carrier_b" | "detection_rate" | "posterior_carrier_b" | "offspring_risk", string>;
  formulas: Record<Scenario, string>;
  notifications: string;
  notificationsUnread: string;
  noNotifications: string;
  markAllRead: string;
  profile: string;
  signOut: string;
  signedInAs: string;
  language: string;
  breadcrumb: string;
  mainNav: string;
  more: string;
  menu: string;
  previous: string;
  next: string;
  pageOf: string; // "{page} of {pages}"
  rowsEmpty: string;
  sortAscending: string;
  sortDescending: string;
  technicalDetails: string;
  gene: string;
  classification: string;
  zygosity: string;
  visibility: Record<"only_you" | "you_and_counselor" | "couple", string>;
  loopStates: Record<LoopState, string>;
  stepOf: string; // "Step {n} of {total}"
  youAreHere: string;
  owner: string;
  due: string;
  nextAction: string;
  completed: string;
  skipped: string;
  expandMenu: string;
  collapseMenu: string;
  simulated: string;
  simulatedDetail: string;
  upcoming: string;
  messagesEmpty: string;
  gatePassed: string;
  skipToContent: string;
  confirm: string;
  consequences: string;
}

export const DEFAULT_LABELS: UILabels = {
  close: "Close",
  cancel: "Cancel",
  loading: "Loading",
  retry: "Try again",
  errorTitle: "Something went wrong",
  errorBody: "Nothing was shared. You can try again.",
  errorReference: "Reference",
  emptyTitle: "Nothing here yet",
  offline: "You are offline. Changes will not be saved until you reconnect.",
  stale: "This information may be out of date.",
  refresh: "Refresh",
  permissionTitle: "Consent needed",
  heldForReview: "Held for counselor review",
  heldForReviewBody: "A genetic counselor will go through this with you before it is shown.",
  howCounted: "How it was counted",
  hideCounted: "Hide how it was counted",
  notComputed: "Not calculated",
  notComputedHelp: "A genetic counselor will explain this.",
  formula: "Formula",
  inputs: "Inputs",
  contract: "Contract version",
  digest: "Digest",
  scenario: "Scenario",
  provenanceSource: "Source: docs/07-RISK-MATH-SPEC.md §2",
  inputNames: {
    F: "F (genome-wide context only)",
    prior_carrier_b: "Prior",
    detection_rate: "Detection rate d",
    posterior_carrier_b: "Posterior",
    offspring_risk: "Offspring risk",
  },
  formulas: {
    concordant_positive: "Both partners carry a change in the same gene: Mendelian recessive inheritance (value stored in the locked record)",
    discordant: "prior = R + (1 − R)·q; posterior = prior·(1 − d) / (prior·(1 − d) + (1 − prior)); offspring risk = posterior / 4",
    concordant_negative: "Each partner: q(1 − d) / (q(1 − d) + 1 − q); offspring risk = product / 4",
    shared_vus_roh: "Not calculated: reviewed by a genetic counselor",
    atypical_genotype: "Not calculated: reviewed by a genetic counselor",
  },
  notifications: "Notifications",
  notificationsUnread: "{count} unread",
  noNotifications: "You have no notifications.",
  markAllRead: "Mark all as read",
  profile: "Profile",
  signOut: "Sign out",
  signedInAs: "Signed in as {name}",
  language: "Language",
  breadcrumb: "Breadcrumb",
  mainNav: "Main",
  more: "More",
  menu: "Menu",
  previous: "Previous",
  next: "Next",
  pageOf: "{page} of {pages}",
  rowsEmpty: "No records yet.",
  sortAscending: "sorted ascending",
  sortDescending: "sorted descending",
  technicalDetails: "Technical details",
  gene: "Gene",
  classification: "Classification",
  zygosity: "Copies",
  visibility: { only_you: "Only you", you_and_counselor: "You and your counselor", couple: "You and your partner" },
  loopStates: {
    ResultIssued: "Result issued",
    PatientNotified: "You were notified",
    ComprehensionConfirmed: "Understanding checked",
    ConfirmatoryDone: "Confirmatory test done",
    CounselingDone: "Counseling done",
    ReproReferralDone: "Referral done",
    HumanClosure: "Closed by your counselor",
  },
  stepOf: "Step {n} of {total}",
  youAreHere: "You are here",
  owner: "Owner",
  due: "Due",
  nextAction: "Next",
  completed: "Completed",
  skipped: "Skipped",
  expandMenu: "Expand menu",
  collapseMenu: "Collapse menu",
  simulated: "Simulated",
  simulatedDetail: "Simulated environment: synthetic people, no real results.",
  upcoming: "Upcoming",
  messagesEmpty: "No messages yet. Messages from your care team will appear here.",
  gatePassed: "Checked by the safety gate",
  skipToContent: "Skip to content",
  confirm: "Confirm",
  consequences: "What happens",
};

export type LinkLike = ComponentType<AnchorHTMLAttributes<HTMLAnchorElement> & { href: string }>;

interface UIContextValue {
  locale: string;
  dir: "ltr" | "rtl";
  labels: UILabels;
  Link: LinkLike;
}

const DefaultLink: LinkLike = (props) => <a {...props} />;

const UIContext = createContext<UIContextValue>({ locale: "en", dir: "ltr", labels: DEFAULT_LABELS, Link: DefaultLink });

type DeepPartial<T> = { [K in keyof T]?: T[K] extends object ? DeepPartial<T[K]> : T[K] };

function merge(base: UILabels, over?: DeepPartial<UILabels>): UILabels {
  if (!over) return base;
  const out: Record<string, unknown> = { ...base };
  for (const [k, v] of Object.entries(over)) {
    const b = (base as unknown as Record<string, unknown>)[k];
    out[k] = v && typeof v === "object" && b && typeof b === "object" ? { ...(b as object), ...(v as object) } : v;
  }
  return out as unknown as UILabels;
}

export function EvolveUIProvider({
  locale = "en",
  dir = "ltr",
  labels,
  Link,
  children,
}: {
  locale?: string;
  dir?: "ltr" | "rtl";
  labels?: DeepPartial<UILabels>;
  Link?: LinkLike;
  children: ReactNode;
}) {
  const value = useMemo(
    () => ({ locale, dir, labels: merge(DEFAULT_LABELS, labels), Link: Link ?? DefaultLink }),
    [locale, dir, labels, Link],
  );
  return <UIContext.Provider value={value}>{children}</UIContext.Provider>;
}

export function useUI(): UIContextValue {
  return useContext(UIContext);
}

/** Tiny ICU-less interpolation for the package's own labels: "{count} unread". */
export function fmt(template: string, vars: Record<string, string | number>): string {
  return template.replace(/\{(\w+)\}/g, (_, k: string) => (k in vars ? String(vars[k]) : `{${k}}`));
}
