"use client";

import type { ComponentProps } from "react";
import NextLink from "next/link";

type LinkProps = Omit<ComponentProps<typeof NextLink>, "href"> & {
  href: string;
  locale?: string;
};

const SUPPORTED_LOCALES = new Set(["ar", "en"]);

function withLocale(href: string, locale?: string): string {
  if (!locale) return href;
  if (href.startsWith("http://") || href.startsWith("https://") || href.startsWith("#")) {
    return href;
  }

  const normalized = href.startsWith("/") ? href : `/${href}`;
  const segments = normalized.split("/").filter(Boolean);

  if (segments.length > 0 && SUPPORTED_LOCALES.has(segments[0])) {
    segments.shift();
  }

  return `/${[locale, ...segments].join("/")}`;
}

export function Link({ href, locale, ...props }: LinkProps) {
  return <NextLink href={withLocale(href, locale)} {...props} />;
}

