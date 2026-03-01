import type { HTMLAttributes } from "react";
import { cn } from "@/src/lib/ui/cn";

type BadgeTone = "info" | "success" | "warning" | "danger" | "neutral";

type BadgeProps = HTMLAttributes<HTMLSpanElement> & {
  tone?: BadgeTone;
};

const toneClasses: Record<BadgeTone, string> = {
  info: "bg-blue-500/10 text-blue-700 border-blue-500/20",
  success: "bg-emerald-500/10 text-emerald-700 border-emerald-500/20",
  warning: "bg-amber-500/10 text-amber-700 border-amber-500/20",
  danger: "bg-red-500/10 text-red-700 border-red-500/20",
  neutral: "bg-slate-500/10 text-slate-700 border-slate-500/20",
};

export default function Badge({ className, tone = "neutral", ...props }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-loginSm border px-2.5 py-1 text-xs font-semibold",
        toneClasses[tone],
        className,
      )}
      {...props}
    />
  );
}
