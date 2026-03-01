import type { HTMLAttributes } from "react";
import { cn } from "@/src/lib/ui/cn";

type CardProps = HTMLAttributes<HTMLDivElement> & {
  elevated?: boolean;
};

export default function Card({
  className,
  elevated = true,
  ...props
}: CardProps) {
  return (
    <div
      className={cn(
        "glass-surface border border-app-border/70 rounded-loginLg",
        elevated ? "shadow-card" : "shadow-soft",
        className,
      )}
      {...props}
    />
  );
}
