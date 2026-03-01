import type { ReactNode } from "react";
import { NextIntlClientProvider } from "next-intl";

export default async function LocaleLayout({
  children,
  params,
}: {
  children: ReactNode;
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  const isArabic = locale === "ar";

  return (
    <NextIntlClientProvider locale={locale} messages={{}}>
      <div dir={isArabic ? "rtl" : "ltr"} className="min-h-screen">
        {children}
      </div>
    </NextIntlClientProvider>
  );
}
