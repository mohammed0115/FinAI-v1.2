import type { HTMLAttributes } from "react";
import { cn } from "@/src/lib/ui/cn";

type SectionProps = HTMLAttributes<HTMLElement>;

export default function Section({ className, ...props }: SectionProps) {
  return <section className={cn("mb-6", className)} {...props} />;
}
