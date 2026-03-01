"use client";

import { BarChart3, FileText, LayoutDashboard, Settings, ShieldCheck } from "lucide-react";
import { usePathname } from "next/navigation";
import { Link } from "@/i18n/navigation";
import { cn } from "@/src/lib/ui/cn";

type SidebarProps = {
  locale: string;
};

const navItems = [
  { href: "/dashboard", labelAr: "لوحة التحكم", labelEn: "Dashboard", icon: LayoutDashboard },
  { href: "/compliance", labelAr: "الامتثال", labelEn: "Compliance", icon: ShieldCheck },
  { href: "/transactions", labelAr: "المعاملات", labelEn: "Transactions", icon: BarChart3 },
  { href: "/reports", labelAr: "التقارير", labelEn: "Reports", icon: FileText },
  { href: "/settings/organization", labelAr: "الإعدادات", labelEn: "Settings", icon: Settings },
];

export default function Sidebar({ locale }: SidebarProps) {
  const pathname = usePathname() || "";
  const isArabic = locale === "ar";

  return (
    <aside className="fixed inset-y-0 start-0 z-30 hidden w-72 border-e border-white/10 bg-sidebar p-5 shadow-card lg:block">
      <div className="mb-8 flex items-center gap-3">
        <div className="relative">
          <div className="h-11 w-11 rounded-loginMd bg-primary shadow-primary" />
          <span className="absolute -end-0.5 -top-0.5 h-2.5 w-2.5 rounded-full border border-slate-900 bg-emerald-400" />
        </div>
        <div>
          <p className="text-lg font-bold text-white">GSC-FinAI</p>
          <p className="text-xs text-slate-300">{isArabic ? "منصة التمويل الذكية" : "Intelligent Finance Platform"}</p>
        </div>
      </div>

      <nav className="space-y-1.5">
        {navItems.map((item) => {
          const Icon = item.icon;
          const target = `/${locale}${item.href}`;
          const active = pathname === target || pathname.startsWith(`${target}/`);

          return (
            <Link
              key={item.href}
              href={item.href}
              locale={locale}
              className={cn(
                "flex items-center gap-2.5 rounded-loginSm border px-3 py-2.5 text-sm transition-all",
                active
                  ? "border-cyan-300/30 bg-white/[0.12] text-white shadow-soft"
                  : "border-transparent text-slate-300 hover:border-white/10 hover:bg-white/[0.08] hover:text-white",
              )}
            >
              <Icon className="h-4 w-4" />
              <span>{isArabic ? item.labelAr : item.labelEn}</span>
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
