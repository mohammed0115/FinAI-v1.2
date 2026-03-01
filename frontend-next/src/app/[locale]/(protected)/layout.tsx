import type { ReactNode } from "react";
import AuthGateClient from "@/src/components/auth/AuthGateClient";
import AppShell from "@/src/components/shell/AppShell";

export default async function ProtectedLayout({
  children,
  params,
}: {
  children: ReactNode;
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;

  return (
    <AuthGateClient locale={locale}>
      <AppShell locale={locale}>{children}</AppShell>
    </AuthGateClient>
  );
}
