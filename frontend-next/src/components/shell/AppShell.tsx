import type { ReactNode } from "react";
import Sidebar from "@/src/components/shell/Sidebar";
import Topbar from "@/src/components/shell/Topbar";

type AppShellProps = {
  locale: string;
  children: ReactNode;
};

export default function AppShell({ locale, children }: AppShellProps) {
  return (
    <div className="relative min-h-screen overflow-x-hidden">
      <div className="pointer-events-none fixed inset-0 app-grid-overlay" />
      <div className="pointer-events-none fixed -end-28 -top-32 h-72 w-72 rounded-full bg-blue-500/20 blur-3xl" />
      <div className="pointer-events-none fixed bottom-0 start-1/3 h-72 w-72 rounded-full bg-cyan-500/10 blur-3xl" />

      <div className="relative z-10 min-h-screen">
        <Sidebar locale={locale} />
        <div className="min-h-screen lg:ms-72">
          <Topbar locale={locale} />
          <main className="px-4 pb-8 pt-4 md:px-6 md:pt-6">{children}</main>
        </div>
      </div>
    </div>
  );
}
