"use client";
// DataTable on TanStack Table v9 (headless) + AuditTable + ConsentTable.
// Semantic <table>, sortable headers with aria-sort, keyboard row activation, loading/empty states.
import { createColumnHelper, createPaginatedRowModel, createSortedRowModel, rowPaginationFeature, rowSortingFeature, sortFns, tableFeatures, useTable, type PaginationState, type RowData, type SortingState } from "@tanstack/react-table";
import { ArrowDown, ArrowUp, ArrowUpDown } from "lucide-react";
import { useMemo, useState, type ReactNode } from "react";
import { cn } from "../lib/cn";
import { useUI } from "../provider";
import { Button } from "../primitives/button";
import { ConfirmDialog } from "../primitives/dialog";
import { Skeleton } from "../primitives/feedback";
import { StatusChip, type Status } from "../primitives/display";
import { Pagination } from "../primitives/pagination";

const features = tableFeatures({
  rowSortingFeature,
  rowPaginationFeature,
  sortedRowModel: createSortedRowModel(),
  paginatedRowModel: createPaginatedRowModel(),
  sortFns,
});

export interface DataColumn<T> {
  id: string;
  header: string;
  cell: (row: T) => ReactNode;
  /** Provide to make the column sortable (string or number only). */
  sortValue?: (row: T) => string | number;
  align?: "start" | "end";
  mono?: boolean;
  /** Hide below the md breakpoint (the row still reads well). */
  hideOnMobile?: boolean;
}

export function DataTable<T extends RowData>({
  caption,
  columns,
  data,
  getRowId,
  loading,
  emptyState,
  pageSize = 10,
  onRowActivate,
  dense,
  testId,
}: {
  caption: string;
  columns: DataColumn<T>[];
  data: T[];
  getRowId: (row: T) => string;
  loading?: boolean;
  emptyState?: ReactNode;
  pageSize?: number;
  onRowActivate?: (row: T) => void;
  dense?: boolean;
  testId?: string;
}) {
  const { labels } = useUI();
  const [sorting, setSorting] = useState<SortingState>([]);
  const [pagination, setPagination] = useState<PaginationState>({ pageIndex: 0, pageSize });

  const tColumns = useMemo(() => {
    const helper = createColumnHelper<typeof features, T>();
    return columns.map((c) =>
      helper.accessor((row: T): unknown => (c.sortValue ? c.sortValue(row) : ""), {
        id: c.id,
        header: c.header,
        enableSorting: !!c.sortValue,
        sortFn: "alphanumeric",
      }),
    );
  }, [columns]);
  const colById = useMemo(() => new Map(columns.map((c) => [c.id, c])), [columns]);

  const table = useTable({
    features,
    columns: tColumns,
    data,
    getRowId: (row: T) => getRowId(row),
    state: { sorting, pagination },
    onSortingChange: setSorting,
    onPaginationChange: setPagination,
  });

  const pad = dense ? "px-3 py-2" : "px-4 py-3";
  const rows = table.getRowModel().rows;
  const pages = table.getPageCount();

  return (
    <div className="space-y-3" data-testid={testId}>
      <div className="overflow-x-auto rounded-lg border border-line bg-surface-1">
        <table className="w-full border-collapse text-sm">
          <caption className="sr-only">{caption}</caption>
          <thead className="bg-surface-2 text-start text-xs uppercase tracking-[0.06em] text-ink-2">
            {table.getHeaderGroups().map((g) => (
              <tr key={g.id}>
                {g.headers.map((h) => {
                  const col = colById.get(h.column.id);
                  const sorted = h.column.getIsSorted();
                  const canSort = h.column.getCanSort();
                  return (
                    <th
                      key={h.id}
                      scope="col"
                      aria-sort={sorted === "asc" ? "ascending" : sorted === "desc" ? "descending" : canSort ? "none" : undefined}
                      className={cn("font-semibold", pad, col?.align === "end" ? "text-end" : "text-start", col?.hideOnMobile && "hidden md:table-cell")}
                    >
                      {canSort ? (
                        <button
                          type="button"
                          onClick={h.column.getToggleSortingHandler()}
                          className="-mx-2 inline-flex min-h-9 items-center gap-1 rounded-sm px-2 uppercase hover:text-ink"
                        >
                          {col?.header}
                          {sorted === "asc" ? (
                            <ArrowUp aria-hidden className="size-3.5" />
                          ) : sorted === "desc" ? (
                            <ArrowDown aria-hidden className="size-3.5" />
                          ) : (
                            <ArrowUpDown aria-hidden className="size-3.5 opacity-60" />
                          )}
                          <span className="sr-only">
                            {sorted === "asc" ? labels.sortAscending : sorted === "desc" ? labels.sortDescending : ""}
                          </span>
                        </button>
                      ) : (
                        col?.header
                      )}
                    </th>
                  );
                })}
              </tr>
            ))}
          </thead>
          <tbody>
            {loading
              ? Array.from({ length: 3 }, (_, i) => (
                  <tr key={i} className="border-t border-line">
                    {columns.map((c) => (
                      <td key={c.id} className={cn(pad, c.hideOnMobile && "hidden md:table-cell")}>
                        <Skeleton className="h-4 w-3/4" />
                      </td>
                    ))}
                  </tr>
                ))
              : rows.map((r) => (
                  <tr
                    key={r.id}
                    tabIndex={onRowActivate ? 0 : undefined}
                    onClick={onRowActivate ? () => onRowActivate(r.original) : undefined}
                    onKeyDown={
                      onRowActivate
                        ? (e) => {
                            if (e.key === "Enter") onRowActivate(r.original);
                          }
                        : undefined
                    }
                    className={cn("border-t border-line", onRowActivate && "cursor-pointer hover:bg-surface-2 focus-visible:bg-surface-2")}
                  >
                    {columns.map((c) => (
                      <td
                        key={c.id}
                        className={cn(pad, "align-top text-ink", c.align === "end" && "text-end", c.mono && "font-mono text-xs", c.hideOnMobile && "hidden md:table-cell")}
                      >
                        {c.cell(r.original)}
                      </td>
                    ))}
                  </tr>
                ))}
          </tbody>
        </table>
        {!loading && data.length === 0 ? (
          <div className="border-t border-line p-4">{emptyState ?? <p className="text-sm text-ink-2">{labels.rowsEmpty}</p>}</div>
        ) : null}
      </div>
      <Pagination page={pagination.pageIndex + 1} pages={pages} onPage={(p) => table.setPageIndex(p - 1)} />
    </div>
  );
}

