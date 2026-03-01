"use client";

import { Bell } from "lucide-react";
import { usePathname, useSearchParams } from "next/navigation";
import { Link } from "@/i18n/navigation";
import Button from "@/src/components/ui/Button";
import LtrIsland from "@/src/components/common/LtrIsland";

type TopbarProps = {
  locale: string;
};

export default function Topbar({ locale }: TopbarProps) {
  const pathname = usePathname() || `/${locale}/dashboard`;
  const searchParams = useSearchParams();
  const isArabic = locale === "ar";
  const targetLocale = isArabic ? "en" : "ar";
  const search = searchParams?.toString();
  const href = `${pathname}${search ? `?${search}` : ""}`;

  return (
    <header className="sticky top-0 z-20 border-b border-app-border/70 bg-[var(--surface-glass-strong)] backdrop-blur-xl">
      <div className="flex h-16 items-center justify-between px-4 md:px-6">
        <div className="flex items-center gap-3">
          <div className="hidden rounded-loginMd border border-app-border/70 bg-white/70 px-3 py-1.5 text-xs text-app-textSecondary md:block">
            <span>{isArabic ? "السنة المالية" : "Fiscal year"}</span>{" "}
            <LtrIsland className="font-semibold">2026</LtrIsland>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Link href={href} locale={targetLocale}>
            <Button variant="secondary" className="px-3 py-2 text-xs">
              {isArabic ? "English" : "العربية"}
            </Button>
          </Link>
          <button
            type="button"
            className="relative inline-flex h-10 w-10 items-center justify-center rounded-loginMd border border-app-border/70 bg-white/65 text-app-textSecondary transition hover:bg-white/85"
            aria-label="notifications"
          >
            <Bell className="h-4 w-4" />
            <span className="absolute end-2 top-2 h-2 w-2 rounded-full bg-red-500" />
          </button>
        </div>
      </div>
    </header>
  );
}
