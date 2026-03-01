import type { ButtonHTMLAttributes, ReactNode } from "react";
import { cn } from "@/src/lib/ui/cn";

type ButtonVariant = "primary" | "secondary" | "ghost";

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant;
  icon?: ReactNode;
};

const variantClasses: Record<ButtonVariant, string> = {
  primary:
    "bg-primary text-white shadow-primary hover:brightness-105 active:brightness-95",
  secondary:
    "bg-app-card/80 text-app-text border border-app-border shadow-soft hover:bg-app-card/95",
  ghost: "bg-transparent text-app-textSecondary hover:bg-white/40",
};

export default function Button({
  className,
  variant = "secondary",
  icon,
  children,
  ...props
}: ButtonProps) {
  return (
    <button
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-loginMd px-4 py-2.5 text-sm font-semibold transition-all disabled:cursor-not-allowed disabled:opacity-60",
        variantClasses[variant],
        className,
      )}
      {...props}
    >
      {icon}
      {children}
    </button>
  );
}
