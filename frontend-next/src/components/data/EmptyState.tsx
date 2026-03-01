import type { ReactNode } from "react";
import { Inbox } from "lucide-react";

type EmptyStateProps = {
  title?: ReactNode;
  description?: ReactNode;
  action?: ReactNode;
};

export default function EmptyState({
  title,
  description,
  action,
}: EmptyStateProps) {
  return (
    <div className="glass-surface flex w-full flex-col items-center justify-center rounded-loginLg border border-app-border/70 px-6 py-10 text-center shadow-soft">
      <div className="mb-3 rounded-loginMd bg-white/70 p-3">
        <Inbox className="h-5 w-5 text-app-textMuted" />
      </div>
      <h3 className="text-base font-semibold text-app-text">
        {title ?? "لا توجد بيانات بعد"}
      </h3>
      <p className="mt-1 text-sm text-app-textSecondary">
        {description ?? "ستظهر العناصر هنا عند توفر البيانات."}
      </p>
      {action ? <div className="mt-4">{action}</div> : null}
    </div>
  );
}
