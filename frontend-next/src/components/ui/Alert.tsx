import type { HTMLAttributes, ReactNode } from "react";
import { AlertCircle, CheckCircle2, Info, TriangleAlert } from "lucide-react";
import { cn } from "@/src/lib/ui/cn";

type AlertTone = "info" | "success" | "warning" | "danger";

type AlertProps = HTMLAttributes<HTMLDivElement> & {
  tone?: AlertTone;
  title?: ReactNode;
};

const toneClasses: Record<AlertTone, string> = {
  info: "border-blue-500/20 bg-blue-500/10 text-blue-800",
  success: "border-emerald-500/20 bg-emerald-500/10 text-emerald-800",
  warning: "border-amber-500/20 bg-amber-500/10 text-amber-800",
  danger: "border-red-500/20 bg-red-500/10 text-red-800",
};

function ToneIcon({ tone }: { tone: AlertTone }) {
  if (tone === "success") return <CheckCircle2 className="h-4 w-4 shrink-0" />;
  if (tone === "warning") return <TriangleAlert className="h-4 w-4 shrink-0" />;
  if (tone === "danger") return <AlertCircle className="h-4 w-4 shrink-0" />;
  return <Info className="h-4 w-4 shrink-0" />;
}

export default function Alert({
  className,
  tone = "info",
  title,
  children,
  ...props
}: AlertProps) {
  return (
    <div
      className={cn(
        "flex items-start gap-2 rounded-loginMd border px-3.5 py-3 text-sm",
        toneClasses[tone],
        className,
      )}
      {...props}
    >
      <ToneIcon tone={tone} />
      <div className="space-y-0.5">
        {title ? <p className="font-semibold">{title}</p> : null}
        <div>{children}</div>
      </div>
    </div>
  );
}