/** AuditTable: "who saw what, when" — own AuditEvents only (api.md v1.2.0 /me/activity). No genes, no counterpart identity. */
export interface AuditRow {
  ts: string;
  actor_role: string;
  action: string;
  object_kind: string;
}

export function AuditTable({
  rows,
  loading,
  caption,
  headers,
  formatTs,
  describe,
}: {
  rows: AuditRow[];
  loading?: boolean;
  caption: string;
  headers: { when: string; who: string; what: string };
  formatTs: (iso: string) => string;
  describe: (row: AuditRow) => ReactNode;
}) {
  const columns = useMemo<DataColumn<AuditRow>[]>(
    () => [
      { id: "ts", header: headers.when, cell: (r) => <time dateTime={r.ts}>{formatTs(r.ts)}</time>, sortValue: (r) => r.ts },
      { id: "actor", header: headers.who, cell: (r) => r.actor_role, sortValue: (r) => r.actor_role },
      { id: "what", header: headers.what, cell: describe },
    ],
    [headers, formatTs, describe],
  );
  return <DataTable caption={caption} columns={columns} data={rows} getRowId={(r) => `${r.ts}-${r.action}-${r.object_kind}`} loading={loading} testId="audit-table" />;
}

/** ConsentTable: status, scope, expiry, revoke-with-confirm (A6). */
export interface ConsentRow {
  id: string;
  status: "proposed" | "active" | "inactive" | "rejected";
  direction: "given" | "received";
  scopeLabel: string;
  expires_at: string;
}

export function ConsentTable({
  rows,
  loading,
  caption,
  headers,
  statusLabel,
  directionLabel,
  formatTs,
  revoke,
}: {
  rows: ConsentRow[];
  loading?: boolean;
  caption: string;
  headers: { scope: string; direction: string; status: string; expires: string; actions: string };
  statusLabel: (s: ConsentRow["status"]) => string;
  directionLabel: (d: ConsentRow["direction"]) => string;
  formatTs: (iso: string) => string;
  revoke?: {
    label: string;
    title: string;
    description?: string;
    consequences: string[];
    confirmLabel: string;
    onRevoke: (id: string) => Promise<void> | void;
  };
}) {
  const statusTone: Record<ConsentRow["status"], Status> = { active: "compatible", proposed: "review", inactive: "neutral", rejected: "neutral" };
  const columns: DataColumn<ConsentRow>[] = [
    { id: "scope", header: headers.scope, cell: (r) => r.scopeLabel },
    { id: "direction", header: headers.direction, cell: (r) => directionLabel(r.direction), hideOnMobile: true },
    {
      id: "status",
      header: headers.status,
      cell: (r) => (
        <StatusChip status={statusTone[r.status]} size="sm">
          {statusLabel(r.status)}
        </StatusChip>
      ),
      sortValue: (r) => r.status,
    },
    { id: "expires", header: headers.expires, cell: (r) => <time dateTime={r.expires_at}>{formatTs(r.expires_at)}</time>, sortValue: (r) => r.expires_at },
    {
      id: "actions",
      header: headers.actions,
      align: "end",
      cell: (r) =>
        revoke && r.status === "active" && r.direction === "given" ? (
          <ConfirmDialog
            trigger={
              <Button variant="danger-outline" size="sm">
                {revoke.label}
              </Button>
            }
            title={revoke.title}
            description={revoke.description}
            consequences={revoke.consequences}
            confirmLabel={revoke.confirmLabel}
            onConfirm={() => revoke.onRevoke(r.id)}
          />
        ) : null,
    },
  ];
  return <DataTable caption={caption} columns={columns} data={rows} getRowId={(r) => r.id} loading={loading} testId="consent-table" />;
}

