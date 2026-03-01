import type { InputHTMLAttributes } from "react";
import { cn } from "@/src/lib/ui/cn";

type InputProps = InputHTMLAttributes<HTMLInputElement>;

export default function Input({ className, ...props }: InputProps) {
  return (
    <input
      className={cn(
        "h-11 w-full rounded-loginMd border border-app-border/80 bg-white/80 px-3.5 text-sm text-app-text placeholder:text-app-textMuted outline-none transition-all focus:border-app-primaryFrom focus:bg-white focus:ring-2 focus:ring-app-primaryFrom/20",
        className,
      )}
      {...props}
    />
  );
}
