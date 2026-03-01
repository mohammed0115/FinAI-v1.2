import type { HTMLAttributes } from "react";
import { cn } from "@/src/lib/ui/cn";

type LtrIslandProps = HTMLAttributes<HTMLSpanElement>;

export default function LtrIsland({ className, ...props }: LtrIslandProps) {
  return <span dir="ltr" className={cn("inline-block text-start", className)} {...props} />;
}
