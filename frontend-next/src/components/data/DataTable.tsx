import type { ReactNode } from "react";
import { cn } from "@/src/lib/ui/cn";

type Column<T> = {
  key: string;
  header: ReactNode;
  className?: string;
  render: (row: T) => ReactNode;
};

type DataTableProps<T> = {
  rows: T[];
  columns: Array<Column<T>>;
  rowKey: (row: T, index: number) => string;
  emptyState?: ReactNode;
};

export default function DataTable<T>({
  rows,
  columns,
  rowKey,
  emptyState,
}: DataTableProps<T>) {
  if (!rows.length) {
    return <>{emptyState ?? null}</>;
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[34rem] border-separate border-spacing-0 text-sm">
        <thead>
          <tr>
            {columns.map((column) => (
              <th
                key={column.key}
                className={cn(
                  "border-b border-app-border/70 px-4 py-3 text-start text-xs font-semibold uppercase tracking-wide text-app-textMuted",
                  column.className,
                )}
              >
                {column.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr key={rowKey(row, index)} className="hover:bg-white/40">
              {columns.map((column) => (
                <td
                  key={column.key}
                  className={cn(
                    "border-b border-app-border/50 px-4 py-3 text-app-textSecondary",
                    column.className,
                  )}
                >
                  {column.render(row)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
