import type { ReactNode } from "react";
import { cn } from "@/src/lib/ui/cn";

type LoadingStateProps = {
  label?: ReactNode;
  className?: string;
};

export default function LoadingState({ label, className }: LoadingStateProps) {
  return (
    <div className={cn("flex min-h-screen w-full items-center justify-center", className)}>
      <div className="glass-surface inline-flex items-center gap-3 rounded-loginMd border border-app-border/70 px-4 py-3 shadow-soft">
        <span className="h-4 w-4 animate-spin rounded-full border-2 border-app-borderStrong/70 border-t-app-primaryFrom" />
        <span className="text-sm text-app-textSecondary">{label ?? "جاري التحميل..."}</span>
      </div>
    </div>
  );
}
