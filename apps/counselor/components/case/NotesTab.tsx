"use client";
// Notes: internal to the care team, stored and audited by ID only, never sent to patients (api.md v1.2.0).
import { Alert, Button, Card, EmptyState, FormField, Textarea, useToast } from "@evolve/ui";
import { Lock, NotebookPen } from "lucide-react";
import { useTranslations } from "next-intl";
import { useState } from "react";
import { useAddNote } from "@/lib/queries";
import type { CaseView } from "@/lib/types";
import { useFormatTs } from "../format";

export function NotesTab({ view, readOnly, text, setText }: { view: CaseView; readOnly: boolean; text: string; setText: (t: string) => void }) {
  const t = useTranslations("notes");
  const formatTs = useFormatTs();
  const toast = useToast();
  const add = useAddNote();
  const [error, setError] = useState<string | null>(null);
  const notes = [...view.notes].sort((a, b) => b.ts.localeCompare(a.ts));

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!text.trim()) {
      setError(t("required"));
      return;
    }
    setError(null);
    try {
      await add.mutateAsync({ caseId: view.case.case_id, text });
      setText("");
      toast({ title: t("added"), tone: "success" });
    } catch {
      setError(t("error"));
    }
  };

  return (
    <section className="space-y-5" aria-labelledby="notes-h" data-testid="notes">
      <h2 id="notes-h" className="text-lg font-semibold text-ink">
        {t("title")}
      </h2>
      <Alert tone="info" icon={Lock}>
        {t("internal")}
      </Alert>
      {readOnly ? null : (
        <form onSubmit={submit} className="space-y-3" data-testid="note-form">
          <FormField label={t("label")} help={t("help")} error={error ?? undefined}>
            <Textarea value={text} onChange={(e) => setText(e.target.value)} maxLength={5000} rows={4} />
          </FormField>
          <Button type="submit" loading={add.isPending} data-testid="note-add">
            {t("add")}
          </Button>
        </form>
      )}
      {notes.length === 0 ? (
        <EmptyState icon={NotebookPen} title={t("emptyTitle")} />
      ) : (
        <ul className="space-y-3" data-testid="note-list">
          {notes.map((n) => (
            <li key={n.id}>
              <Card as="article" padding="sm">
                <header className="mb-2 flex flex-wrap items-center justify-between gap-2 text-sm">
                  <span className="font-semibold">
                    {n.kind === "closure" ? t("closureKind") : t("noteKind")} · <span className="font-mono">{n.author}</span>
                  </span>
                  <time dateTime={n.ts} className="text-ink-2">
                    {formatTs(n.ts)}
                  </time>
                </header>
                <p className="max-w-[72ch] whitespace-pre-wrap text-ink">{n.text}</p>
              </Card>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
